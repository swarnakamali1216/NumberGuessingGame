from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from datetime import datetime, timedelta
import logging
import json
import sys
import os
from dotenv import load_dotenv
from flask_seasurf import SeaSurf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load .env from parent directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

from werkzeug.middleware.proxy_fix import ProxyFix

# Initialize Flask App
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Security Extensions
csrf = SeaSurf(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://user:password@localhost:5432/guess_it_game'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ----- Production / security settings (override via environment) -----
# Use env vars to control these in production
app.config['ENV'] = os.getenv('FLASK_ENV', 'production')
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.config['REMEMBER_COOKIE_SECURE'] = app.config['SESSION_COOKIE_SECURE']
app.config['REMEMBER_COOKIE_HTTPONLY'] = True

# Session lifetime
try:
    lifetime = int(os.getenv('PERMANENT_SESSION_LIFETIME', '3600'))
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=lifetime)
except (ValueError, TypeError):
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# ----- Structured JSON logging for production-friendly logs -----
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'time': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'funcName': record.funcName,
        }
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)
        
        # Add extra fields if they exist
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
            
        return json.dumps(log_record, ensure_ascii=False)

# Configure root and app loggers (stream to stdout for container friendliness)
json_handler = logging.StreamHandler(stream=sys.stdout)
json_handler.setFormatter(JSONFormatter())

# Set logging level based on environment
log_level = logging.DEBUG if app.config['DEBUG'] else logging.INFO
json_handler.setLevel(log_level)

root_logger = logging.getLogger()
# Clear existing handlers to avoid duplicates
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
root_logger.addHandler(json_handler)
root_logger.setLevel(log_level)

# Explicitly set Flask's logger to use our handler
app.logger.handlers = root_logger.handlers
app.logger.setLevel(log_level)

@app.after_request
def add_security_headers(response):
    """Add security headers to every response engine"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self';"
    )
    
    if app.config.get('SESSION_COOKIE_SECURE'):
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
    return response

# Initialize Database
db = SQLAlchemy(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize OAuth (optional - only if credentials are provided)
oauth = OAuth(app)
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
OAUTH_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

if OAUTH_ENABLED:
    app.config['GOOGLE_CLIENT_ID'] = GOOGLE_CLIENT_ID
    app.config['GOOGLE_CLIENT_SECRET'] = GOOGLE_CLIENT_SECRET
    
    google = oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )
else:
    google = None

# ============== DATABASE MODELS ==============

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    name = db.Column(db.String(120), nullable=False)
    avatar_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    games = db.relationship('Game', back_populates='player', cascade='all, delete-orphan')
    profile = db.relationship('PlayerProfile', back_populates='user', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.name}>'

class PlayerProfile(db.Model):
    """Player statistics and profile"""
    __tablename__ = 'player_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    games_won = db.Column(db.Integer, default=0)
    games_lost = db.Column(db.Integer, default=0)
    best_score = db.Column(db.Integer, nullable=True)
    worst_score = db.Column(db.Integer, nullable=True)
    total_attempts = db.Column(db.Integer, default=0)
    current_streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    achievements = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', back_populates='profile')
    
    def __repr__(self):
        return f'<PlayerProfile {self.user.name}: {self.games_won}W-{self.games_lost}L>'

class Game(db.Model):
    """Individual game history"""
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # easy, medium, hard
    attempts = db.Column(db.Integer, nullable=False)
    won = db.Column(db.Boolean, default=False)
    secret_number = db.Column(db.Integer, nullable=False)
    guesses = db.Column(db.JSON, default=list)  # List of all guesses made
    played_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship
    player = db.relationship('User', back_populates='games')
    
    def __repr__(self):
        return f'<Game {self.user.name}: {self.difficulty} ({self.attempts} attempts)>'

# ============== LOGIN MANAGER ==============

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============== AUTHENTICATION ROUTES ==============

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    """Login page with Google OAuth and guest option"""
    if request.method == 'POST':
        # Guest login
        nickname = request.form.get('nickname', '').strip()
        if not nickname or len(nickname) < 2 or len(nickname) > 20:
            return render_template('login.html', error='Invalid nickname (2-20 characters)')
        
        # Create guest user
        guest_user = User(name=nickname, email=f'guest_{nickname}@local')
        db.session.add(guest_user)
        db.session.commit()
        
        # Create profile
        profile = PlayerProfile(user_id=guest_user.id)
        db.session.add(profile)
        db.session.commit()
        
        login_user(guest_user)
        session['player_name'] = nickname
        return redirect(url_for('game'))
    
    return render_template('login.html', oauth_enabled=OAUTH_ENABLED)

@app.route('/login/google')
@limiter.limit("5 per minute")
def login_google():
    """Redirect to Google OAuth"""
    if not OAUTH_ENABLED:
        return redirect(url_for('login'))
    try:
        redirect_uri = url_for('authorize_google', _external=True)
        app.logger.info(f"Initiating Google OAuth with redirect_uri: {redirect_uri}")
        return google.authorize_redirect(redirect_uri)
    except Exception as e:
        app.logger.error(f"Google OAuth redirect error: {repr(e)}")
        return redirect(url_for('login'))

@app.route('/authorize/google')
def authorize_google():
    """Handle Google OAuth callback"""
    if not OAUTH_ENABLED:
        return redirect(url_for('login'))
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            # Check if user exists
            user = User.query.filter_by(google_id=user_info['sub']).first()
            
            if not user:
                # Create new user
                user = User(
                    google_id=user_info['sub'],
                    email=user_info['email'],
                    name=user_info['name'],
                    avatar_url=user_info.get('picture')
                )
                db.session.add(user)
                db.session.commit()
                
                # Create profile
                profile = PlayerProfile(user_id=user.id)
                db.session.add(profile)
                db.session.commit()
            
            login_user(user)
            session['player_name'] = user.name
            session['user_email'] = user.email
            app.logger.info(f"User {user.name} logged in via Google OAuth")
            return redirect(url_for('game'))
    except Exception as e:
        app.logger.error(f"Google OAuth Error: {repr(e)}", exc_info=True)
        return render_template('login.html', error=f'Google login failed: {str(e)}', oauth_enabled=OAUTH_ENABLED)
    
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Logout user"""
    logout_user()
    session.clear()
    return redirect(url_for('index'))

