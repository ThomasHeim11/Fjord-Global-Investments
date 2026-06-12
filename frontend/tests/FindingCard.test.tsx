import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { FindingCard } from "../src/components/FindingCard";
import type { Finding } from "../src/types";

function makeFinding(overrides: Partial<Finding> = {}): Finding {
  return {
    id: 1,
    run_id: 1,
    category: "mandate",
    severity: "critical",
    entity_id: "FGI-067",
    entity_name: "FGI Singapore Solar III",
    title: "Mandate expired (FGI-067)",
    description: "The board mandate expired 8 days ago.",
    evidence: {},
    recommendation: "Prepare a renewal resolution before the board meeting.",
    detected_by: "llm:analysis",
    ...overrides,
  };
}

function renderCard(finding: Finding) {
  return render(
    <MemoryRouter>
      <FindingCard finding={finding} />
    </MemoryRouter>,
  );
}

describe("FindingCard", () => {
  it("shows the plain-language severity and category labels", () => {
    renderCard(makeFinding());
    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getByText("Board mandate")).toBeInTheDocument();
  });

  it("cleans the entity id out of the title (the badge already shows it)", () => {
    renderCard(makeFinding());
    expect(screen.getByRole("heading", { name: "Mandate expired" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "FGI-067" })).toHaveAttribute(
      "href",
      "/entities/FGI-067",
    );
  });

  it("renders the recommendation when present", () => {
    renderCard(makeFinding());
    expect(screen.getByText("What to do")).toBeInTheDocument();
    expect(screen.getByText(/Prepare a renewal resolution/)).toBeInTheDocument();
  });

  it("shows the letter-vs-register comparison when evidence has it", () => {
    renderCard(
      makeFinding({
        category: "conflict",
        evidence: { letter_says: "2026-06-19", register_says: "2028-01-10", letter: "lux.pdf" },
      }),
    );
    expect(screen.getByText("2026-06-19")).toBeInTheDocument();
    expect(screen.getByText("2028-01-10")).toBeInTheDocument();
    expect(screen.getByText(/Per the agent letter/)).toBeInTheDocument();
  });

  it("omits the comparison box when there is no comparison evidence", () => {
    renderCard(makeFinding({ evidence: {} }));
    expect(screen.queryByText("vs")).not.toBeInTheDocument();
  });

  it("falls back to the raw detection source when unmapped", () => {
    renderCard(makeFinding({ detected_by: "llm:resolution" }));
    expect(screen.getByText(/Notification matched to the register/)).toBeInTheDocument();
  });
});
