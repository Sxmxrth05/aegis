import { Route, Routes } from 'react-router-dom';
import { NavBar } from './components/shared/NavBar';
import Landing from './pages/Landing';
import Monitor from './pages/Monitor';
import Negotiate from './pages/Negotiate';
import Trajectory from './pages/Trajectory';
import History from './pages/History';
import About from './pages/About';

export default function App() {
  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/monitor" element={<Monitor />} />
        <Route path="/negotiate/:id?" element={<Negotiate />} />
        <Route path="/negotiate/:id/trajectory" element={<Trajectory />} />
        <Route path="/history" element={<History />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </div>
  );
}
