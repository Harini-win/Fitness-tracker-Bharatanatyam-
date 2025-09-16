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

class SquatCounter:
    def __init__(self):
        self.counter = 0
        self.stage = "up"
        self.feedback = "Stand straight to start"
        self.stage_entry_time = time.time()
        
        # Audio feedback tracking (for frontend)
        self.should_speak = False  # Flag to indicate when audio should be played
        self.audio_message = ""    # The message that should be spoken
        self.last_feedback_spoken = ""
        self.last_feedback_time = 0
        
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
            print(f"Audio set: '{message}' at time {current_time}")
        else:
            self.should_speak = False
            self.audio_message = ""

    def analyze_squat_form(self, landmarks):
        """Comprehensive squat form analysis with specific feedback"""
        try:
            # Use right side landmarks (more commonly visible)
            hip = [landmarks[24].x, landmarks[24].y]
            knee = [landmarks[26].x, landmarks[26].y]
            ankle = [landmarks[28].x, landmarks[28].y]
            shoulder = [landmarks[12].x, landmarks[12].y]
            
            # Calculate key angles and positions
            knee_angle = calculate_angle(hip, knee, ankle)
            is_hip_below_knee = hip[1] > knee[1]
            
            # Check body alignment
            knee_alignment = abs(knee[0] - ankle[0])  # Knees over toes
            back_straight = abs(shoulder[0] - hip[0]) < 0.1  # Back alignment
            
            current_time = time.time()
            stage_time = current_time - self.stage_entry_time
            
            # Reset audio flag at start of each frame
            self.should_speak = False
            self.audio_message = ""
            
            # Detailed form analysis for "up" position
            if self.stage == "up":
                if knee_angle < 160:
                    if knee_angle < 100 and is_hip_below_knee:
                        # Good depth achieved - transition to down
                        self.stage = "down"
                        self.stage_entry_time = current_time
                        self.counter += 1
                        
                        if self.counter % 5 == 0:
                            message = f"Excellent! {self.counter} squats completed!"
                            self.set_audio_feedback(message)
                            return f"{message} Stand up slowly"
                        else:
                            message = f"Perfect depth! {self.counter}"
                            self.set_audio_feedback(message)
                            return f"{message} - Push through heels"
                    
                    elif knee_angle < 130:
                        if not is_hip_below_knee:
                            return "Good depth! Push your hips back further"
                        elif knee_alignment > 0.1:
                            return "Keep knees aligned over your toes"
                        elif not back_straight:
                            return "Keep chest up and back straight while squatting"
                        else:
                            return "Almost there! Go a bit lower for full range"
                    
                    elif knee_angle < 160:
                        if knee_alignment > 0.15:
                            message = "Keep your knees tracking over your toes"
                            if current_time - self.last_audio_time > 4.0:  # Less frequent form feedback
                                self.set_audio_feedback(message)
                            return message
                        elif not back_straight:
                            message = "Chest up! Don't round your back"
                            if current_time - self.last_audio_time > 4.0:
                                self.set_audio_feedback(message)
                            return message
                        else:
                            return "Continue squatting down, hips back"
                
                else:
                    # Standing position
                    if stage_time > 3.0:
                        return "Start your next squat by pushing hips back"
                    elif not back_straight:
                        return "Stand tall with chest up and shoulders back"
                    else:
                        return "Good standing position. Begin your squat"
            
            # Detailed form analysis for "down" position
            elif self.stage == "down":
                if knee_angle > 160:
                    # Successfully stood up
                    self.stage = "up"
                    self.stage_entry_time = current_time
                    return "Great! Ready for your next squat"
                
                elif knee_angle > 130:
                    if not back_straight:
                        return "Keep chest up as you stand"
                    else:
                        return "Good! Continue standing up straight"
                
                elif knee_angle > 100:
                    return "Push through your heels to stand up"
                
                else:
                    # Still in bottom position
                    if stage_time > 2.0:
                        return "Drive up through your heels to standing"
                    elif not back_straight:
                        return "Maintain chest up position, then stand"
                    else:
                        return "Hold this depth briefly, then stand up strong"
            
            return "Continue with good form"
            
        except (IndexError, TypeError):
            return "Adjust your position so I can see all landmarks"

    def process_frame(self, landmarks, frame):
        """Process frame with comprehensive squat coaching"""
        # Check full body visibility
        required_landmarks = [24, 26, 28, 12, 14, 16] 
        is_full_body_visible = all(landmarks[i].visibility > 0.7 for i in required_landmarks)

        if not is_full_body_visible:
            self.feedback = "Move back so I can see your entire body"
            self.set_audio_feedback(self.feedback)
        else:
            # Get detailed form analysis
            self.feedback = self.analyze_squat_form(landmarks)

        # Calculate angles for display
        try:
            hip = [landmarks[24].x, landmarks[24].y]
            knee = [landmarks[26].x, landmarks[26].y]
            ankle = [landmarks[28].x, landmarks[28].y]
            
            knee_angle = calculate_angle(hip, knee, ankle)
            is_hip_below_knee = hip[1] > knee[1]
            
        except (IndexError, TypeError):
            knee_angle = 0
            is_hip_below_knee = False

        # Color-code feedback based on content
        feedback_color = (0, 255, 0)  # Green for good
        if "adjust" in self.feedback.lower() or "move back" in self.feedback.lower():
            feedback_color = (0, 0, 255)  # Red for positioning
        elif ("keep" in self.feedback.lower() or "push" in self.feedback.lower() or 
              "chest up" in self.feedback.lower() or "knees" in self.feedback.lower()):
            feedback_color = (0, 165, 255)  # Orange for form corrections
        elif ("excellent" in self.feedback.lower() or "perfect" in self.feedback.lower() or 
              "great" in self.feedback.lower()):
            feedback_color = (0, 255, 0)  # Green for success

        # Display information on frame
        cv2.putText(frame, self.feedback, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, feedback_color, 2, cv2.LINE_AA)
        cv2.putText(frame, f'Squats: {self.counter}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, f'Stage: {self.stage.upper()}', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        
        # Show form metrics
        depth_status = "Good Depth" if is_hip_below_knee else "Go Deeper"
        depth_color = (0, 255, 0) if is_hip_below_knee else (0, 165, 255)
        cv2.putText(frame, f'Depth: {depth_status}', (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, depth_color, 2, cv2.LINE_AA)
        
        # Show technique reminders
        technique_tip = ""
        if self.stage == "up" and knee_angle < 160:
            technique_tip = "Hips back, chest up, knees over toes"
        elif self.stage == "down":
            technique_tip = "Drive through heels to stand up"
        elif self.stage == "up":
            technique_tip = "Ready to squat: hips back first"
            
        if technique_tip:
            cv2.putText(frame, technique_tip, (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1, cv2.LINE_AA)
        
        # Show angle measurement
        cv2.putText(frame, f'Knee Angle: {int(knee_angle)}°', (10, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        
        # Progress indicator for depth
        if knee_angle < 160:
            depth_progress = max(0, min(100, int((160 - knee_angle) / 60 * 100)))
            cv2.putText(frame, f'Depth: {depth_progress}%', (200, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

        return frame