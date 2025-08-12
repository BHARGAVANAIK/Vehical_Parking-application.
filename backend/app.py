from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import timedelta, datetime
from flask_jwt_extended import (JWTManager, create_access_token, jwt_required, get_jwt_identity)
from functools import wraps
from flask_cors import CORS
from celery import Celery
import csv
from datetime import datetime
from collections import defaultdict
from flask_caching import Cache
import io
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parking_system.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'strong secret!'
app.config['CACHE_TYPE'] = 'RedisCache'
app.config['CACHE_REDIS_HOST'] = 'localhost'
app.config['CACHE_REDIS_PORT'] = 6379
app.config['CACHE_REDIS_DB'] = 1 
app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379/1'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  
jwt = JWTManager(app)
CORS(app)
db = SQLAlchemy(app)
cache = Cache(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(10), nullable=False, default='user')

class ParkingLot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prime_location_name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    address = db.Column(db.String(200), nullable=False)
    pin_code = db.Column(db.String(10), nullable=False)
    number_of_spots = db.Column(db.Integer, nullable=False)

class ParkingSpot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.id'), nullable=False)
    status = db.Column(db.String(1), nullable=False, default='A')  # A-available, O-occupied

class ParkingReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parking_timestamp = db.Column(db.DateTime, nullable=False)
    leaving_timestamp = db.Column(db.DateTime, nullable=True)
    parking_cost = db.Column(db.Float, nullable=True)

@app.route('/')
def home():
    return "Parking App Backend is running!"

first_request_done = False

@app.before_request
def create_tables_and_admin():
    global first_request_done
    if not first_request_done:
        db.create_all()
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password=generate_password_hash('admin123'),
                email='admin@parking.com',
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created with username: admin and password: admin123")
        first_request_done = True

@app.route('/users')
def list_users():
    users = User.query.all()
    return {
        "users": [
            {"id": u.id, "username": u.username, "role": u.role} for u in users
        ]
    }

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend='redis://localhost:6379/0',
        broker='redis://localhost:6379/0'
    )
    celery.conf.update(app.config)
    return celery

celery = make_celery(app)

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not all(k in data for k in ('username', 'password', 'email')):
        return jsonify({"msg": "Missing parameters"}), 400
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"msg": "Username already exists"}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"msg": "Email already registered"}), 409
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        username=data['username'],
        password=hashed_password,
        email=data['email'],
        role='user'
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "User registered successfully"}), 201

def generate_jwt(user):
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=1) 
    }
    jwt_token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return jwt_token

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                bearer, token = auth_header.split()
                if bearer.lower() != 'bearer':
                    return jsonify({'message': 'Invalid bearer token'}), 401
            except ValueError:
                return jsonify({'message': 'Invalid authorization header'}), 401
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.filter_by(id=data['user_id']).first()
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

@celery.task
def send_daily_reminders():
    from datetime import datetime, date
    today = date.today()
    users = User.query.filter_by(role='user').all()
    for user in users:
        has_booked = ParkingReservation.query.filter(
            ParkingReservation.user_id == user.id,
            ParkingReservation.parking_timestamp >= datetime(today.year, today.month, today.day)
        ).first()
        if not has_booked:
            print(f"Reminder sent to {user.email}")

@celery.task
def send_monthly_reports():
    from datetime import datetime, timedelta
    users = User.query.filter_by(role='user').all()
    for user in users:
        today = datetime.now()
        first_of_month = today.replace(day=1)
        last_month = first_of_month - timedelta(days=1)
        start = last_month.replace(day=1)
        end = last_month
        reservations = ParkingReservation.query.filter(
            ParkingReservation.user_id == user.id,
            ParkingReservation.parking_timestamp >= start,
            ParkingReservation.parking_timestamp <= end
        ).all()
        report_html = f"<h1>Monthly Report for {user.username}</h1>"
        report_html += f"<p>Total bookings: {len(reservations)}</p>"
        print(f"Report sent to {user.email}")

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({'message': f'This is a protected route. Hello, {current_user["username"]}!'}), 200

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not all(k in data for k in ('username', 'password')):
        return jsonify({"msg": "Missing username or password"}), 400
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"msg": "Bad username or password"}), 401
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"username": user.username, "role": user.role}
    )
    return jsonify(access_token=access_token), 200

