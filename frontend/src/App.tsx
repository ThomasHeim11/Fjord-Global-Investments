/**
 * App shell: sets up routing, the review context provider, and the top
 * navigation bar. Defines all top-level routes (Review, Register, PortfolioGPT).
 */
import { BrowserRouter, Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import { ReviewProvider, useReview } from "./ReviewContext";
import { Ask } from "./pages/Ask";
import { Dashboard } from "./pages/Dashboard";
import { Entities } from "./pages/Entities";
import { EntityDetail } from "./pages/EntityDetail";

/**
 * Thin top progress bar, shown on every page while a review is running, so the
 * scan keeps visibly working even after you navigate away from Review.
 */
function TopProgress() {
  const { running } = useReview();
  if (!running) return null;
  return (
    <div className="progress-top" role="progressbar" aria-label="Reviewing">
      <span />
    </div>
  );
}

/** Root component: wires up the router, review context, nav bar, and routes. */
export default function App() {
  return (
    <BrowserRouter>
      <ReviewProvider>
        <TopProgress />
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
      </ReviewProvider>
    </BrowserRouter>
  );
}
