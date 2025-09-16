import cv2
import mediapipe as mp
from araimandi_counter import AraimandiCounter
from mulumandi_counter import MulumandiJumpCounter
from mandia_davu_counter import MandiAdavuCounter

# --- Global Initializations ---
# Initialize Mediapipe Pose once to avoid re-creating it for every request.
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(
    static_image_mode=False,
    model_complexity=1,
    smooth_landmarks=True,
    enable_segmentation=False,
    smooth_segmentation=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Initialize counter instances once. This maintains their state (counts, timers)
# across different frames sent from the frontend.
araimandi_counter = AraimandiCounter(target_time_seconds=10)
mulumandi_counter = MulumandiJumpCounter()
mandi_adavu_counter = MandiAdavuCounter()

def _get_landmarks(frame):
    """Helper function to process a frame with Mediapipe and return landmarks."""
    try:
        # Recolor image to RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        
        # Make detection
        results = pose.process(image)
        
        # Recolor back to BGR  
        image.flags.writeable = True
        
        # Check if landmarks were detected
        if results.pose_landmarks:
            return results.pose_landmarks.landmark
        else:
            return None
            
    except Exception as e:
        print(f"Error in _get_landmarks: {e}")
        return None

# --- Main Processing Functions for the API ---

def process_araimandi(frame):
    """Processes a single frame for the Araimandi exercise."""
    landmarks = _get_landmarks(frame)
    if landmarks:
        # Process the frame with the counter
        _ = araimandi_counter.process_frame(landmarks, frame)
        
        # Return feedback and audio info
        feedback_text = ""
        if araimandi_counter.is_holding:
            feedback_text = f"Holding pose: {araimandi_counter.elapsed_time:.1f}s - {araimandi_counter.feedback}"
        else:
            feedback_text = araimandi_counter.feedback
        
        # Get audio info - with safe attribute access
        audio_message = getattr(araimandi_counter, 'audio_message', '')
        should_speak = getattr(araimandi_counter, 'should_speak', False)
        
        print(f"Araimandi - Counter feedback: {feedback_text}")  # Debug
        print(f"Araimandi - Should speak: {should_speak}, Audio message: '{audio_message}'")  # Debug
        
        # Return both feedback and audio message for the frontend
        return {
            'feedback': feedback_text,
            'audio_message': audio_message if should_speak else '',
            'should_speak': should_speak
        }
    else:
        return {
            'feedback': "Step back and make sure your full body is visible in the camera",
            'audio_message': "Step back and make sure your full body is visible in the camera",
            'should_speak': True
        }

def process_mulumandi(frame):
    """Processes a single frame for the Mulumandi Jump exercise."""
    landmarks = _get_landmarks(frame)
    if landmarks:
        _ = mulumandi_counter.process_frame(landmarks, frame)
        count = getattr(mulumandi_counter, 'count', 0)
        feedback = getattr(mulumandi_counter, 'feedback', 'Keep jumping!')
        feedback_text = f"Jumps: {count} - {feedback}"
        
        print(f"Mulumandi - Feedback: {feedback_text}")  # Debug
        
        # Check if mulumandi counter has audio system like araimandi
        audio_message = getattr(mulumandi_counter, 'audio_message', feedback)
        should_speak = getattr(mulumandi_counter, 'should_speak', count > 0)  # Speak when there's progress
        
        return {
            'feedback': feedback_text,
            'audio_message': audio_message if should_speak else '',
            'should_speak': should_speak
        }
    return {
        'feedback': "Step back and make sure your full body is visible in the camera",
        'audio_message': "Step back and make sure your full body is visible in the camera",
        'should_speak': True
    }
    
def process_mandia_davu(frame):
    """Processes a single frame for the Mandi Adavu exercise."""
    landmarks = _get_landmarks(frame)
    if landmarks:
        _ = mandi_adavu_counter.process_frame(landmarks, frame)
        count = getattr(mandi_adavu_counter, 'count', 0)
        feedback = getattr(mandi_adavu_counter, 'feedback', 'Keep going!')
        feedback_text = f"Reps: {count} - {feedback}"
        
        print(f"Mandi Adavu - Feedback: {feedback_text}")  # Debug
        
        # Check if mandi adavu counter has audio system like araimandi
        audio_message = getattr(mandi_adavu_counter, 'audio_message', feedback)
        should_speak = getattr(mandi_adavu_counter, 'should_speak', count > 0)  # Speak when there's progress
        
        return {
            'feedback': feedback_text,
            'audio_message': audio_message if should_speak else '',
            'should_speak': should_speak
        }
    return {
        'feedback': "Step back and make sure your full body is visible in the camera",
        'audio_message': "Step back and make sure your full body is visible in the camera", 
        'should_speak': True
    }