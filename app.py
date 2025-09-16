import sqlite3
import hashlib
import secrets
import jwt
import datetime
import random
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import base64
import os
import uuid
import io

# Import all necessary functions from the local auth module
from auth import (
    create_user,
    authenticate_user,
    generate_jwt_token,
    create_session,
    validate_email,
    validate_password,
    invalidate_session,
    get_user_by_id,
    token_required,
    get_daily_challenge,
    complete_daily_challenge,
    verify_jwt_token
)

app = Flask(__name__)
CORS(app)

# NEW: Functions to handle database interactions
def log_exercise_data(user_id, exercise_type, reps_count):
    """Log the user's exercise data to the database."""
    conn = None
    try:
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        today = datetime.datetime.utcnow().date()
        
        cursor.execute('''
            INSERT INTO exercise_logs (user_id, exercise_type, reps_count, log_date)
            VALUES (?, ?, ?, ?)
        ''', (user_id, exercise_type, reps_count, today))
        
        conn.commit()
        print("Exercise data logged successfully.")
        return True
    except sqlite3.Error as e:
        print(f"Database error logging exercise data: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_progress(user_id):
    """Retrieve summarized daily progress for a user."""
    conn = None
    try:
        conn = sqlite3.connect('fitness_tracker.db')
        cursor = conn.cursor()
        
        # This query groups reps by date to get a daily total
        cursor.execute('''
            SELECT log_date, SUM(reps_count)
            FROM exercise_logs
            WHERE user_id = ?
            GROUP BY log_date
            ORDER BY log_date ASC
            LIMIT 30
        ''', (user_id,))
        
        progress_data = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        return progress_data
    except sqlite3.Error as e:
        print(f"Database error getting user progress: {e}")
        return None
    finally:
        if conn:
            conn.close()

def generate_audio_simple_gtts(text):
    """Simple gTTS generation with detailed logging"""
    try:
        print(f"=== AUDIO DEBUG: Starting audio generation ===")
        print(f"Input text: '{text}'")
        print(f"Text length: {len(text)}")
        print(f"Text type: {type(text)}")
        
        from gtts import gTTS
        print("gTTS imported successfully")
        
        # Create gTTS object
        tts = gTTS(text=text, lang='en', slow=False)
        print("gTTS object created")
        
        # Save to BytesIO buffer
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        print("Audio written to buffer")
        
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()
        print(f"Audio bytes length: {len(audio_bytes)}")
        
        # Convert to base64
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        print(f"Base64 audio length: {len(audio_base64)}")
        print("=== AUDIO DEBUG: Audio generation SUCCESS ===")
        
        return audio_base64
        
    except Exception as e:
        print(f"=== AUDIO DEBUG: Audio generation FAILED ===")
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return ""

@app.route('/test_audio', methods=['GET'])
def test_audio():
    """Test endpoint"""
    try:
        print("\n=== TEST AUDIO ENDPOINT CALLED ===")
        test_message = "This is a test audio message"
        audio_base64 = generate_audio_simple_gtts(test_message)
        
        result = {
            'feedback': test_message,
            'audio': audio_base64,
            'audio_length': len(audio_base64) if audio_base64 else 0,
            'success': len(audio_base64) > 0
        }
        print(f"Test result: {result}")
        return jsonify(result)
    except Exception as e:
        print(f"Error in test_audio: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/process_dance_frame', methods=['POST'])
@token_required # NEW: Add this decorator for security
def process_dance_frame():
    try:
        user_id = request.current_user['user_id']
        print("\n=== DANCE FRAME ENDPOINT CALLED ===")
        data = request.get_json()
        exercise_type = data.get('exercise')
        image_data = data.get('image')
        print(f"Exercise type: {exercise_type}")
        
        # Import dance processing functions
        from dance import process_araimandi, process_mulumandi, process_mandia_davu
        
        # Process the image if provided
        frame = None
        if image_data:
            try:
                # Decode base64 image
                header, encoded = image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                print("Image decoded successfully")
            except Exception as e:
                print(f"Error decoding image: {e}")
                frame = None
        
        # Process based on exercise type
        result_data = None
        if exercise_type == 'araimandi':
            if frame is not None:
                result_data = process_araimandi(frame)
            else:
                result_data = {
                    'feedback': "Unable to process image",
                    'audio_message': "Unable to process image",
                    'should_speak': True
                }
        elif exercise_type == 'mulumandi':
            if frame is not None:
                result_data = process_mulumandi(frame)
            else:
                result_data = {
                    'feedback': "Unable to process image", 
                    'audio_message': "Unable to process image",
                    'should_speak': True
                }
        elif exercise_type == 'mandia_davu':
            if frame is not None:
                result_data = process_mandia_davu(frame)
            else:
                result_data = {
                    'feedback': "Unable to process image",
                    'audio_message': "Unable to process image", 
                    'should_speak': True
                }
        else:
            result_data = {
                'feedback': f"Unknown exercise type: {exercise_type}",
                'audio_message': f"Unknown exercise type: {exercise_type}",
                'should_speak': True
            }
        
        print(f"=== DANCE PROCESSING RESULT ===")
        print(f"Result data: {result_data}")
        
        # Generate audio if needed
        audio_base64 = ""
        if result_data.get('should_speak', False) and result_data.get('audio_message'):
            audio_message = result_data['audio_message'].strip()
            # Only generate audio for non-empty messages
            if audio_message and len(audio_message) > 0:
                print(f"Generating audio for message: '{audio_message}'")
                audio_base64 = generate_audio_simple_gtts(audio_message)
            else:
                print("Empty audio message - skipping audio generation")
        else:
            print("No audio generation needed")
        
        final_result = {
            'feedback': result_data.get('feedback', 'Processing...'),
            'audio': audio_base64,
            'audio_length': len(audio_base64) if audio_base64 else 0,
            'should_speak': result_data.get('should_speak', False)
        }
        
        print(f"=== DANCE ENDPOINT FINAL RESULT ===")
        print(f"Feedback: {final_result['feedback']}")
        print(f"Audio length: {final_result['audio_length']}")
        print(f"Should speak: {final_result['should_speak']}")
        
        return jsonify(final_result)

    except Exception as e:
        print(f"=== DANCE ENDPOINT ERROR ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/process_workout_frame', methods=['POST'])
@token_required
def process_workout_frame():
    """Process workout frames (squats and pushups)"""
    try:
        user_id = request.current_user['user_id']
        print("\n=== WORKOUT FRAME ENDPOINT CALLED ===")
        data = request.get_json()
        exercise_type = data.get('exercise')
        image_data = data.get('image')
        is_challenge = data.get('is_challenge', False)
        print(f"Exercise type: {exercise_type}")
        
        from workout import process_squat, process_pushup
        
        frame = None
        if image_data:
            try:
                header, encoded = image_data.split(',', 1)
                image_bytes = base64.b64decode(encoded)
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                print("Image decoded successfully")
            except Exception as e:
                print(f"Error decoding image: {e}")
                frame = None
        
        result_data = None
        if exercise_type == 'squats':
            if frame is not None:
                feedback_text = process_squat(frame)
                from workout import squat_counter
                should_speak = getattr(squat_counter, 'should_speak', False)
                audio_message = getattr(squat_counter, 'audio_message', '')
                
                if is_challenge and squat_counter.count >= 1: 
                    complete_daily_challenge(user_id, exercise_type)
                    audio_message += " Daily challenge completed! "

                if squat_counter.count > 0:
                    log_exercise_data(user_id, exercise_type, squat_counter.count)
                
                result_data = {
                    'feedback': feedback_text,
                    'audio_message': audio_message,
                    'should_speak': should_speak
                }
            else:
                result_data = {
                    'feedback': "Unable to process image",
                    'audio_message': "Unable to process image",
                    'should_speak': True
                }
        elif exercise_type == 'pushups':
            if frame is not None:
                feedback_text = process_pushup(frame)
                from workout import pushup_counter
                should_speak = getattr(pushup_counter, 'should_speak', False)
                audio_message = getattr(pushup_counter, 'audio_message', '')
                
                if is_challenge and pushup_counter.count >= 1:
                    complete_daily_challenge(user_id, exercise_type)
                    audio_message += " Daily challenge completed! "

                if pushup_counter.count > 0:
                    log_exercise_data(user_id, exercise_type, pushup_counter.count)
                
                result_data = {
                    'feedback': feedback_text,
                    'audio_message': audio_message,
                    'should_speak': should_speak
                }
            else:
                result_data = {
                    'feedback': "Unable to process image",
                    'audio_message': "Unable to process image",
                    'should_speak': True
                }
        else:
            result_data = {
                'feedback': f"Unknown exercise type: {exercise_type}",
                'audio_message': f"Unknown exercise type: {exercise_type}",
                'should_speak': True
            }
        
        print(f"=== WORKOUT PROCESSING RESULT ===")
        print(f"Result data: {result_data}")
        
        audio_base64 = ""
        if result_data.get('should_speak', False) and result_data.get('audio_message'):
            audio_message = result_data['audio_message'].strip()
            if audio_message and len(audio_message) > 0:
                print(f"Generating audio for message: '{audio_message}'")
                audio_base64 = generate_audio_simple_gtts(audio_message)
            else:
                print("Empty audio message - skipping audio generation")
        else:
            print("No audio generation needed")
        
        final_result = {
            'feedback': result_data.get('feedback', 'Processing...'),
            'audio': audio_base64,
            'audio_length': len(audio_base64) if audio_base64 else 0,
            'should_speak': result_data.get('should_speak', False)
        }
        
        print(f"=== WORKOUT ENDPOINT FINAL RESULT ===")
        print(f"Feedback: {final_result['feedback']}")
        print(f"Audio length: {final_result['audio_length']}")
        print(f"Should speak: {final_result['should_speak']}")
        
        return jsonify(final_result)

    except Exception as e:
        print(f"=== WORKOUT ENDPOINT ERROR ===")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# === AUTHENTICATION ENDPOINTS ===

@app.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        confirm_password = data.get('re_password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400
        
        if not validate_email(email):
            return jsonify({'success': False, 'error': 'Please enter a valid email address'}), 400
        
        is_valid_password, password_message = validate_password(password)
        if not is_valid_password:
            return jsonify({'success': False, 'error': password_message}), 400
        
        if password != confirm_password:
            return jsonify({'success': False, 'error': 'Passwords do not match'}), 400
        
        result = create_user(email, password)
        
        if result['success']:
            token = generate_jwt_token(result['user_id'], result['email'])
            create_session(result['user_id'], token)
            
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': {
                    'id': result['user_id'],
                    'email': result['email']
                },
                'token': token
            }), 201
        else:
            return jsonify({'success': False, 'error': result['error']}), 400
            
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'success': False, 'error': 'Registration failed'}), 500

