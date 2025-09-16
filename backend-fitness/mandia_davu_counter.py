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

class MandiAdavuCounter:
    def __init__(self):
        self.counter = 0
        self.state = "start"  # States: "start", "araimandi_ready", "dip", "jump", "mandi_contact", "araimandi_landed"
        self.previous_ankle_y = None
        self.feedback = "Get in position"
        self.is_full_body_visible = False
        
        # Audio feedback tracking (for frontend)
        self.last_feedback_spoken = ""
        self.last_feedback_time = 0
        self.should_speak = False  # Flag to indicate when audio should be played
        self.audio_message = ""    # The message that should be spoken
        self.state_entry_time = time.time()
        
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
            print(f"Mandi Adavu Audio set: '{message}' at time {current_time}")  # Debug
        else:
            self.should_speak = False
            self.audio_message = ""
            print(f"Mandi Adavu Audio skipped - duplicate or too soon")  # Debug

    def check_form_and_give_feedback(self, landmarks):
        """Check form and provide specific correction feedback"""
        try:
            hip = [landmarks[24].x, landmarks[24].y]
            knee = [landmarks[26].x, landmarks[26].y]
            ankle = [landmarks[28].x, landmarks[28].y]
            shoulder = [landmarks[12].x, landmarks[12].y]
            
            current_ankle_y = landmarks[28].y
            current_knee_y = landmarks[26].y
            knee_angle = calculate_angle(hip, knee, ankle)
            
            # Check if back is straight
            back_alignment = abs(shoulder[0] - hip[0])
            is_back_straight = back_alignment < 0.1
            
            # State-specific feedback
            if self.state == "start":
                if knee_angle > 160:  # Standing straight
                    if not is_back_straight:
                        return "Straighten your back and get into araimandi position"
                    else:
                        return "Good posture! Now lower into araimandi position"
                elif knee_angle > 105:
                    return "Bend down more to reach araimandi"
                elif 80 < knee_angle < 100:
                    self.state = "araimandi_ready"
                    self.state_entry_time = time.time()
                    return "Perfect araimandi! Ready to perform mandi adavu"
                else:
                    return "Too deep! Rise up slightly to araimandi"
            
            elif self.state == "araimandi_ready":
                current_time = time.time()
                hold_time = current_time - self.state_entry_time
                
                if knee_angle < 80:
                    self.state = "dip"
                    self.state_entry_time = current_time
                    return "Good dip! Now jump up and drop to mandi"
                elif knee_angle > 105:
                    if not is_back_straight:
                        return "Keep back straight and return to araimandi"
                    else:
                        return "Lower back to araimandi position"
                elif not is_back_straight:
                    return "Straighten your back while in araimandi"
                elif hold_time > 1.5:
                    return "Great hold! Now dip down and prepare for the jump"
                else:
                    return "Hold araimandi steady, then dip and jump"
            
            elif self.state == "dip":
                if self.previous_ankle_y is not None and current_ankle_y < self.previous_ankle_y - 0.02:
                    self.state = "jump"
                    return "Excellent jump! Now drop to mandi position"
                elif knee_angle > 90:
                    return "Dip lower before jumping"
                else:
                    return "From this dip, jump up explosively"
            
            elif self.state == "jump":
                knee_ankle_distance = abs(current_knee_y - current_ankle_y)
                if knee_ankle_distance < 0.05:
                    self.state = "mandi_contact"
                    return "Perfect mandi contact! Now rise back to araimandi"
                elif knee_ankle_distance > 0.15:
                    return "Drop your knees closer to the ground for mandi"
                else:
                    return "Good descent! Get your knees to touch the ground"
            
            elif self.state == "mandi_contact":
                if 80 < knee_angle < 100:
                    self.state = "araimandi_landed"
                    self.counter += 1
                    return f"Excellent mandi adavu! Rep {self.counter} completed"
                elif knee_angle < 70:
                    return "Rise up from mandi to araimandi position"
                elif knee_angle > 120:
                    return "Don't stand up fully, return to araimandi"
                else:
                    return "Push up to araimandi position from mandi"
            
            elif self.state == "araimandi_landed":
                if knee_angle < 80:
                    self.state = "dip"
                    return "Starting next rep! Good dip"
                elif knee_angle > 105:
                    self.state = "start"
                    return "Standing reset. Ready for next mandi adavu"
                elif not is_back_straight:
                    return "Straighten your back while in araimandi"
                else:
                    return "Great landing! Continue or stand to reset"
            
            # Store ankle position for next frame
            self.previous_ankle_y = current_ankle_y
            
            return "Continue the movement sequence"
            
        except (IndexError, TypeError):
            return "Adjust position so I can see all your landmarks"

    def process_frame(self, landmarks, frame):
        """Process frame with audio feedback for web integration"""
        
        # Reset audio flag at start of each frame
        self.should_speak = False
        self.audio_message = ""
        
        # Ensure full body is visible for accurate tracking
        required_landmarks = [24, 26, 28, 12, 14, 16]
        self.is_full_body_visible = all(landmarks[i].visibility > 0.7 for i in required_landmarks)

        if not self.is_full_body_visible:
            self.feedback = "Ensure your entire body is visible"
            current_time = time.time()
            # Only give body visibility feedback occasionally
            if current_time - self.last_audio_time > 4.0:
                self.set_audio_feedback("Move back so I can see your full body")
        else:
            # Get detailed feedback based on current form
            form_feedback = self.check_form_and_give_feedback(landmarks)
            self.feedback = form_feedback
            
            # Set audio feedback for important state changes and counts
            if "completed" in form_feedback.lower() or "excellent" in form_feedback.lower():
                self.set_audio_feedback(form_feedback)
            elif "perfect" in form_feedback.lower() or "good" in form_feedback.lower():
                self.set_audio_feedback(form_feedback)
            elif current_time - self.last_audio_time > 3.0:  # Form corrections every 3 seconds
                self.set_audio_feedback(form_feedback)

        # Display information on the frame
        cv2.putText(frame, f'Reps: {self.counter}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, f'State: {self.state}', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        
        # Color-code feedback based on state and content
        feedback_color = (0, 255, 0)  # Green for good
        if "error" in self.feedback.lower() or "adjust" in self.feedback.lower():
            feedback_color = (0, 0, 255)  # Red for errors
        elif "more" in self.feedback.lower() or "lower" in self.feedback.lower() or "straighten" in self.feedback.lower():
            feedback_color = (0, 165, 255)  # Orange for corrections
        elif "excellent" in self.feedback.lower() or "perfect" in self.feedback.lower():
            feedback_color = (0, 255, 0)  # Green for success
        
        cv2.putText(frame, self.feedback, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, feedback_color, 2, cv2.LINE_AA)
        
        # Show step-by-step progress
        progress_text = ""
        if self.state == "start":
            progress_text = "Step 1: Get into araimandi position"
        elif self.state == "araimandi_ready":
            progress_text = "Step 2: Hold araimandi, prepare to dip"
        elif self.state == "dip":
            progress_text = "Step 3: Dip down, then jump up"
        elif self.state == "jump":
            progress_text = "Step 4: Drop to mandi (knees to ground)"
        elif self.state == "mandi_contact":
            progress_text = "Step 5: Rise from mandi to araimandi"
        elif self.state == "araimandi_landed":
            progress_text = "Step 6: Complete! Continue or reset"
            
        cv2.putText(frame, progress_text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)
        
        # Show technique tips
        technique_tip = ""
        if self.state in ["araimandi_ready", "dip"]:
            technique_tip = "Keep back straight throughout movement"
        elif self.state == "jump":
            technique_tip = "Control descent - knees should touch ground"
        elif self.state == "mandi_contact":
            technique_tip = "Push up smoothly to araimandi"
            
        if technique_tip:
            cv2.putText(frame, technique_tip, (10, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1, cv2.LINE_AA)

        return frame