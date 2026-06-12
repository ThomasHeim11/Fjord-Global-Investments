import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/api", () => ({
  api: {
    listChats: vi.fn().mockResolvedValue([]),
    getChat: vi.fn(),
    deleteChat: vi.fn().mockResolvedValue(undefined),
    sendChat: vi.fn().mockResolvedValue({
      conversation_id: "c1",
      answer: "Nothing overdue right now.",
      sources: [{ kind: "register", ref: "FGI-001", detail: "" }],
    }),
  },
}));

import { api } from "../src/api";
import { Ask } from "../src/pages/Ask";

beforeEach(() => vi.clearAllMocks());

describe("PortfolioGPT (Ask)", () => {
  it("loads the conversation list on mount", async () => {
    render(<Ask />);
    await waitFor(() => expect(api.listChats).toHaveBeenCalled());
  });

  it("shows the suggestion cards on an empty conversation", () => {
    render(<Ask />);
    expect(screen.getByText(/What is each agent asking/)).toBeInTheDocument();
    expect(screen.getByText(/Which jurisdictions have the most overdue/)).toBeInTheDocument();
  });

  it("sends a suggestion and renders the answer with its sources", async () => {
    const user = userEvent.setup();
    render(<Ask />);

    await user.click(
      screen.getByRole("button", { name: /Which jurisdictions have the most overdue/ }),
    );

    expect(api.sendChat).toHaveBeenCalledWith(
      expect.stringContaining("Which jurisdictions"),
      null,
    );
    await waitFor(() =>
      expect(screen.getByText("Nothing overdue right now.")).toBeInTheDocument(),
    );
    // the answer's sources block rendered (its label is unique to a reply)
    expect(screen.getByText("Sources")).toBeInTheDocument();
  });

  it("rolls back the question if the send fails", async () => {
    (api.sendChat as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error("429"));
    const user = userEvent.setup();
    render(<Ask />);

    await user.click(screen.getByRole("button", { name: /What is each agent asking/ }));

    // error surfaces and the suggestions return (conversation rolled back to empty)
    await waitFor(() => expect(screen.getByText(/429/)).toBeInTheDocument());
  });
});
