from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import secrets
import random
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scavenger_hunt.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
CORS(app)

db = SQLAlchemy(app)

# Admin credentials
ADMIN_USERNAME = "acsisdabestadmin"
ADMIN_PASSWORD = "ACSchili2025admin"

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    team = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(128))
    points = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    puzzle_order = db.Column(db.Text)
    current_puzzle_index = db.Column(db.Integer, default=0)
    warnings = db.Column(db.Integer, default=0)
    is_banned = db.Column(db.Boolean, default=False)
    ban_reason = db.Column(db.String(200))
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.relationship('Progress', backref='user', lazy=True, cascade='all, delete-orphan')

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    puzzle_piece = db.Column(db.Integer, nullable=False)
    location_confirmed = db.Column(db.Boolean, default=False)
    question_attempts = db.Column(db.Integer, default=0)
    question_correct = db.Column(db.Boolean, default=False)
    points_earned = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime)

# Location pins - CHANGE THESE TO YOUR ACTUAL PINS!
LOCATION_PINS = {
    1: "312297", 2: "119082", 3: "812942", 4: "806632",
    5: "539485", 6: "954074", 7: "629241", 8: "701793", 
    9: "231366", 10: "203102", 11: "762586", 12: "700624",
    13: "449006", 14: "815838", 15: "816937", 16: "273797"
}

CHEMISTRY_QUESTIONS = {
    1: {
        "question": "Which functional group is present in vanillin, the main compound in vanilla?",
        "options": ["Alcohol (-OH)", "Aldehyde (-CHO)", "Carboxylic acid (-COOH)", "Ester (-COOR)"],
        "answer": 1
    },
    2: {
        "question": "The pungency of mustard seeds is due to compounds formed when seeds are crushed. These are:",
        "options": ["Alkaloids", "Terpenes", "Isothiocyanates", "Amino acids"],
        "answer": 2
    },
    3: {
        "question": "3. Nutmeg contains myristicin, a compound with psychoactive properties. To which chemical family does it belong?",
        "options": ["Phenylpropanoids", "Carotenoids", "Amines", "Flavonoids"],
        "answer": 0
    },
    4: {
        "question": "Which spice is rich in allyl sulfides, compounds responsible for both aroma and health benefits?",
        "options": ["Garlic", "Cinnamon", "Ginger", "Cardamom"],
        "answer": 0
    },
    5: {
        "question": "The compound responsible for the yellow color of turmeric is:",
        "options": ["Capsaicin", "Curcumin", "Piperine", "Eugenol"],
        "answer": 1
    },
    6: {
        "question": "The “cooling” sensation of mint or cardamom is due to compounds that activate which type of receptors?",
        "options": ["Heat receptors", "Cold receptors (TRPM8 channels)", "Pain receptors", "Sweet taste receptors"],
        "answer": 1
    },
    7: {
        "question": "What type of organic molecule is eugenol, the main active compound in cloves?",
        "options": ["Carbohydrate", "Terpenoid alcohol", "Phenolic alcohol", "Protein"],
        "answer": 2
    },
    8: {
        "question": "Which spice was once so valuable it was used as currency?",
        "options": ["Cinnamon", "Paprika", "Turmeric", "Black pepper"],
        "answer": 3
    },
    9: {
        "question": "Capsaicin, the compound that makes chili peppers “hot,” is most concentrated in:",
        "options": ["The seeds", "The skin", "The stem", "The white pith/placenta"],
        "answer": 3
    },
    10: {
        "question": "The “bite” of black pepper comes from which molecule?",
        "options": ["Capsaicin", "Curcumin", "Piperine", "Eugenol"],
        "answer": 2
    },
    11: {
        "question": "Curcumin, studied for its anti-inflammatory effects, is found in which spice?",
        "options": ["Tumeric", "Cinnamon", "Clove", "Nutmeg"],
        "answer": 0
    },
    12: {
        "question": "The double bonds in many spice-derived molecules can undergo:",
        "options": ["Hydrogenation", "Hydrolysis", "All of the above", "None of the above"],
        "answer": 2
    },
    13: {
        "question": "The bright red pigment in paprika and chili peppers belongs to which class of organic compounds?",
        "options": ["Anthocyanins", "Carotenoids", "Alkaloids", "Phenols"],
        "answer": 1
    },
    14: {
        "question": "Which spice owes its distinctive blue color in essential oil to the compound chamazulene, formed during distillation?",
        "options": ["Ginger", "Blue chamomile", "Clove", "Nutmeg"],
        "answer": 1
    },
    15: {
        "question": "The compound responsible for the aroma of citrus peels, sometimes found in coriander and cardamom oils, is:",
        "options": ["Eugenol", "Vanillin", "Myrcene", "Limonene"],
        "answer": 3
    },
    16: {
        "question": "Cinnamaldehyde can be oxidized to which organic compound?",
        "options": ["Cinnamic acid", "Benzyl alcohol", "Benzaldehyde", "Phenol"],
        "answer": 0
    }
}

