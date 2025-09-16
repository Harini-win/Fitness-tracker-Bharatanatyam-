import cv2
import numpy as np
import time

def calculate_angle(a, b, c):
    """Calculates the angle between three points (A, B, C) with B as the vertex."""
    a = np.array(a)  # First point
    b = np.array(b)  # Middle point (vertex)
    c = np.array(c)  # End point

    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    angle = np.abs(radians * 180.0 / np.pi)

    if angle > 180.0:
        angle = 360 - angle

    return angle

class PushupCounter:
    def __init__(self):
        self.counter = 0
        self.stage = "up"  # "up" or "down"
        self.feedback = "Get in position"
        self.is_side_view = False
        self.is_full_body_visible = False
        self.count_announced = False
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

    def check_form_and_give_feedback(self, landmarks):
        """Analyze push-up form and provide specific feedback"""
        try:
            # Use right side landmarks
            shoulder = [landmarks[12].x, landmarks[12].y]
            elbow = [landmarks[14].x, landmarks[14].y]
            wrist = [landmarks[16].x, landmarks[16].y]
            hip = [landmarks[24].x, landmarks[24].y]
            knee = [landmarks[26].x, landmarks[26].y]
            ankle = [landmarks[28].x, landmarks[28].y]

            # Calculate angles
            elbow_angle = calculate_angle(shoulder, elbow, wrist)
            body_angle = calculate_angle(shoulder, hip, ankle)
            hip_angle = calculate_angle(shoulder, hip, knee)
            
            current_time = time.time()
            
            # Check body alignment
            body_straight = body_angle > 165
            hip_alignment = hip_angle > 160  # Hips shouldn't sag
            
            # Hand position check (wrists should be roughly under shoulders)
            hand_position_good = abs(wrist[0] - shoulder[0]) < 0.15
            
            # Reset audio flag at start of each frame
            self.should_speak = False
            self.audio_message = ""
            
            if not self.is_full_body_visible:
                return "Move back so I can see your entire body"
            
            # Body position analysis
            if not body_straight:
                if body_angle < 140:
                    message = "Your body is too bent. Straighten your back and legs"
                    if current_time - self.last_audio_time > 4.0:  # Less frequent form feedback
                        self.set_audio_feedback(message)
                    return message
                else:
                    return "Keep your body in a straight line from head to heels"
            
            if not hip_alignment:
                if hip_angle < 140:
                    message = "Don't let your hips sag. Engage your core"
                    if current_time - self.last_audio_time > 4.0:
                        self.set_audio_feedback(message)
                    return message
                else:
                    return "Keep your hips level with your body"
            
            if not hand_position_good:
                if wrist[0] < shoulder[0] - 0.15:
                    return "Move your hands forward, under your shoulders"
                else:
                    return "Move your hands back, under your shoulders"
            
            # Form is good, now check push-up execution
            self.is_side_view = True
            
            # Stage-specific feedback
            if self.stage == "up":
                if elbow_angle < 100:
                    # Transition to down
                    self.stage = "down"
                    self.stage_entry_time = current_time
                    self.count_announced = False
                    return "Good descent! Now push back up"
                elif elbow_angle < 140:
                    return "Continue lowering down, chest towards the floor"
                else:
                    stage_time = current_time - self.stage_entry_time
                    if stage_time > 2.0:
                        return "Lower your body down for a push-up"
                    else:
                        return "Ready to start push-up. Lower down slowly"
            
            elif self.stage == "down":
                if elbow_angle > 160:
                    # Transition to up - count the rep
                    self.stage = "up"
                    self.stage_entry_time = current_time
                    self.counter += 1
                    
                    # Announce the count
                    if not self.count_announced:
                        self.count_announced = True
                        if self.counter % 5 == 0:
                            message = f"Excellent! {self.counter} push-ups completed"
                            self.set_audio_feedback(message)
                            return message
                        else:
                            message = f"Great! {self.counter}"
                            self.set_audio_feedback(message)
                            return message
                elif elbow_angle < 80:
                    return "Perfect depth! Now push up strongly"
                elif elbow_angle < 120:
                    return "Good! Push up with controlled strength"
                else:
                    stage_time = current_time - self.stage_entry_time
                    if stage_time > 3.0:
                        return "Push up from the bottom position"
                    else:
                        return "Hold briefly, then push up explosively"
            
            return "Maintain good form and continue"
            
        except (IndexError, TypeError):
            return "Adjust your position so I can see all landmarks clearly"

    def process_frame(self, landmarks, frame):
        """Process frame with comprehensive feedback"""
        # Check for full body visibility
        required_landmarks = [12, 14, 16, 24, 26, 28]  # Right shoulder, elbow, wrist, hip, knee, ankle
        self.is_full_body_visible = all(landmarks[i].visibility > 0.7 for i in required_landmarks)

        if not self.is_full_body_visible:
            self.feedback = "Ensure your entire body is visible"
            self.set_audio_feedback("Move back so I can see your full body")
        else:
            # Get detailed form feedback
            self.feedback = self.check_form_and_give_feedback(landmarks)

        # Calculate angles for display
        try:
            shoulder = [landmarks[12].x, landmarks[12].y]
            elbow = [landmarks[14].x, landmarks[14].y]
            wrist = [landmarks[16].x, landmarks[16].y]
            hip = [landmarks[24].x, landmarks[24].y]
            ankle = [landmarks[28].x, landmarks[28].y]
            
            elbow_angle = calculate_angle(shoulder, elbow, wrist)
            body_angle = calculate_angle(shoulder, hip, ankle)
            
        except (IndexError, TypeError):
            elbow_angle = 0
            body_angle = 0

        # Color-code feedback based on content
        feedback_color = (0, 255, 0)  # Green for good
        if "error" in self.feedback.lower() or "adjust" in self.feedback.lower():
            feedback_color = (0, 0, 255)  # Red for errors
        elif ("move" in self.feedback.lower() or "straighten" in self.feedback.lower() or 
              "don't" in self.feedback.lower() or "engage" in self.feedback.lower()):
            feedback_color = (0, 165, 255)  # Orange for corrections
        elif ("excellent" in self.feedback.lower() or "perfect" in self.feedback.lower() or 
              "great" in self.feedback.lower()):
            feedback_color = (0, 255, 0)  # Green for success

        # Display information on frame
        cv2.putText(frame, self.feedback, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, feedback_color, 2, cv2.LINE_AA)
        cv2.putText(frame, f'Push-ups: {self.counter}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, f'Stage: {self.stage.upper()}', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        
        # Show form analysis
        form_status = "Good Form" if self.is_side_view else "Check Form"
        form_color = (0, 255, 0) if self.is_side_view else (0, 0, 255)
        cv2.putText(frame, f'Form: {form_status}', (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.8, form_color, 2, cv2.LINE_AA)
        
        # Show technique tips
        technique_tip = ""
        if self.stage == "up" and self.is_side_view:
            technique_tip = "Lower down slowly and controlled"
        elif self.stage == "down" and self.is_side_view:
            technique_tip = "Push up explosively to full extension"
        elif not self.is_side_view:
            technique_tip = "Position yourself for side view"
            
        if technique_tip:
            cv2.putText(frame, technique_tip, (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1, cv2.LINE_AA)
        
        # Show angle measurements
        cv2.putText(frame, f'Elbow: {int(elbow_angle)}°', (10, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, f'Body: {int(body_angle)}°', (150, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

        return frame