@app.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400
        
        result = authenticate_user(email, password)
        
        if result['success']:
            token = generate_jwt_token(result['user_id'], result['email'])
            create_session(result['user_id'], token)
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': result['user_id'],
                    'email': result['email']
                },
                'token': token
            }), 200
        else:
            return jsonify({'success': False, 'error': result['error']}), 401
            
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'success': False, 'error': 'Login failed'}), 500

@app.route('/logout', methods=['POST'])
@token_required
def logout():
    """User logout endpoint"""
    try:
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token[7:]
            invalidate_session(token)
        
        return jsonify({
            'success': True,
            'message': 'Logout successful'
        }), 200
        
    except Exception as e:
        print(f"Logout error: {e}")
        return jsonify({'success': False, 'error': 'Logout failed'}), 500

@app.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Get user profile information"""
    try:
        user_id = request.current_user['user_id']
        user_data = get_user_by_id(user_id)
        
        if user_data:
            return jsonify({
                'success': True,
                'user': user_data
            }), 200
        else:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
    except Exception as e:
        print(f"Profile error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get profile'}), 500

@app.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify if a token is valid"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        
        if not token:
            return jsonify({'valid': False, 'error': 'No token provided'}), 400
        
        payload = verify_jwt_token(token)
        
        if payload:
            return jsonify({
                'valid': True,
                'user': {
                    'id': payload['user_id'],
                    'email': payload['email']
                }
            }), 200
        else:
            return jsonify({'valid': False, 'error': 'Invalid token'}), 401
            
    except Exception as e:
        print(f"Token verification error: {e}")
        return jsonify({'valid': False, 'error': 'Token verification failed'}), 500

# NEW: Daily Challenge Endpoints
@app.route('/api/daily_challenge', methods=['GET'])
@token_required
def get_challenge():
    """Retrieve the user's daily challenge for today."""
    user_id = request.current_user['user_id']
    challenge_data = get_daily_challenge(user_id)
    
    if challenge_data:
        return jsonify({'success': True, 'challenge': challenge_data}), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to retrieve daily challenge'}), 500

