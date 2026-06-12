import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { FindingCard } from "../src/components/FindingCard";
import type { Finding } from "../src/types";

// react-pdf needs a canvas (jsdom has none), so stub the viewer and assert the
// props the card passes it.
vi.mock("../src/components/PdfViewer", () => ({
  PdfViewer: (props: { url: string; filename: string; highlight: string }) => (
    <div data-testid="pdf-viewer" data-url={props.url} data-highlight={props.highlight}>
      {props.filename}
    </div>
  ),
}));

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

  it("opens the in-app PDF viewer on the right letter, highlighting the quoted line", async () => {
    const user = userEvent.setup();
    renderCard(
      makeFinding({
        category: "conflict",
        evidence: { letter_says: "2026-06-19", register_says: "2028-01-10", letter: "lux.pdf" },
      }),
    );
    expect(screen.queryByTestId("pdf-viewer")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /lux\.pdf/ }));
    const viewer = await screen.findByTestId("pdf-viewer");
    expect(viewer).toHaveAttribute("data-url", expect.stringContaining("/api/letters/lux.pdf"));
    expect(viewer).toHaveAttribute("data-highlight", "2026-06-19");
  });

  it("extracts the inner name as the highlight term for unknown-entity findings", async () => {
    const user = userEvent.setup();
    renderCard(
      makeFinding({
        category: "unknown_entity",
        entity_id: null,
        evidence: { letter_says: "names 'FGI Amsterdam Office II B.V.'", register_says: "not present", letter: "nl.pdf" },
      }),
    );
    await user.click(screen.getByRole("button", { name: /nl\.pdf/ }));
    expect(await screen.findByTestId("pdf-viewer")).toHaveAttribute(
      "data-highlight",
      "FGI Amsterdam Office II B.V.",
    );
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
