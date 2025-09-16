import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

const DS = () => {
    const navigate = useNavigate();
    const [challengeStatus, setChallengeStatus] = useState("pending"); // "pending", "completed", "expired"
    const [challengeExercise, setChallengeExercise] = useState(null);
    const [loading, setLoading] = useState(true);

    const availableExercises = [
        { type: "squats", name: "Squats" },
        { type: "pushups", name: "Pushups" },
        { type: "araimandi", name: "Araimandi" },
        { type: "mulumandi", name: "Mulumandi" },
        { type: "mandia_davu", name: "Mandi adavu" }
    ];

    useEffect(() => {
        // In a real application, you would fetch the challenge status from your backend
        // For this example, we'll simulate it with localStorage.
        const today = new Date().toISOString().slice(0, 10);
        const lastChallenge = JSON.parse(localStorage.getItem('dailyChallenge'));

        if (lastChallenge && lastChallenge.date === today) {
            setChallengeStatus(lastChallenge.status);
            setChallengeExercise(lastChallenge.exercise);
        } else {
            // Assign a new random challenge for the day
            const randomExercise = availableExercises[Math.floor(Math.random() * availableExercises.length)];
            const newChallenge = {
                date: today,
                status: "pending",
                exercise: randomExercise
            };
            localStorage.setItem('dailyChallenge', JSON.stringify(newChallenge));
            setChallengeExercise(newChallenge.exercise);
            setChallengeStatus("pending");
        }
        setLoading(false);
    }, []);

    const handleStartChallenge = () => {
        if (challengeExercise) {
            // Navigate to the correct page based on exercise type
            if (challengeExercise.type === 'squats' || challengeExercise.type === 'pushups') {
                navigate(`/workout?exercise=${challengeExercise.type}`);
            } else {
                navigate(`/dance?exercise=${challengeExercise.type}`);
            }
        }
    };

    // This function would be called by the exercise components upon success
    const handleChallengeCompletion = () => {
        const today = new Date().toISOString().slice(0, 10);
        const updatedChallenge = {
            date: today,
            status: "completed",
            exercise: challengeExercise
        };
        localStorage.setItem('dailyChallenge', JSON.stringify(updatedChallenge));
        setChallengeStatus("completed");
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center relative bg-[url('/img.jpg')] flex flex-col">
                <div className="relative z-10 text-white text-4xl font-bold">Loading...</div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center relative bg-[url('/img.jpg')] flex flex-col">
            <div className="justify-center mb-8 relative z-20 text-white text-4xl font-bold">
                <h2>Daily Challenge</h2>
            </div>
            <div className="relative z-10 bg-transparent rounded-2xl shadow-lg p-6 w-full max-w-4xl h-[500px] border-2 border-white/20 backdrop-blur-[20px] shadow-black/20 text-white flex flex-col items-center justify-center text-center">
                {challengeStatus === "completed" ? (
                    <>
                        <h3 className="text-white text-4xl font-bold">Congratulations!</h3>
                        <p className="mt-4 text-xl">You have completed today's challenge.</p>
                        <p className="text-purple-400 mt-2">Challenge: {challengeExercise.name}</p>
                        <svg className="mt-8 w-24 h-24 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </>
                ) : (
                    <>
                        <h3 className="text-white text-4xl font-bold mb-4">Your Challenge Today:</h3>
                        <p className="text-purple-400 text-3xl font-bold">{challengeExercise?.name || "No challenge assigned"}</p>
                        <p className="mt-4 text-lg">Complete this exercise successfully to mark the challenge as done for today.</p>
                        <button
                            onClick={handleStartChallenge}
                            className="mt-8 bg-white text-black px-6 py-3 rounded-full font-semibold hover:bg-neutral-200 transition-colors"
                        >
                            Start Challenge
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};

export default DS;