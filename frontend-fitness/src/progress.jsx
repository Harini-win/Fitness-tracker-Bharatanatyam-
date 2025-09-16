import React, { useState, useEffect, useRef } from "react";
import Chart from 'chart.js/auto'; // Import Chart.js
import { getAuthToken } from "./authUtils";

const Progress = () => {
    const chartRef = useRef(null);
    const [progressData, setProgressData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchProgressData = async () => {
            setLoading(true);
            setError(null);
            const token = getAuthToken();
            if (!token) {
                setError("Authentication token missing. Please log in.");
                setLoading(false);
                return;
            }

            try {
                const response = await fetch('http://127.0.0.1:5000/api/progress', {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                });

                if (!response.ok) {
                    throw new Error("Failed to fetch progress data.");
                }

                const data = await response.json();
                if (data.success) {
                    setProgressData(data.progress);
                } else {
                    setError(data.error || "An error occurred.");
                }

            } catch (err) {
                console.error("Fetch error:", err);
                setError("Network error or server issue. Please try again later.");
            } finally {
                setLoading(false);
            }
        };

        fetchProgressData();
    }, []);

    useEffect(() => {
        if (progressData.length > 0 && chartRef.current) {
            // Destroy any existing chart instance before creating a new one
            if (chartRef.current.chart) {
                chartRef.current.chart.destroy();
            }

            const ctx = chartRef.current.getContext('2d');
            const dates = progressData.map(item => item.date);
            const counts = progressData.map(item => item.count);

            chartRef.current.chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Correct Reps Per Day',
                        data: counts,
                        backgroundColor: 'rgba(128, 90, 213, 0.2)',
                        borderColor: 'rgb(128, 90, 213)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(255, 255, 255, 0.2)'
                            },
                            ticks: {
                                color: 'white'
                            },
                            title: {
                                display: true,
                                text: 'Repetitions',
                                color: 'white'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(255, 255, 255, 0.2)'
                            },
                            ticks: {
                                color: 'white'
                            },
                            title: {
                                display: true,
                                text: 'Date',
                                color: 'white'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
    }, [progressData]);

    const renderContent = () => {
        if (loading) {
            return <p>Loading your progress...</p>;
        }
        if (error) {
            return <p className="text-red-400">{error}</p>;
        }
        if (progressData.length === 0) {
            return <p>No data to display yet. Start an exercise to see your progress!</p>;
        }
        return (
            <div className="relative w-full h-full">
                <canvas ref={chartRef}></canvas>
            </div>
        );
    };

    return (
        <div className="min-h-screen flex items-center justify-center relative bg-[url('/img.jpg')] flex-col">
            <div className="justify-center mb-8 relative z-20 text-white text-4xl font-bold">
                <h2>Dashboard</h2>
            </div>
            <div className="relative z-10 bg-transparent rounded-2xl shadow-lg p-6 w-full max-w-4xl h-[500px] border-2 border-white/20 backdrop-blur-[20px] shadow-black/20 text-white flex items-center justify-center text-center">
                {renderContent()}
            </div>
        </div>
    );
};

export default Progress;