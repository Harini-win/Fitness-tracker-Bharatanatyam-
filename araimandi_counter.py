import cv2
import numpy as np
import time

def calculate_angle(a, b, c):
    """Calculates the angle between three points (A, B, C) with B as the vertex."""
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

class AraimandiCounter:
    def __init__(self, target_time_seconds=60):
        self.start_time = None
        self.elapsed_time = 0
        self.is_holding = False
        self.target_time = target_time_seconds
        print(f"Target time set to {self.target_time} seconds")
        self.feedback = "Get into Araimandi pose"
        self.is_full_body_visible = False
        self.time_in_pose = 0
        
        # Audio feedback tracking (for frontend)
        self.spoken_count_s = 0
        self.last_spoken_time_s = None
        self.last_feedback_spoken = ""
        self.last_feedback_time = 0
        self.should_speak = False  # Flag to indicate when audio should be played
        self.audio_message = ""    # The message that should be spoken
        
        # Audio rate limiting
        self.last_audio_time = 0
        self.min_audio_interval = 2.0  # Minimum 2 seconds between audio messages

    def set_audio_feedback(self, message):
        """Set audio feedback to be played by frontend"""
        current_time = time.time()
        
        # Rate limiting: minimum interval between audio messages
        if current_time - self.last_audio_time < self.min_audio_interval:
            self.should_speak = False
            self.audio_message = ""
            return
            
        # Prevent duplicate audio within reasonable time
        if message != self.last_feedback_spoken or current_time - self.last_feedback_time > 3.0:
            self.should_speak = True
            self.audio_message = message
            self.last_feedback_spoken = message
            self.last_feedback_time = current_time
            self.last_audio_time = current_time
            print(f"Audio set: '{message}' at time {current_time}")  # Debug
        else:
            self.should_speak = False
            self.audio_message = ""
            print(f"Audio skipped - duplicate or too soon")  # Debug

    def check_form(self, landmarks):
        """Checks if the user's form is valid for the Araimandi Hold."""
        try:
            # Use left side landmarks (more commonly visible)
            # Mediapipe landmarks: 23=left_hip, 25=left_knee, 27=left_ankle, 11=left_shoulder
            left_hip = [landmarks[23].x, landmarks[23].y]
            left_knee = [landmarks[25].x, landmarks[25].y] 
            left_ankle = [landmarks[27].x, landmarks[27].y]
            left_shoulder = [landmarks[11].x, landmarks[11].y]
            
            # Also get right side for better analysis
            right_hip = [landmarks[24].x, landmarks[24].y]
            right_knee = [landmarks[26].x, landmarks[26].y]
            right_ankle = [landmarks[28].x, landmarks[28].y]
            
            # Check visibility - Mediapipe provides visibility score (0-1)
            required_landmarks = [23, 25, 27, 24, 26, 28, 11]  # Both sides + shoulder
            visibility_scores = [landmarks[i].visibility for i in required_landmarks]
            
            # Lower threshold for visibility check
            self.is_full_body_visible = all(score > 0.5 for score in visibility_scores)
            
            if not self.is_full_body_visible:
                return False, "Move closer to camera - lower body not fully visible"
            
            # Calculate knee angles for both legs
            left_knee_angle = calculate_angle(left_hip, left_knee, left_ankle)
            right_knee_angle = calculate_angle(right_hip, right_knee, right_ankle)
            
            # Use the better visible leg's angle
            knee_angle = left_knee_angle if landmarks[25].visibility > landmarks[26].visibility else right_knee_angle
            
            # Check if person is in squat position (more lenient range)
            # For Araimandi, knees should be bent (around 90 degrees, but allow 70-120 range)
            knee_angle_good = 70 < knee_angle < 120
            
            # Check if torso is relatively upright (less strict than original)
            # Use hip to shoulder alignment
            hip_x = (left_hip[0] + right_hip[0]) / 2  # Average hip position
            shoulder_x = left_shoulder[0]
            
            # Allow more flexibility in torso position
            is_torso_ok = abs(hip_x - shoulder_x) < 0.15  # Increased from 0.1
            
            if knee_angle_good and is_torso_ok:
                return True, "Perfect Araimandi form!"
            else:
                if not knee_angle_good:
                    if knee_angle < 70:
                        return False, "Bend knees more - go deeper"
                    else:
                        return False, "Bend knees less - come up slightly"  
                else:
                    return False, "Keep torso upright"

        except (IndexError, TypeError, AttributeError) as e:
            return False, "Adjust your position in frame"

    def process_frame(self, landmarks, frame):
        """Processes the frame, updates the timer, and displays feedback."""
        
        # Reset audio flag at start of each frame
        self.should_speak = False
        self.audio_message = ""
        
        is_form_valid, form_feedback = self.check_form(landmarks)

        if is_form_valid:
            if not self.is_holding:
                self.is_holding = True
                self.start_time = time.time() - self.elapsed_time
                self.set_audio_feedback("Timer started")
            
            current_time = time.time()
            self.elapsed_time = current_time - self.start_time
            self.time_in_pose = self.elapsed_time
            
            # Round elapsed time to the nearest second
            rounded_time = int(round(self.elapsed_time))
            
            # Voice feedback for the timer count - every 3 seconds
            if rounded_time > self.spoken_count_s and rounded_time <= self.target_time and rounded_time > 0:
                # Announce every 3 seconds: 3, 6, 9, 12, 15, etc.
                if rounded_time % 3 == 0:
                    self.set_audio_feedback(f"{rounded_time} seconds")
                    self.spoken_count_s = rounded_time
                else:
                    self.spoken_count_s = rounded_time  # Update count but don't speak

            if self.elapsed_time >= self.target_time:
                self.feedback = "Congratulations! Hold complete."
                if not hasattr(self, 'completion_announced') or not self.completion_announced:
                    self.set_audio_feedback("Congratulations! You are done!")
                    self.completion_announced = True
            else:
                self.feedback = form_feedback

        else:
            if self.is_holding:
                self.is_holding = False
                self.elapsed_time = time.time() - self.start_time if self.start_time else 0
                self.time_in_pose = self.elapsed_time
                self.set_audio_feedback("Timer stopped")
            
            self.start_time = None
            self.feedback = form_feedback
            
            # Only give form feedback occasionally to avoid spam
            current_time = time.time()
            if current_time - self.last_audio_time > 4.0:  # Only every 4 seconds for form feedback
                self.set_audio_feedback(self.feedback)

        # Display information on the frame
        timer_display = f"Time: {int(self.elapsed_time)}s / {self.target_time}s"
        cv2.putText(frame, timer_display, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        
        feedback_color = (0, 255, 0) if self.is_holding else (0, 0, 255)
        cv2.putText(frame, self.feedback, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, feedback_color, 2, cv2.LINE_AA)
        
        return frame