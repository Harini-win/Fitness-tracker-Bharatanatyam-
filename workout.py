import cv2
import mediapipe as mp
import time
# Import the modified counter classes
from squat_counter import SquatCounter
from pushup_counter import PushupCounter

# --- Global Initializations ---
# These objects are created only once when the server starts.
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

# Global instances to maintain state (rep counts, etc.)
squat_counter = SquatCounter()
pushup_counter = PushupCounter()

def _get_landmarks(frame):
    """Helper function to process a frame and extract landmarks."""
    try:
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        image.flags.writeable = True
        if results.pose_landmarks:
            return results.pose_landmarks.landmark
        else:
            return None
    except Exception as e:
        print(f"Error in _get_landmarks: {e}")
        return None

# --- Main Processing Functions for the API ---

def process_squat(frame):
    """Processes a single frame for the Squat exercise."""
    landmarks = _get_landmarks(frame)
    if landmarks:
        try:
            # Process frame and get updated feedback
            _ = squat_counter.process_frame(landmarks, frame)
            
            # Get feedback and count from the counter
            feedback = getattr(squat_counter, 'feedback', 'Processing...')
            count = getattr(squat_counter, 'counter', 0)
            
            # Return formatted feedback
            return f"Squats: {count} - {feedback}"
            
        except Exception as e:
            print(f"Error in process_squat: {e}")
            return f"Error processing squat: {str(e)}"
        
    return "No body detected - please step back so your full body is visible"

def process_pushup(frame):
    """Processes a single frame for the Push-up exercise."""
    landmarks = _get_landmarks(frame)
    if landmarks:
        try:
            # Process frame and get updated feedback
            _ = pushup_counter.process_frame(landmarks, frame)
            
            # Get feedback and count from the counter
            feedback = getattr(pushup_counter, 'feedback', 'Processing...')
            count = getattr(pushup_counter, 'counter', 0)
            
            # Return formatted feedback
            return f"Push-ups: {count} - {feedback}"
            
        except Exception as e:
            print(f"Error in process_pushup: {e}")
            return f"Error processing pushup: {str(e)}"
        
    return "No body detected - please step back so your full body is visible"