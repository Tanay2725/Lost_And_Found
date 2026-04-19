from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
from models import db, User, LostItem, FoundItem, ActivityLog
from datetime import datetime
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lostfound.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
CORS(app, supports_credentials=True)

# Create tables
with app.app_context():
    db.create_all()
    # Create demo user if none exists
    if not User.query.filter_by(email='demo@college.edu').first():
        demo = User(email='demo@college.edu', password='demo123', name='Demo Student')
        db.session.add(demo)
        db.session.commit()

# Helper: get current logged-in user
def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

# ---------- API ROUTES ----------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/lost', methods=['GET'])
def get_lost_items():
    items = LostItem.query.order_by(LostItem.reported_at.desc()).all()
    return jsonify([{
        'id': i.id,
        'name': i.name,
        'location': i.location,
        'desc': i.description,
        'reported_at': i.reported_at.strftime('%Y-%m-%d %H:%M')
    } for i in items])

@app.route('/api/found', methods=['GET'])
def get_found_items():
    items = FoundItem.query.order_by(FoundItem.reported_at.desc()).all()
    return jsonify([{
        'id': i.id,
        'name': i.name,
        'location': i.location,
        'desc': i.description,
        'reported_at': i.reported_at.strftime('%Y-%m-%d %H:%M')
    } for i in items])

@app.route('/api/activity', methods=['GET'])
def get_activity():
    logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(10).all()
    return jsonify([{
        'message': log.message,
        'created_at': log.created_at.strftime('%Y-%m-%d %H:%M'),
        'user': log.user.name
    } for log in logs])

@app.route('/api/report', methods=['POST'])
def report_item():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Please login first'}), 401
    
    data = request.get_json()
    item_type = data.get('type')  # 'lost' or 'found'
    name = data.get('name')
    location = data.get('location')
    description = data.get('desc', '')
    
    if not name or not location or not item_type:
        return jsonify({'error': 'Missing required fields'}), 400
    
    if item_type == 'lost':
        new_item = LostItem(name=name, location=location, description=description, user_id=user.id)
        db.session.add(new_item)
        msg = f"📢 New lost report: '{name}' at {location}"
    elif item_type == 'found':
        new_item = FoundItem(name=name, location=location, description=description, user_id=user.id)
        db.session.add(new_item)
        msg = f"✨ New found report: '{name}' at {location}"
    else:
        return jsonify({'error': 'Invalid type'}), 400
    
    # Add activity log
    activity = ActivityLog(message=msg, user_id=user.id)
    db.session.add(activity)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Item reported successfully'}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    if user and user.password == password:  # plain compare for demo
        session['user_id'] = user.id
        activity = ActivityLog(message=f"🔐 {user.name} logged in", user_id=user.id)
        db.session.add(activity)
        db.session.commit()
        return jsonify({'success': True, 'user': {'id': user.id, 'email': user.email, 'name': user.name}})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    user = get_current_user()
    if user:
        activity = ActivityLog(message=f"👋 {user.name} logged out", user_id=user.id)
        db.session.add(activity)
        db.session.commit()
    session.clear()
    return jsonify({'success': True})

@app.route('/api/me', methods=['GET'])
def me():
    user = get_current_user()
    if user:
        return jsonify({'id': user.id, 'email': user.email, 'name': user.name})
    return jsonify({'error': 'Not logged in'}), 401

if __name__ == '__main__':
    app.run(debug=True)