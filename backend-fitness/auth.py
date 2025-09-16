import sqlite3
import hashlib
import secrets
import jwt
import datetime
from functools import wraps
from flask import request, jsonify
import re
import os
import random

# JWT utilities - FIXED SECRET KEY ISSUE
def get_or_create_secret_key():
    """Get existing secret key or create a persistent one"""
    key_file = 'jwt_secret.key'
    if os.path.exists(key_file):
        with open(key_file, 'r') as f:
            return f.read().strip()
    else:
        key = secrets.token_urlsafe(32)
        with open(key_file, 'w') as f:
            f.write(key)
        return key

# Use persistent secret key instead of regenerating on each restart
SECRET_KEY = get_or_create_secret_key()
JWT_EXPIRATION_HOURS = 24

print(f"Using JWT secret key: {SECRET_KEY[:10]}...")  # Debug log

# Database setup
def init_db():
    """Initialize the database with users and sessions tables"""
    conn = None
    try:
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Create a table for user sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                token_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                challenge_date DATE NOT NULL,
                exercise TEXT NOT NULL,
                is_completed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(user_id, challenge_date)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exercise_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                exercise_type TEXT NOT NULL,
                reps_count INTEGER NOT NULL,
                log_date DATE NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        print("Database initialized successfully")
        
    except sqlite3.Error as e:
        print(f"Error initializing database: {e}")
    finally:
        if conn:
            conn.close()

# Password hashing utilities
def generate_salt():
    """Generate a random salt for password hashing"""
    return secrets.token_hex(16)

def hash_password(password, salt):
    """Hash a password with salt using SHA-256"""
    return hashlib.sha256((password + salt).encode()).hexdigest()

def verify_password(password, salt, stored_hash):
    """Verify a password against stored hash"""
    return hash_password(password, salt) == stored_hash

def generate_jwt_token(user_id, email):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    print(f"Generated token for user {user_id}: {token[:20]}...")  # Debug log
    return token

def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        print(f"Verifying token: {token[:20]}... with secret: {SECRET_KEY[:10]}...")  # Debug log
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        print(f"Token verification successful: {payload}")  # Debug log
        return payload
    except jwt.ExpiredSignatureError:
        print("Token expired")  # Debug log
        return None
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")  # Debug log
        return None
    except Exception as e:
        print(f"Token verification error: {e}")  # Debug log
        return None

# Database operations
def create_user(email, password):
    """Create a new user in the database"""
    with sqlite3.connect('fitness_tracker.db') as conn:
        try:
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            if cursor.fetchone():
                return {'success': False, 'error': 'User with this email already exists'}
            
            # Generate salt and hash password
            salt = generate_salt()
            password_hash = hash_password(password, salt)
            
            # Insert new user
            cursor.execute('''
                INSERT INTO users (email, password_hash, salt)
                VALUES (?, ?, ?)
            ''', (email, password_hash, salt))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            return {'success': True, 'user_id': user_id, 'email': email}
            
        except sqlite3.Error as e:
            conn.rollback()
            return {'success': False, 'error': f'Database error: {str(e)}'}