# Location hints - CUSTOMIZE THESE FOR YOUR CAMPUS!
LOCATION_HINTS = {
    1: "Where you go for safety concerns and to get your student ID (security desk)",
    2: "Where you go to report any incidents that occurred on campus (student services)",
    3: "Where you can get your school-provided devices and ask questions or report concerns about your student account (IT)",
    4: "Where you can get free printing services (hint: it's on the 1st floor)",
    5: "Where you go for chemistry tutoring provided by ACS (bonding with chemistry)",
    6: "Where you for to ask about the library resources available to students (library help desk)",
    7: "Where you go to pay for tuition or any pending balances (business services)",
    8: "Where you go to check in for financial aid services (welcome center wright stop)",
    9: "Where you go to meet your transfer advisor (advising and transfer center)",
    10: "Where you get your resume fixed up and learn about internship/work opportunities (career center)",
    11: "Where you can go for tutoring and writing support outside of the engineering center (tutoring/writing center)",
    12: "Where you can heat up your food, buy snacks from the vending machines, and purchase hot meals (cafeteria)",
    13: "Where you go for mental health and wellness support (wellness center)",
    14: "Where you go to learn about resources available to first year students (first year experience center)",
    15: "Where you go for student organization related concerns and questions (activities and special events center)",
    16: "Where you go to meet your student government officers and learn about campus initiatives (SGA office)"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    
    existing = User.query.filter_by(
        first_name=data['first_name'],
        last_name=data['last_name']
    ).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'User already exists'}), 400
    
    # Create randomized puzzle order
    puzzle_order = list(range(1, 17))
    random.shuffle(puzzle_order)
    
    user = User(
        first_name=data['first_name'],
        last_name=data['last_name'],
        team=data['team'],
        password_hash=generate_password_hash(data['password']),
        puzzle_order=json.dumps(puzzle_order),
        current_puzzle_index=0
    )
    
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    return jsonify({'success': True, 'user_id': user.id})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    
    user = User.query.filter_by(
        first_name=data['first_name'],
        last_name=data['last_name']
    ).first()
    
    if user and check_password_hash(user.password_hash, data['password']):
        session['user_id'] = user.id
        return jsonify({'success': True, 'user_id': user.id})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/admin_login', methods=['POST'])
def admin_login():
    data = request.json
    
    if data['username'] == ADMIN_USERNAME and data['password'] == ADMIN_PASSWORD:
        session['is_admin'] = True
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401

@app.route('/profile/<int:user_id>')
def profile(user_id):
    if 'user_id' not in session or session['user_id'] != user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get_or_404(user_id)
    
    if user.is_banned:
        return jsonify({
            'error': 'banned',
            'message': f'Your account has been banned. Reason: {user.ban_reason}'
        }), 403
    
    user.last_activity = datetime.utcnow()
    db.session.commit()
    
    progress = Progress.query.filter_by(user_id=user_id).all()
    puzzle_order = json.loads(user.puzzle_order) if user.puzzle_order else list(range(1, 17))
    
    puzzle_status = {}
    for i in range(1, 17):
        p = next((x for x in progress if x.puzzle_piece == i), None)
        puzzle_status[i] = {
            'unlocked': p is not None,
            'location_confirmed': p.location_confirmed if p else False,
            'question_correct': p.question_correct if p else False,
            'attempts': p.question_attempts if p else 0
        }
    
    current_hint = None
    if user.current_puzzle_index < 16:
        current_puzzle = puzzle_order[user.current_puzzle_index]
        current_hint = LOCATION_HINTS[current_puzzle]
    
    return jsonify({
        'user': {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'team': user.team,
            'points': user.points,
            'warnings': user.warnings
        },
        'puzzle_status': puzzle_status,
        'puzzle_order': puzzle_order,
        'current_puzzle_index': user.current_puzzle_index,
        'current_hint': current_hint
    })