@app.route('/admin/dashboard')
@jwt_required()
def admin_dashboard():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"msg": "Admins only!"}), 403
    return jsonify({"msg": f"Welcome Admin {current_user['username']}"})

@app.route('/user/dashboard')
@jwt_required()
def user_dashboard():
    current_user = get_jwt_identity()
    if current_user['role'] != 'user':
        return jsonify({"msg": "Users only!"}), 403
    return jsonify({"msg": f"Welcome User {current_user['username']}"})

@app.route('/admin/parking-lots', methods=['POST'])
@jwt_required()
def create_parking_lot():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({'msg': 'Admins only!'}), 403
    data = request.get_json()
    required = ['prime_location_name', 'price', 'address', 'pin_code', 'number_of_spots']
    if not all(k in data for k in required):
        return jsonify({'msg': 'Missing fields'}), 400
    lot = ParkingLot(
        prime_location_name=data['prime_location_name'],
        price=data['price'],
        address=data['address'],
        pin_code=data['pin_code'],
        number_of_spots=data['number_of_spots']
    )
    db.session.add(lot)
    db.session.commit()
    for _ in range(lot.number_of_spots):
        spot = ParkingSpot(lot_id=lot.id)
        db.session.add(spot)
    db.session.commit()
    return jsonify({'msg': 'Parking lot created', 'lot_id': lot.id}), 201

