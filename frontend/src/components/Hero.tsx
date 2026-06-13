/**
 * Landing hero: a full-bleed photo with the live entity count overlaid as a
 * headline number, mirroring oljefondet's fund-value landing.
 */
import { useEffect, useState } from "react";
import { api } from "../api";
import heroImage from "../../picture/image.png";

/**
 * Full-bleed photo with a defining headline number overlaid. The run action
 * lives in the sticky bar below, so the hero stays a clean header.
 */
export function Hero() {
  const [entities, setEntities] = useState<number | null>(null);

  useEffect(() => {
    api
      .getEntities({})
      .then((e) => setEntities(e.length))
      .catch(() => {});
  }, []);

  return (
    <div
      className="hero-banner"
      style={{ backgroundImage: `url(${heroImage})` }}
    >
      <div className="hero-banner-inner">
        <div className="hero-banner-label">FGI Subsidiary Portfolio</div>
        <div className="hero-banner-number">
          {entities ?? "…"}
          {/* 18 = the fund's stated operating footprint. The register holds a
              19th distinct value ("Noveria"), which is itself a flagged anomaly. */}
          <span className="hero-banner-unit">
            entities across 18 jurisdictions
          </span>
        </div>
        <div className="hero-banner-tagline">
          Spot the governance risks hiding in your register.
        </div>
      </div>
    </div>
  );
}