@app.route('/api/complete_challenge', methods=['POST'])
@token_required
def complete_challenge():
    """Mark the daily challenge as completed."""
    user_id = request.current_user['user_id']
    data = request.get_json()
    exercise = data.get('exercise')
    
    if not exercise:
        return jsonify({'success': False, 'error': 'Exercise type is required'}), 400
    
    result = complete_daily_challenge(user_id, exercise)
    return jsonify(result), 200

# NEW: Progress Dashboard Endpoint
@app.route('/api/progress', methods=['GET'])
@token_required
def get_progress():
    """Endpoint to retrieve a user's progress data."""
    user_id = request.current_user['user_id']
    progress_data = get_user_progress(user_id)
    
    if progress_data is not None:
        return jsonify({'success': True, 'progress': progress_data}), 200
    else:
        return jsonify({'success': False, 'error': 'Failed to retrieve progress data'}), 500

# NEW: Endpoint to log dance completion
@app.route('/api/log_dance_completion', methods=['POST'])
@token_required
def log_dance_completion():
    """Logs a dance exercise completion to the database."""
    try:
        user_id = request.current_user['user_id']
        data = request.get_json()
        exercise_type = data.get('exercise')
        
        if not exercise_type:
            return jsonify({'success': False, 'error': 'Exercise type is required'}), 400
        
        log_exercise_data(user_id, exercise_type, 1) # Log one completion
        return jsonify({'success': True, 'message': 'Dance logged successfully'}), 200
    
    except Exception as e:
        print(f"Failed to log dance completion: {e}")
        return jsonify({'success': False, 'error': 'Failed to log dance completion'}), 500

if __name__ == '__main__':
    print("=== STARTING INTEGRATED SERVER ===")
    print("This version integrates audio feedback with dance and workout processing")
    print("Check console for detailed debug information")
    app.run(debug=True, port=5000)