@app.route('/admin/parking-lots/<int:lot_id>', methods=['PUT'])
@jwt_required()
def edit_parking_lot(lot_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({'msg': 'Admins only!'}), 403
    lot = ParkingLot.query.get_or_404(lot_id)
    data = request.get_json()
    for field in ['prime_location_name', 'price', 'address', 'pin_code']:
        if field in data:
            setattr(lot, field, data[field])
    if 'number_of_spots' in data:
        diff = data['number_of_spots'] - lot.number_of_spots
        if diff > 0:
            for _ in range(diff):
                spot = ParkingSpot(lot_id=lot.id)
                db.session.add(spot)
        elif diff < 0:
            available_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').all()
            if len(available_spots) < abs(diff):
                return jsonify({'msg': 'Not enough available spots to remove'}), 400
            for spot in available_spots[:abs(diff)]:
                db.session.delete(spot)
        lot.number_of_spots = data['number_of_spots']
    db.session.commit()
    return jsonify({'msg': 'Parking lot updated'})

@app.route('/admin/parking-lots/<int:lot_id>', methods=['DELETE'])
@jwt_required()
def delete_parking_lot(lot_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({'msg': 'Admins only!'}), 403
    lot = ParkingLot.query.get_or_404(lot_id)
    occupied_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
    if occupied_spots > 0:
        return jsonify({'msg': 'Cannot delete lot with occupied spots'}), 400
    ParkingSpot.query.filter_by(lot_id=lot.id).delete()
    db.session.delete(lot)
    db.session.commit()
    return jsonify({'msg': 'Parking lot deleted'})

@app.route('/admin/parking-lots', methods=['GET'])
@jwt_required()
def get_parking_lots():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({'msg': 'Admins only!'}), 403
    lots = ParkingLot.query.all()
    result = []
    for lot in lots:
        total_spots = ParkingSpot.query.filter_by(lot_id=lot.id).count()
        available_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        result.append({
            'id': lot.id,
            'prime_location_name': lot.prime_location_name,
            'price': lot.price,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'number_of_spots': total_spots,
            'available_spots': available_spots
        })
    return jsonify(result)

@app.route('/admin/parking-spots/<int:spot_id>', methods=['DELETE'])
@jwt_required()
def delete_parking_spot(spot_id):
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({'msg': 'Admins only!'}), 403
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status != 'A':
        return jsonify({'msg': 'Cannot delete occupied spot'}), 400
    db.session.delete(spot)
    db.session.commit()
    return jsonify({'msg': 'Spot deleted'})

@app.route('/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({'msg': 'Admins only!'}), 403
    users = User.query.filter(User.role != 'admin').all()
    result = [{'id': u.id, 'username': u.username, 'email': u.email} for u in users]
    return jsonify(result)

@app.route('/admin/summary', methods=['GET'])
@jwt_required()
def admin_summary():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({'msg': 'Admins only!'}), 403
    lots = ParkingLot.query.count()
    spots = ParkingSpot.query.count()
    occupied = ParkingSpot.query.filter_by(status='O').count()
    users = User.query.filter(User.role != 'admin').count()
    return jsonify({
        'total_lots': lots,
        'total_spots': spots,
        'occupied_spots': occupied,
        'registered_users': users
    })

@app.route('/user/parking-lots', methods=['GET'])
@jwt_required()
@cache.cached(timeout=300, key_prefix='user_parking_lots')
def user_parking_lots():
    lots = ParkingLot.query.all()
    result = []
    for lot in lots:
        available_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        result.append({
            'id': lot.id,
            'prime_location_name': lot.prime_location_name,
            'price': lot.price,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'available_spots': available_spots,
            'number_of_spots': lot.number_of_spots
        })
    return jsonify(result)

@app.route('/user/search-parking-lots', methods=['GET'])
@jwt_required()
def search_parking_lots():
    query = request.args.get('query', '').strip()
    if not query:
        return jsonify({'msg': 'Query parameter is required'}), 400
    search = "%{}%".format(query)
    lots = ParkingLot.query.filter(
        db.or_(
            ParkingLot.prime_location_name.ilike(search),
            ParkingLot.address.ilike(search),
            ParkingLot.pin_code.ilike(search)
        )
    ).all()
    result = []
    for lot in lots:
        available_spots = ParkingSpot.query.filter_by(lot_id=lot.id, status='A').count()
        result.append({
            'id': lot.id,
            'prime_location_name': lot.prime_location_name,
            'price': lot.price,
            'address': lot.address,
            'pin_code': lot.pin_code,
            'available_spots': available_spots,
            'number_of_spots': lot.number_of_spots
        })
    return jsonify(result)

@app.route('/user/book', methods=['POST'])
@jwt_required()
def book_spot():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    lot_id = data.get('lot_id')
    lot = ParkingLot.query.get(lot_id)
    if not lot:
        return jsonify({'msg': 'Parking lot not found'}), 404
    spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='A').first()
    if not spot:
        return jsonify({'msg': 'No available spots in this lot'}), 400
    spot.status = 'O'
    reservation = ParkingReservation(
        spot_id=spot.id,
        user_id=current_user_id,
        parking_timestamp=datetime.now(),
        parking_cost=lot.price)
    db.session.add(reservation)
    db.session.commit()
    return jsonify({
        'msg': 'Spot booked!',
        'reservation_id': reservation.id,
        'spot_id': spot.id,
        'lot_id': lot.id,
        'parking_timestamp': reservation.parking_timestamp
    })

@app.route('/user/release', methods=['POST'])
@jwt_required()
def release_spot():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    reservation_id = data.get('reservation_id')
    reservation = ParkingReservation.query.filter_by(
        id=reservation_id, user_id=current_user_id, leaving_timestamp=None
    ).first()
    if not reservation:
        return jsonify({'msg': 'Active reservation not found'}), 404

    reservation.leaving_timestamp = datetime.now() 
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.status = 'A'
    db.session.commit()
    return jsonify({'msg': 'Spot released!', 'leaving_timestamp': reservation.leaving_timestamp})

@app.route('/user/history', methods=['GET'])
@jwt_required()
def user_history():
    current_user_id = get_jwt_identity()
    reservations = ParkingReservation.query.filter_by(user_id=current_user_id).all()
    result = []
    for res in reservations:
        lot = ParkingLot.query.get(ParkingSpot.query.get(res.spot_id).lot_id)
        result.append({
            'reservation_id': res.id,
            'lot': lot.prime_location_name,
            'spot_id': res.spot_id,
            'parking_timestamp': res.parking_timestamp,
            'leaving_timestamp': res.leaving_timestamp,
            'parking_cost': res.parking_cost
        })
    return jsonify(result)

@app.route('/user/summary', methods=['GET'])
@jwt_required()
def user_summary():
    current_user_id = get_jwt_identity()
    total_bookings = ParkingReservation.query.filter_by(user_id=current_user_id).count()
    active = ParkingReservation.query.filter_by(user_id=current_user_id, leaving_timestamp=None).count()
    total_spent = db.session.query(db.func.sum(ParkingReservation.parking_cost)).filter_by(user_id=current_user_id).scalar() or 0
    return jsonify({
        'total_bookings': total_bookings,
        'active_bookings': active,
        'total_spent': total_spent
    })

@celery.task
def export_user_history(user_id):
    user = User.query.get(user_id)
    reservations = ParkingReservation.query.filter_by(user_id=user_id).all()
    filename = f"user_{user_id}_history.csv"
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Reservation ID', 'Spot ID', 'Parking Time', 'Leaving Time', 'Cost'])
        for r in reservations:
            writer.writerow([r.id, r.spot_id, r.parking_timestamp, r.leaving_timestamp, r.parking_cost])
    print(f"CSV export ready for {user.username}")

@app.route('/user/bookings', methods=['GET'])
@jwt_required()
def user_bookings():
    user_id = int(get_jwt_identity())
    reservations = (
        db.session.query(ParkingReservation, ParkingSpot, ParkingLot)
        .join(ParkingSpot, ParkingReservation.spot_id == ParkingSpot.id)
        .join(ParkingLot, ParkingSpot.lot_id == ParkingLot.id)
        .filter(ParkingReservation.user_id == user_id)
        .order_by(ParkingReservation.parking_timestamp.desc())
        .all()
    )
    result = []
    for reservation, spot, lot in reservations:
        if reservation.leaving_timestamp:
            status = 'completed'
        elif reservation.parking_timestamp:
            status = 'occupied'
        else:
            status = 'active'
        result.append({
            'id': reservation.id,
            'prime_location_name': lot.prime_location_name,
            'address': lot.address,
            'spot_id': spot.id,
            'start_time': reservation.parking_timestamp.isoformat() if reservation.parking_timestamp else None,
            'end_time': reservation.leaving_timestamp.isoformat() if reservation.leaving_timestamp else None,
            'status': status,
            'parking_cost': reservation.parking_cost
        })
    return jsonify(result)

@app.route('/user/occupy-spot', methods=['POST'])
@jwt_required()
def occupy_spot():
    data = request.get_json()
    reservation_id = data.get('reservation_id')
    user_id = int(get_jwt_identity())
    reservation = ParkingReservation.query.filter_by(id=reservation_id, user_id=user_id).first()
    if not reservation:
        return jsonify({'msg': 'Reservation not found'}), 404
    if reservation.parking_timestamp:
        return jsonify({'msg': 'Spot already marked as occupied'}), 400
    reservation.parking_timestamp = datetime.now()
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.status = 'O'
    db.session.commit()
    return jsonify({'msg': 'Spot marked as occupied', 'parking_timestamp': reservation.parking_timestamp.isoformat()})

@app.route('/user/release-spot', methods=['POST'])
@jwt_required()
def release_spot_v2():
    data = request.get_json()
    reservation_id = data.get('reservation_id')
    user_id = int(get_jwt_identity())
    reservation = ParkingReservation.query.filter_by(id=reservation_id, user_id=user_id).first()
    if not reservation:
        return jsonify({'msg': 'Reservation not found'}), 404
    if reservation.leaving_timestamp:
        return jsonify({'msg': 'Spot already released'}), 400
    if not reservation.parking_timestamp:
        return jsonify({'msg': 'You must mark as occupied before releasing'}, 400)
    reservation.leaving_timestamp = datetime.now()
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.status = 'A'
    db.session.commit()
    return jsonify({'msg': 'Spot marked as released', 'leaving_timestamp': reservation.leaving_timestamp.isoformat()})

@app.route('/admin/parking-lots/<int:lot_id>', methods=['PUT'])
@jwt_required()
def update_parking_lot(lot_id):
    data = request.get_json()
    lot = ParkingLot.query.get_or_404(lot_id)
    lot.prime_location_name = data.get('prime_location_name', lot.prime_location_name)
    lot.address = data.get('address', lot.address)
    lot.pin_code = data.get('pin_code', lot.pin_code)
    lot.price = data.get('price', lot.price)
    old_spots = lot.number_of_spots
    new_spots = data.get('number_of_spots', lot.number_of_spots)
    if new_spots > old_spots:
        for i in range(old_spots + 1, new_spots + 1):
            new_spot = ParkingSpot(lot_id=lot.id, spot_number=i, status='A')
            db.session.add(new_spot)
        lot.number_of_spots = new_spots
    elif new_spots < old_spots:
        removable_spots = ParkingSpot.query.filter(
            ParkingSpot.lot_id == lot.id,
            ParkingSpot.spot_number > new_spots,
            ParkingSpot.status == 'A'
        ).all()
        if len(removable_spots) == (old_spots - new_spots):
            for spot in removable_spots:
                db.session.delete(spot)
            lot.number_of_spots = new_spots
        else:
            return jsonify({'msg': 'Cannot reduce spots unless extra spots are all available'}), 400
    db.session.commit()
    return jsonify({'msg': 'Parking lot updated'})

@app.route('/admin/summary-charts', methods=['GET'])
@jwt_required()
def admin_summary_charts():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({'msg': 'Admins only!'}), 403
    lots = ParkingLot.query.all()
    lot_labels = []
    bookings_per_lot = []
    occupancy_per_lot = []
    for lot in lots:
        lot_labels.append(lot.prime_location_name)
        bookings = ParkingReservation.query.join(ParkingSpot).filter(ParkingSpot.lot_id == lot.id).count()
        bookings_per_lot.append(bookings)
        occupied = ParkingSpot.query.filter_by(lot_id=lot.id, status='O').count()
        occupancy_per_lot.append(occupied)
    return jsonify({
        'lots': lot_labels,
        'bookings': bookings_per_lot,
        'occupancy': occupancy_per_lot
    })

@app.route('/user/summary-charts', methods=['GET'])
@jwt_required()
def user_summary_charts():
    current_user_id = get_jwt_identity()
    user = db.session.get(User, current_user_id) 
    bookings = ParkingReservation.query.filter_by(user_id=user.id).all()
    month_counts = defaultdict(int)
    lot_counts = defaultdict(int)
    total_spent = 0
    for b in bookings:
        if b.parking_timestamp:
            month = b.parking_timestamp.strftime('%b %Y')
            month_counts[month] += 1
        if b.spot_id:
            spot = db.session.get(ParkingSpot, b.spot_id) 
            if spot: 
                lot = db.session.get(ParkingLot, spot.lot_id) 
                if lot: 
                    lot_counts[lot.prime_location_name] += 1
        if b.parking_cost:
            total_spent += b.parking_cost
    months = sorted(month_counts.keys())
    bookings_per_month = [month_counts[m] for m in months]
    lots = list(lot_counts.keys())
    bookings_per_lot = [lot_counts[l] for l in lots]
    return jsonify({
        'months': months,
        'bookings_per_month': bookings_per_month,
        'lots': lots,
        'bookings_per_lot': bookings_per_lot,
        'total_spent': total_spent
    })

if __name__ == "__main__":
    app.run(debug=True)
