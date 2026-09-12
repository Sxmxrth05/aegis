import { Route, Routes } from 'react-router-dom';
import { CustomCursor } from './components/shared/CustomCursor';
import { NavBar } from './components/shared/NavBar';
import { useAegisSocket } from './lib/websocket';
import Landing from './pages/Landing';
import Monitor from './pages/Monitor';
import Negotiate from './pages/Negotiate';
import Trajectory from './pages/Trajectory';
import History from './pages/History';
import About from './pages/About';

export default function App() {
  // Mounted once here (not per-page) so the connection and its status
  // persist across route changes — the NavBar's live indicator needs it
  // regardless of which page is showing.
  useAegisSocket();

  return (
    <div className="min-h-screen bg-background">
      <CustomCursor />
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
