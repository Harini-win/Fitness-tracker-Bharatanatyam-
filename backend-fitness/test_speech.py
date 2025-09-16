# tts_pyttsx3.py
import pyttsx3

engine = pyttsx3.init()            # initialize engine (sapi5 on Windows, nsss on mac, espeak on linux)
voices = engine.getProperty("voices")
rate = engine.getProperty("rate")

print("Available voices:", len(voices))
# optional: pick a different voice (0 or 1 usually)
if voices:
	engine.setProperty("voice", voices[0].id)   # change index if you want a different voice
else:
	print("No voices available.")
engine.setProperty("rate", rate - 40)       # slower speaking rate

text1 = "Hello! This is a short text to speech test using pyttsx3."
text2 = "Hello Harini!"
engine.say(text1)
engine.runAndWait()

engine.say(text2)
engine.runAndWait()