# ============== GAME ROUTES ==============

@app.route('/')
def index():
    """Home - redirect to game or login"""
    if current_user.is_authenticated:
        return redirect(url_for('game'))
    # Render the login page at root so users land on the login/guest screen
    return render_template('login.html', oauth_enabled=OAUTH_ENABLED)

@app.route('/game', methods=['GET', 'POST'])
@login_required
def game():
    """Main game interface"""
    player_name = current_user.name
    user_id = current_user.id
    
    if request.method == 'POST':
        if 'difficulty' in request.form:
            # Change difficulty - start new game
            difficulty = request.form.get('difficulty', 'medium')
            init_game(user_id, difficulty)
            return redirect(url_for('game'))
        
        elif 'guess' in request.form:
            # Process guess
            try:
                guess = int(request.form.get('guess', 0))
                return process_guess(user_id, guess)
            except ValueError:
                return render_template('game.html', 
                    message='❌ Please enter a valid number',
                    feedback_class='error')
    
    # Get current game or create one
    current_game = get_current_game(user_id)
    if not current_game:
        init_game(user_id, 'medium')
        current_game = get_current_game(user_id)
    
    # Get leaderboard
    leaderboard = get_leaderboard(5)
    
    # Default values if game retrieval fails
    message = 'Make your first guess!'
    feedback_class = 'info'
    attempts = 0
    difficulty = 'medium'
    
    if current_game:
        message = current_game.get('message', message)
        feedback_class = current_game.get('feedback_class', feedback_class)
        attempts = current_game.get('attempts', attempts)
        difficulty = current_game.get('difficulty', difficulty)
    
    return render_template('game.html',
        message=message,
        feedback_class=feedback_class,
        player_name=player_name,
        attempts=attempts,
        difficulty=difficulty,
        leaderboard=leaderboard)

def init_game(user_id, difficulty='medium'):
    """Initialize new game"""
    import random
    ranges = {'easy': (1, 50), 'medium': (1, 100), 'hard': (1, 500)}
    low, high = ranges.get(difficulty, (1, 100))
    
    game = Game(
        user_id=user_id,
        difficulty=difficulty,
        secret_number=random.randint(low, high),
        attempts=0,
        won=False
    )
    db.session.add(game)
    db.session.commit()
    
    session['current_game_id'] = game.id

def get_current_game(user_id):
    """Get active game from session"""
    game_id = session.get('current_game_id')
    if not game_id:
        return None
    
    game = Game.query.get(game_id)
    if not game or game.user_id != user_id:
        return None
    
    data = {
        'id': game.id,
        'difficulty': game.difficulty,
        'attempts': game.attempts,
        'message': f'Guess a number between {get_range(game.difficulty)[0]} and {get_range(game.difficulty)[1]}',
        'feedback_class': 'info'
    }
    
    return data

def get_range(difficulty):
    """Get number range for difficulty"""
    ranges = {'easy': (1, 50), 'medium': (1, 100), 'hard': (1, 500)}
    return ranges.get(difficulty, (1, 100))

