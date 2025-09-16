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

class MulumandiJumpCounter:
    def __init__(self):
        self.counter = 0
        self.count = 0  # Alias for counter to match expected interface
        self.state = "start"  # States: "start", "araimandi", "compression", "airborne", "landed"
        self.previous_ankle_y = None
        self.feedback = "Get ready to jump"
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
            print(f"Mulumandi Audio set: '{message}' at time {current_time}")  # Debug
        else:
            self.should_speak = False
            self.audio_message = ""
            print(f"Mulumandi Audio skipped - duplicate or too soon")  # Debug

    def check_form_and_give_feedback(self, landmarks):
        """Check form and provide specific correction feedback"""
        try:
            hip = [landmarks[24].x, landmarks[24].y]
            knee = [landmarks[26].x, landmarks[26].y]
            ankle = [landmarks[28].x, landmarks[28].y]
            shoulder = [landmarks[12].x, landmarks[12].y]
            
            knee_angle = calculate_angle(hip, knee, ankle)
            current_ankle_y = landmarks[28].y
            
            # Check if back is straight (shoulder should be roughly above hip)
            back_alignment = abs(shoulder[0] - hip[0])
            is_back_straight = back_alignment < 0.1
            
            # State-specific feedback
            if self.state == "start":
                if knee_angle > 160:  # Standing straight
                    if not is_back_straight:
                        return "Straighten your back and prepare for araimandi"
                    else:
                        return "Good posture! Now bend into araimandi position"
                elif knee_angle > 105:
                    return "Bend down more to reach araimandi position"
                elif 80 < knee_angle < 105:
                    self.state = "araimandi"
                    self.state_entry_time = time.time()
                    return "Perfect araimandi! Hold this position"
                else:
                    return "Too deep! Rise up slightly to araimandi"
            
            elif self.state == "araimandi":
                current_time = time.time()
                hold_time = current_time - self.state_entry_time
                
                if knee_angle < 75:
                    self.state = "compression"
                    self.state_entry_time = current_time
                    return "Good compression! Now jump up explosively"
                elif knee_angle > 110:
                    if not is_back_straight:
                        return "Keep back straight and return to araimandi"
                    else:
                        return "Lower down to araimandi position"
                elif not is_back_straight:
                    return "Straighten your back while holding araimandi"
                elif hold_time > 1.0:  # Held for more than 1 second
                    return "Great hold! Now compress down and prepare to jump"
                else:
                    return "Hold the araimandi position steady"
            
            elif self.state == "compression":
                if knee_angle > 90:
                    return "Compress lower before jumping"
                elif self.previous_ankle_y is not None and current_ankle_y < self.previous_ankle_y - 0.02:
                    self.state = "airborne"
                    return "Excellent jump! Control your landing"
                elif knee_angle > 160:
                    self.state = "start"
                    return "Jump attempt failed. Reset to araimandi"
                else:
                    return "Push off explosively from this position"
            
            elif self.state == "airborne":
                if 80 < knee_angle < 105:
                    self.state = "landed"
                    self.counter += 1
                    self.count = self.counter  # Update count alias
                    return f"Perfect controlled landing! Jump {self.counter} completed"
                elif knee_angle > 150:
                    return "Prepare to land in araimandi position"
                else:
                    return "Control your descent into araimandi"
            
            elif self.state == "landed":
                if knee_angle > 160:
                    self.state = "start"
                    return "Excellent! Stand up and prepare for next jump"
                elif not is_back_straight:
                    return "Straighten your back before standing up"
                else:
                    return "Great landing! Now stand up to reset"
            
            # Store ankle position for next frame
            self.previous_ankle_y = current_ankle_y
            
            return "Continue with the movement"
            
        except (IndexError, TypeError):
            return "Adjust your position so I can see all landmarks"

    def process_frame(self, landmarks, frame):
        """Process frame with audio feedback for web integration"""
        
        # Reset audio flag at start of each frame
        self.should_speak = False
        self.audio_message = ""
        
        # Check for full body visibility first
        required_landmarks = [24, 26, 28, 12, 14, 16]  # Right hip, knee, ankle, shoulder, elbow, wrist
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
        cv2.putText(frame, f'Jumps: {self.counter}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, f'State: {self.state}', (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
        
        # Color-code feedback based on state
        feedback_color = (0, 255, 0)  # Green for good
        if "failed" in self.feedback.lower() or "error" in self.feedback.lower():
            feedback_color = (0, 0, 255)  # Red for errors
        elif "adjust" in self.feedback.lower() or "more" in self.feedback.lower():
            feedback_color = (0, 165, 255)  # Orange for corrections
        
        cv2.putText(frame, self.feedback, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, feedback_color, 2, cv2.LINE_AA)
        
        # Show progress indicator
        progress_text = ""
        if self.state == "start":
            progress_text = "Step 1: Get into araimandi"
        elif self.state == "araimandi":
            progress_text = "Step 2: Hold position, then compress"
        elif self.state == "compression":
            progress_text = "Step 3: Jump explosively"
        elif self.state == "airborne":
            progress_text = "Step 4: Control landing"
        elif self.state == "landed":
            progress_text = "Step 5: Stand up to reset"
            
        cv2.putText(frame, progress_text, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2, cv2.LINE_AA)

        return frame