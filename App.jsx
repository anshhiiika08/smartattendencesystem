import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/home";
import Login from "./pages/Login";
import RegisterStudent from "./pages/RegisterStudents";
import Attendance from "./pages/Attendance";
import Dashboard from "./pages/Dashboard";
import Report from "./pages/Report";
import Students from "./pages/Students";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<RegisterStudent />} />
        <Route path="/attendance" element={<Attendance />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/report" element={<Report />}/>
        <Route path="/students" element={<Students />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;