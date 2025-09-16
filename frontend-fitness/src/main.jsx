import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { BrowserRouter, Routes, Route } from "react-router-dom";
import LoginForm from "./login";
import RegisterForm from "./register";
import FitnessDashboard from "./home";
import Work from "./workout";
import Progress from "./progress";
import Dance from "./dance";
import DS from "./daily_challenge";

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
    <Routes>
      <Route path="/" element={<LoginForm />} />
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/home" element={<FitnessDashboard />} />
      <Route path="/work" element={<Work />} />
      <Route path="/progress" element={<Progress />} />
      <Route path="/dance" element={<Dance />} />
      <Route path="/daily_challenge" element={<DS />} />
    </Routes>
  </BrowserRouter>
  </StrictMode>
)