@app.route('/verify_location', methods=['POST'])
def verify_location():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    puzzle_piece = data['puzzle_piece']
    pin = data['pin']
    
    if LOCATION_PINS.get(puzzle_piece) == pin:
        user_id = session['user_id']
        progress = Progress.query.filter_by(
            user_id=user_id,
            puzzle_piece=puzzle_piece
        ).first()
        
        if not progress:
            progress = Progress(user_id=user_id, puzzle_piece=puzzle_piece)
            db.session.add(progress)
        
        progress.location_confirmed = True
        db.session.commit()
        
        return jsonify({
            'success': True,
            'question': CHEMISTRY_QUESTIONS[puzzle_piece]
        })
    
    return jsonify({'success': False, 'message': 'Invalid PIN'}), 400

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    puzzle_piece = data['puzzle_piece']
    answer = data['answer']
    user_id = session['user_id']
    
    progress = Progress.query.filter_by(
        user_id=user_id,
        puzzle_piece=puzzle_piece
    ).first()
    
    if not progress or not progress.location_confirmed:
        return jsonify({'error': 'Location not confirmed'}), 400
    
    if progress.question_correct:
        return jsonify({'error': 'Question already answered correctly'}), 400
    
    progress.question_attempts += 1
    correct = CHEMISTRY_QUESTIONS[puzzle_piece]['answer'] == answer
    
    if correct:
        progress.question_correct = True
        points = [100, 75, 50, 25][min(progress.question_attempts - 1, 3)]
        progress.points_earned = points
        progress.completed_at = datetime.utcnow()
        
        user = User.query.get(user_id)
        user.points += points
        
        puzzle_order = json.loads(user.puzzle_order)
        current_index = puzzle_order.index(puzzle_piece)
        if current_index == user.current_puzzle_index:
            user.current_puzzle_index = min(user.current_puzzle_index + 1, 15)
        
        all_progress = Progress.query.filter_by(user_id=user_id).all()
        if len([p for p in all_progress if p.question_correct]) == 16:
            user.points += 100
    
    db.session.commit()
    
    next_hint = None
    if correct or progress.question_attempts >= 4:
        user = User.query.get(user_id)
        puzzle_order = json.loads(user.puzzle_order)
        
        if user.current_puzzle_index < 16:
            next_puzzle = puzzle_order[user.current_puzzle_index]
            next_hint = LOCATION_HINTS[next_puzzle]
    
    return jsonify({
        'correct': correct,
        'attempts': progress.question_attempts,
        'next_hint': next_hint,
        'points_earned': progress.points_earned if correct else 0
    })

@app.route('/leaderboard')
def leaderboard():
    teams = db.session.query(
        User.team,
        db.func.sum(User.points).label('total_points')
    ).group_by(User.team).order_by(db.desc('total_points')).all()
    
    return jsonify([{
        'team': team,
        'points': points
    } for team, points in teams])

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'is_admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    team_filter = request.args.get('team', 'all')
    sort_by = request.args.get('sort', 'points')
    search = request.args.get('search', '')
    
    query = User.query
    if team_filter != 'all':
        query = query.filter_by(team=team_filter)
    if search:
        query = query.filter(
            db.or_(
                User.first_name.contains(search),
                User.last_name.contains(search)
            )
        )
    
    if sort_by == 'points':
        query = query.order_by(User.points.desc())
    elif sort_by == 'activity':
        query = query.order_by(User.last_activity.desc())
    
    users = query.all()
    user_data = []
    
    for user in users:
        progress = Progress.query.filter_by(user_id=user.id).order_by(Progress.completed_at).all()
        completed = len([p for p in progress if p.question_correct])
        
        completion_times = []
        for p in progress:
            if p.completed_at:
                time_diff = (p.completed_at - user.created_at).total_seconds() / 60
                completion_times.append({
                    'puzzle': p.puzzle_piece,
                    'time': round(time_diff, 1),
                    'points': p.points_earned,
                    'attempts': p.question_attempts
                })
        
        if user.last_activity:
            minutes_ago = (datetime.utcnow() - user.last_activity).total_seconds() / 60
            if minutes_ago < 10:
                activity_status = 'active'
            elif minutes_ago < 20:
                activity_status = 'idle'
            else:
                activity_status = 'inactive'
        else:
            activity_status = 'unknown'
        
        user_data.append({
            'id': user.id,
            'name': f"{user.first_name} {user.last_name}",
            'team': user.team,
            'points': user.points,
            'completed_puzzles': completed,
            'warnings': user.warnings,
            'is_banned': user.is_banned,
            'activity_status': activity_status,
            'last_activity': user.last_activity.strftime('%H:%M:%S') if user.last_activity else 'Never',
            'completion_times': completion_times,
            'average_time': round(sum(t['time'] for t in completion_times) / len(completion_times), 1) if completion_times else 0
        })
    
    team_stats = db.session.query(
        User.team,
        db.func.sum(User.points).label('total_points'),
        db.func.count(User.id).label('player_count')
    ).group_by(User.team).all()
    
    return jsonify({
        'users': user_data,
        'team_stats': [{
            'team': team,
            'points': points or 0,
            'players': count
        } for team, points, count in team_stats],
        'total_players': len(users),
        'active_players': sum(1 for u in user_data if u['activity_status'] == 'active')
    })

@app.route('/admin/warn_user/<int:user_id>', methods=['POST'])
def warn_user(user_id):
    if 'is_admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    message = data.get('message', 'You have received a warning for suspicious activity.')
    
    user = User.query.get_or_404(user_id)
    user.warnings += 1
    db.session.commit()
    
    return jsonify({
        'success': True,
        'warnings': user.warnings
    })

@app.route('/admin/ban_user/<int:user_id>', methods=['POST'])
def ban_user(user_id):
    if 'is_admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    reason = data.get('reason', 'Cheating detected')
    
    user = User.query.get_or_404(user_id)
    user.is_banned = True
    user.ban_reason = reason
    user.points = 0
    
    Progress.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/admin/unban_user/<int:user_id>', methods=['POST'])
def unban_user(user_id):
    if 'is_admin' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user = User.query.get_or_404(user_id)
    user.is_banned = False
    user.ban_reason = None
    user.warnings = 0
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5003)