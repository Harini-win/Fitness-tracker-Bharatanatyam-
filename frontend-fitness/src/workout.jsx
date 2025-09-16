import React, { useState, useRef, useEffect } from 'react';
import { getAuthToken } from './authUtils';

const WORKOUT_OPTIONS = [
    { label: "Squats", value: "squats" },
    { label: "Push-ups", value: "pushups" }
];

const CustomDropdown = ({ options, selected, onSelect }) => {
    const [open, setOpen] = useState(false);
    const selectedLabel = options.find(opt => opt.value === selected)?.label || "Choose an exercise";

    const handleSelect = (option) => {
        onSelect(option.value);
        setOpen(false);
    };

    return (
        <div className="relative inline-block text-left w-56">
            <button
                type="button"
                className="w-full bg-white text-purple-700 font-semibold px-4 py-2 rounded-t-lg shadow focus:outline-none flex justify-between items-center"
                onClick={() => setOpen(!open)}
            >
                {selectedLabel}
                <span className="ml-2">{open ? "▲" : "▼"}</span>
            </button>
            {open && (
                <div className="absolute w-full bg-white rounded-b-lg shadow z-10">
                    {options.map((option) => (
                        <div
                            key={option.value}
                            className={`px-4 py-2 cursor-pointer hover:bg-purple-100 ${selected === option.value ? "text-purple-600 bg-purple-50" : ""}`}
                            onClick={() => handleSelect(option)}
                        >
                            {option.label}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const Work = () => {
    const [selectedExercise, setSelectedExercise] = useState('');
    const [feedback, setFeedback] = useState('Select an exercise and start your workout!');
    const videoRef = useRef(null);
    const canvasRef = useRef(null);

    // Audio state - similar to dance component
    const [isAudioPlaying, setIsAudioPlaying] = useState(false);
    const [lastAudioMessage, setLastAudioMessage] = useState('');
    const [lastAudioTime, setLastAudioTime] = useState(0);
    const currentAudio = useRef(null);

    const startCamera = async () => {
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                if (videoRef.current) videoRef.current.srcObject = stream;
            } catch (error) {
                console.error("Error accessing webcam:", error);
                setFeedback("Could not access webcam. Please enable permissions.");
            }
        }
    };

    useEffect(() => {
        startCamera();
    }, []);

    // Function to play audio immediately
    const playAudio = (audioBase64) => {
        // Stop any currently playing audio
        if (currentAudio.current) {
            currentAudio.current.pause();
            currentAudio.current = null;
        }
        
        setIsAudioPlaying(true);
        
        const audioSrc = `data:audio/mp3;base64,${audioBase64}`;
        const audio = new Audio(audioSrc);
        currentAudio.current = audio;
        
        // Set volume
        audio.volume = 0.8;
        
        // Add error handling for audio
        audio.onerror = (e) => {
            console.error('Audio playback error:', e);
            setIsAudioPlaying(false);
            currentAudio.current = null;
        };
        
        audio.onended = () => {
            console.log('Audio finished playing');
            setIsAudioPlaying(false);
            currentAudio.current = null;
        };
        
        // Play immediately
        audio.play().catch(error => {
            console.error('Error playing audio:', error);
            setIsAudioPlaying(false);
            currentAudio.current = null;
        });
    };

    const sendFrameToServer = () => {
        if (!videoRef.current || !canvasRef.current || !selectedExercise) return;

        const video = videoRef.current;
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL('image/jpeg');

        console.log(`Sending ${selectedExercise} frame to server...`);

        const authToken = getAuthToken(); // Get the auth token

        if (!authToken) {
            setFeedback("Authentication token missing. Please log in.");
            console.error("Authentication token missing.");
            return;
        }

        // Using fetch for better error handling, connecting to the NEW workout endpoint
        fetch('http://127.0.0.1:5000/process_workout_frame', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}` // ADDED: Authorization header
            },
            body: JSON.stringify({
                exercise: selectedExercise,
                image: imageData,
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Server response:', data);
            
            const { feedback: feedbackText, audio: audioBase64, should_speak } = data;
            setFeedback(feedbackText);
            
            // Immediate audio playback with strict rate limiting
            if (audioBase64 && audioBase64.length > 0 && should_speak && !isAudioPlaying) {
                const currentTime = Date.now();
                const audioHash = audioBase64.substring(0, 50); // Use first 50 chars as hash
                
                // Rate limit: minimum 2 seconds between audio, and must be different content
                if (audioHash !== lastAudioMessage && (currentTime - lastAudioTime) > 2000) {
                    console.log('Playing immediate audio, length:', audioBase64.length);
                    playAudio(audioBase64);
                    setLastAudioMessage(audioHash);
                    setLastAudioTime(currentTime);
                } else {
                    console.log('Skipping audio - rate limited or duplicate');
                }
            } else {
                console.log('No audio or already playing');
            }
        })
        .catch(error => {
            console.error("Error sending frame to server:", error);
            setFeedback(`Error: ${error.message}`);
        });
    };

    useEffect(() => {
        if (!selectedExercise) return;
        
        // Clear previous audio when switching exercises
        setLastAudioMessage('');
        setLastAudioTime(0);
        setIsAudioPlaying(false);
        
        // Stop any playing audio
        if (currentAudio.current) {
            currentAudio.current.pause();
            currentAudio.current = null;
        }
        
        const interval = setInterval(sendFrameToServer, 1500); // 1.5 seconds
        return () => clearInterval(interval);
    }, [selectedExercise]);

    // Cleanup audio on unmount
    useEffect(() => {
        return () => {
            if (currentAudio.current) {
                currentAudio.current.pause();
                currentAudio.current = null;
            }
        };
    }, []);

    return (
        <div className="min-h-screen flex items-center justify-center relative bg-[url('/img.jpg')] flex-col p-4">
            <div className="justify-center mb-8 relative z-20">
                <CustomDropdown
                    options={WORKOUT_OPTIONS}
                    selected={selectedExercise}
                    onSelect={setSelectedExercise}
                />
            </div>
            <div className="relative z-10 bg-transparent rounded-2xl shadow-lg p-6 w-full max-w-6xl h-[600px] border-2 border-white/20 backdrop-blur-[20px] shadow-black/20 text-white flex gap-6">
                <div className="w-2/3 h-full bg-black/20 rounded-lg overflow-hidden">
                    <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" style={{ transform: 'scaleX(-1)' }} />
                    <canvas ref={canvasRef} style={{ display: 'none' }} />
                </div>
                <div className="w-1/3 h-full bg-black/20 rounded-lg flex flex-col justify-center items-center p-4">
                    <h2 className="text-2xl font-bold mb-4 text-purple-300">Live Feedback</h2>
                    <p className="text-xl text-center">{feedback}</p>
                    
                    {/* Debug info - hidden in production */}
                    {process.env.NODE_ENV === 'development' && (
                        <div className="mt-4 text-xs text-gray-400">
                            <p>Exercise: {selectedExercise || 'None'}</p>
                            <p>Audio playing: {isAudioPlaying ? 'Yes' : 'No'}</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default Work;
