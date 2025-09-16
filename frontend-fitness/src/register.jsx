import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

const RegisterForm = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [re_password, setRe_password] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!email || !password || !re_password) {
      setError("Please fill in all fields.");
      return;
    }

    if (password !== re_password) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }
    
    setError("");
    setLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:5000/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password: password,
          re_password: re_password,
        }),
      });

      const data = await response.json();

      if (data.success) {
        // Store the JWT token in localStorage
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        
        // Navigate to home page
        navigate("/home");
      } else {
        setError(data.error || "Registration failed. Please try again.");
      }
    } catch (error) {
      console.error('Registration error:', error);
      setError("Network error. Please check your connection and try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative bg-[url('/img.jpg')]">
      <form
        onSubmit={handleSubmit}
        className="relative z-10 bg-transparent rounded-2xl shadow-lg p-6 w-full max-w-xs border-2 border-white/20 backdrop-blur-[20px] shadow-black/20 text-white"
      >
        <h2 className="text-3xl font-bold mb-6 text-center text-white">Register</h2>
        {error && (
          <div className="text-red-400 mb-4 p-2 bg-red-900/20 border border-red-400/20 rounded text-sm">
            {error}
          </div>
        )}
        <div className="mb-4 relative">
          <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="white" viewBox="0 0 448 512" stroke="white">
              <path d="M224 256A128 128 0 1 0 224 0a128 128 0 1 0 0 256zm-45.7 48C79.8 304 0 383.8 0 482.3C0 498.7 13.3 512 29.7 512l388.6 0c16.4 0 29.7-13.3 29.7-29.7C448 383.8 368.2 304 269.7 304l-91.4 0z" />
            </svg>
          </span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-10 py-2 border-2 border-white/20 rounded-3xl focus:outline-none focus:ring-1 focus:ring-purple-400 bg-white/10 text-white placeholder-gray-300"
            required
            placeholder="Email"
            disabled={loading}
          />
        </div>
        <div className="mb-4 relative">
          <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="white">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m6-6V9a6 6 0 10-12 0v2m12 0a2 2 0 012 2v6a2 2 0 01-2 2H6a2 2 0 01-2-2v-6a2 2 0 012-2m12 0H6" />
            </svg>
          </span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-10 py-2 border-2 border-white/20 rounded-3xl focus:outline-none focus:ring-2 focus:ring-purple-400 bg-white/10 text-white placeholder-gray-300"
            required
            placeholder="Password"
            disabled={loading}
          />
        </div>
        <div className="mb-6 relative">
          <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="white" viewBox="0 0 512 512" stroke="white">
              <path d="M336 352c97.2 0 176-78.8 176-176S433.2 0 336 0S160 78.8 160 176c0 18.7 2.9 36.8 8.3 53.7L7 391c-4.5 4.5-7 10.6-7 17l0 80c0 13.3 10.7 24 24 24l80 0c13.3 0 24-10.7 24-24l0-40 40 0c13.3 0 24-10.7 24-24l0-40 40 0c6.4 0 12.5-2.5 17-7l33.3-33.3c16.9 5.4 35 8.3 53.7 8.3zM376 96a40 40 0 1 1 0 80 40 40 0 1 1 0-80z" />
            </svg>
          </span>
          <input
            type="password"
            value={re_password}
            onChange={(e) => setRe_password(e.target.value)}
            className="w-full px-10 py-2 border-2 border-white/20 rounded-3xl focus:outline-none focus:ring-2 focus:ring-purple-400 bg-white/10 text-white placeholder-gray-300"
            required
            placeholder="Re-enter Password"
            disabled={loading}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3 rounded-3xl text-sm font-bold transition ${
            loading
              ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
              : 'bg-white text-black hover:bg-neutral-200'
          }`}
        >
          {loading ? 'Creating Account...' : 'Register'}
        </button>
        <div className="mt-4 text-center text-sm text-white">
          Already have an account?{" "}
          <Link
            to="/"
            className="text-white hover:underline font-medium"
          >
            Login
          </Link>
        </div>
      </form>
    </div>
  );
};

export default RegisterForm;