def authenticate_user(email, password):
    """Authenticate user login"""
    with sqlite3.connect('fitness_tracker.db') as conn:
        try:
            cursor = conn.cursor()
            
            # Get user data
            cursor.execute('''
                SELECT id, email, password_hash, salt 
                FROM users WHERE email = ?
            ''', (email,))
            
            user_data = cursor.fetchone()
            
            if not user_data:
                return {'success': False, 'error': 'Invalid email or password'}
            
            user_id, email, stored_hash, salt = user_data
            
            # Verify password
            if not verify_password(password, salt, stored_hash):
                return {'success': False, 'error': 'Invalid email or password'}
            
            # Update last login
            cursor.execute('''
                UPDATE users SET last_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user_id,))
            
            conn.commit()
            
            return {'success': True, 'user_id': user_id, 'email': email}
            
        except sqlite3.Error as e:
            conn.rollback()
            return {'success': False, 'error': f'Database error: {str(e)}'}

def get_user_by_id(user_id):
    """Get user information by ID"""
    with sqlite3.connect('fitness_tracker.db') as conn:
        try:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, email, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            
            if user_data:
                return {
                    'user_id': user_data[0],  # Changed from 'id' to 'user_id' for consistency
                    'email': user_data[1],
                    'created_at': user_data[2],
                    'last_login': user_data[3]
                }
            return None
            
        except sqlite3.Error as e:
            print(f"Error getting user by ID: {e}")
            return None

# ENHANCED Authentication decorator with detailed debugging
def token_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        print("\n=== TOKEN AUTHENTICATION DEBUG ===")
        auth_header = request.headers.get('Authorization')
        print(f"1. Auth header received: {auth_header}")
        
        if not auth_header:
            print("ERROR: No Authorization header found")
            return jsonify({'error': 'Authorization token is missing'}), 401
        
        try:
            # Handle both "Bearer token" and just "token" formats
            if auth_header.startswith('Bearer '):
                token = auth_header.split(" ")[1]
            else:
                token = auth_header
            
            print(f"2. Extracted token: {token[:20]}...")
            
            # Verify the token
            payload = verify_jwt_token(token)
            print(f"3. Token payload: {payload}")
            
            if not payload:
                print("ERROR: Token verification failed")
                return jsonify({'error': 'Token is invalid or expired'}), 401
            
            # Get user details to ensure user still exists
            user_data = get_user_by_id(payload['user_id'])
            if not user_data:
                print(f"ERROR: User {payload['user_id']} not found in database")
                return jsonify({'error': 'User not found'}), 401
            
            # Add user info to request context
            request.current_user = user_data
            print(f"4. SUCCESS: User {user_data['email']} authenticated")
            print("=== TOKEN AUTHENTICATION SUCCESS ===\n")
            
        except IndexError:
            print("ERROR: Invalid token format")
            return jsonify({'error': 'Token format is invalid. Use "Bearer <token>"'}), 401
        except Exception as e:
            print(f"ERROR: Token validation exception: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Token validation failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated

# Session management
def create_session(user_id, token):
    """Create a user session record with a hashed token"""
    with sqlite3.connect('fitness_tracker.db') as conn:
        try:
            cursor = conn.cursor()
            
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
            
            cursor.execute('''
                INSERT INTO user_sessions (user_id, token_hash, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, token_hash, expires_at))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error creating session: {e}")
            conn.rollback()
            return False

def invalidate_session(token):
    """Invalidate a user session by hashing the token and marking it inactive"""
    with sqlite3.connect('fitness_tracker.db') as conn:
        try:
            cursor = conn.cursor()
            
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            
            cursor.execute('''
                UPDATE user_sessions 
                SET is_active = FALSE 
                WHERE token_hash = ?
            ''', (token_hash,))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"Error invalidating session: {e}")
            conn.rollback()
            return False

# Input validation
def validate_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Password validation - at least 6 characters"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, "Password is valid"

def get_daily_challenge(user_id):
    """Retrieve or create today's daily challenge for the user."""
    with sqlite3.connect('fitness_tracker.db') as conn:
        try:
            cursor = conn.cursor()
            today = datetime.datetime.utcnow().date()
            
            # Check for existing challenge
            cursor.execute('''
                SELECT challenge_date, exercise, is_completed
                FROM daily_challenges
                WHERE user_id = ? AND challenge_date = ?
            ''', (user_id, today))
            
            challenge_data = cursor.fetchone()
            
            if challenge_data:
                return {
                    'date': challenge_data[0],
                    'exercise': challenge_data[1],
                    'is_completed': bool(challenge_data[2])
                }
            else:
                # Create a new challenge
                available_exercises = ['squats', 'pushups', 'araimandi', 'mulumandi', 'mandia_davu']
                new_exercise = random.choice(available_exercises)
                
                cursor.execute('''
                    INSERT INTO daily_challenges (user_id, challenge_date, exercise, is_completed)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, today, new_exercise, False))
                
                conn.commit()
                return {
                    'date': str(today),
                    'exercise': new_exercise,
                    'is_completed': False
                }
        except sqlite3.Error as e:
            print(f"Database error in get_daily_challenge: {e}")
            conn.rollback()
            return None

def complete_daily_challenge(user_id, exercise):
    """Mark the daily challenge as completed if the exercise matches."""
    with sqlite3.connect('fitness_tracker.db') as conn:
        try:
            cursor = conn.cursor()
            today = datetime.datetime.utcnow().date()
            
            # Check if the user's daily challenge matches the completed exercise
            cursor.execute('''
                SELECT id FROM daily_challenges
                WHERE user_id = ? AND challenge_date = ? AND exercise = ? AND is_completed = FALSE
            ''', (user_id, today, exercise))
            
            challenge_id = cursor.fetchone()
            
            if challenge_id:
                cursor.execute('''
                    UPDATE daily_challenges
                    SET is_completed = TRUE
                    WHERE id = ?
                ''', (challenge_id[0],))
                
                conn.commit()
                return {'success': True, 'message': 'Daily challenge completed'}
            
            return {'success': False, 'message': 'No matching pending challenge found'}
            
        except sqlite3.Error as e:
            print(f"Database error in complete_daily_challenge: {e}")
            conn.rollback()
            return {'success': False, 'message': 'Failed to update challenge status'}

# Initialize database when module is imported
init_db()