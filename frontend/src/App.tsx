import { BrowserRouter, Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { Ask } from "./pages/Ask";
import { Dashboard } from "./pages/Dashboard";
import { Entities } from "./pages/Entities";
import { EntityDetail } from "./pages/EntityDetail";

export default function App() {
  return (
    <BrowserRouter>
      <header className="topbar">
        <Link to="/" className="brand">
          <img src="/favicon.svg" alt="" className="brand-logo" />
          Fjord Global Investments
        </Link>
        <nav>
          <NavLink to="/" end>Review</NavLink>
          <NavLink to="/entities">Register</NavLink>
          <NavLink to="/ask">PortfolioGPT</NavLink>
        </nav>
      </header>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/entities" element={<Entities />} />
        <Route path="/entities/:id" element={<EntityDetail />} />
        <Route path="/ask" element={<Ask />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