def process_guess(user_id, guess):
    """Process player's guess"""
    game_id = session.get('current_game_id')
    game = Game.query.get(game_id)
    
    if not game or game.user_id != user_id:
        return redirect(url_for('game'))
    
    low, high = get_range(game.difficulty)
    
    # Validate guess
    if guess < low or guess > high:
        return render_template('game.html',
            message=f'❌ Please guess between {low} and {high}',
            feedback_class='error',
            player_name=current_user.name,
            attempts=game.attempts,
            difficulty=game.difficulty)
    
    game.attempts += 1
    game.guesses.append(guess)
    db.session.commit()
    
    message = f'Guess a number between {low} and {high}'
    feedback_class = 'info'
    game_won = False
    
    if guess == game.secret_number:
        # CORRECT!
        message = f'🎉 CORRECT! You won in {game.attempts} attempts!'
        feedback_class = 'success'
        game_won = True
        game.won = True
        game.completed_at = datetime.utcnow()
        
        # Update profile
        update_player_profile(user_id, game.attempts)
        db.session.commit()
        
        session.pop('current_game_id', None)
    else:
        diff = abs(guess - game.secret_number)
        if diff <= 5:
            message = f"🔥 Very Close! {'Too low' if guess < game.secret_number else 'Too high'}"
            feedback_class = 'hot'
        elif diff <= 15:
            message = f"🌡️ Warm... {'Too low' if guess < game.secret_number else 'Too high'}"
            feedback_class = 'warm'
        elif diff <= 30:
            message = f"❄️ Cold... {'Too low' if guess < game.secret_number else 'Too high'}"
            feedback_class = 'cold'
        else:
            message = f"❌ Way off! {'Too low' if guess < game.secret_number else 'Too high'}"
            feedback_class = 'error'
        
        db.session.commit()
    
    leaderboard = get_leaderboard(5)
    
    return render_template('game.html',
        message=message,
        feedback_class=feedback_class,
        player_name=current_user.name,
        attempts=game.attempts,
        game_won=game_won,
        difficulty=game.difficulty,
        leaderboard=leaderboard)

def update_player_profile(user_id, attempts):
    """Update player profile after game win"""
    profile = PlayerProfile.query.filter_by(user_id=user_id).first()
    
    if profile:
        profile.games_won += 1
        profile.current_streak += 1
        profile.total_attempts += attempts
        
        if profile.best_score is None or attempts < profile.best_score:
            profile.best_score = attempts
        if profile.worst_score is None or attempts > profile.worst_score:
            profile.worst_score = attempts
        if profile.current_streak > profile.best_streak:
            profile.best_streak = profile.current_streak
        
        # Check achievements
        if attempts == 1 and '🎯 One-Shot Wonder' not in profile.achievements:
            profile.achievements.append('🎯 One-Shot Wonder')
        if profile.current_streak == 3 and '🔥 Hot Streak' not in profile.achievements:
            profile.achievements.append('🔥 Hot Streak')
        if profile.games_won == 10 and '🏆 Veteran' not in profile.achievements:
            profile.achievements.append('🏆 Veteran')

@app.route('/profile')
@login_required
def profile():
    """Player's profile page"""
    profile_data = PlayerProfile.query.filter_by(user_id=current_user.id).first()
    
    if not profile_data:
        profile_data = PlayerProfile(user_id=current_user.id)
        db.session.add(profile_data)
        db.session.commit()
    
    return render_template('profile.html',
        player_name=current_user.name,
        profile=profile_data)

@app.route('/leaderboard')
def leaderboard():
    """Public leaderboard"""
    scores = get_leaderboard(None)
    return render_template('leaderboard.html', leaderboard=scores)

def get_leaderboard(limit=None):
    """Get public leaderboard"""
    query = db.session.query(
        User.name,
        PlayerProfile.best_score,
        PlayerProfile.games_won
    ).join(PlayerProfile).filter(
        PlayerProfile.best_score.isnot(None)
    ).order_by(PlayerProfile.best_score.asc())
    
    if limit:
        query = query.limit(limit)
    
    return [{'name': row[0], 'best_score': row[1], 'wins': row[2]} for row in query.all()]

@app.route('/new-game')
@login_required
def new_game():
    """Start a new game"""
    session.pop('current_game_id', None)
    init_game(current_user.id, 'medium')
    return redirect(url_for('game'))

@app.route('/admin', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def admin_login():
    """Admin login"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if password == os.getenv('ADMIN_PASSWORD', 'admin123'):
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error='Invalid password')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin user management"""
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    users = User.query.all()
    stats_list = []
    
    for user in users:
        profile = user.profile
        if profile:
            stats_list.append({
                'name': user.name,
                'email': user.email or 'Guest',
                'games_won': profile.games_won,
                'games_lost': profile.games_lost,
                'best_score': profile.best_score,
                'current_streak': profile.current_streak,
                'total_attempts': profile.total_attempts,
                'achievements': len(profile.achievements)
            })
    
    stats_list.sort(key=lambda x: x['games_won'], reverse=True)
    
    return render_template('admin_dashboard.html',
        players=stats_list,
        total_users=len(users))

@app.route('/admin/logout')
def admin_logout():
    """Logout from admin"""
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/privacy')
def privacy_policy():
    """Privacy Policy Page"""
    return render_template('privacy.html')

@app.route('/terms')
def terms_of_service():
    """Terms of Service Page"""
    return render_template('terms.html')

# ============== ERROR HANDLERS ==============

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

# ============== CREATE DATABASE ==============

with app.app_context():
    # In production use Alembic migrations instead of create_all().
    # To allow quick local setup you can enable automatic create by
    # setting the environment variable ENABLE_DB_CREATE=true
    if os.getenv('ENABLE_DB_CREATE', 'false').lower() == 'true':
        db.create_all()
    else:
        app.logger.info('Database creation skipped — use Alembic migrations (ENABLE_DB_CREATE=true to force).')

if __name__ == '__main__':
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=5000)
