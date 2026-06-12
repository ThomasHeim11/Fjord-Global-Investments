import { describe, expect, it } from "vitest";
import { cleanTitle, formatDate, sourceSummary } from "../src/format";
import type { Source } from "../src/chatStore";

describe("formatDate", () => {
  it("formats a backend timestamp to a readable date", () => {
    expect(formatDate("2026-06-11 13:50:52")).toBe("11 Jun 2026");
  });

  it("falls back to the first 10 chars for unparseable input", () => {
    expect(formatDate("not-a-date-string")).toBe("not-a-date");
  });
});

describe("cleanTitle", () => {
  it("drops the em-dash comparison tail", () => {
    expect(cleanTitle("Mandate expired — letter says X, register says Y", null))
      .toBe("Mandate expired");
  });

  it("removes (N/A) placeholders", () => {
    expect(cleanTitle("Filing overdue (N/A)", null)).toBe("Filing overdue");
  });

  it("strips the entity id when the badge already shows it", () => {
    expect(cleanTitle("Mandate expired (FGI-067)", "FGI-067")).toBe("Mandate expired");
  });

  it("trims trailing punctuation and collapses whitespace", () => {
    expect(cleanTitle("Records   disagree:  ", null)).toBe("Records disagree");
  });

  it("leaves a clean title unchanged", () => {
    expect(cleanTitle("Board mandate expired", null)).toBe("Board mandate expired");
  });
});

describe("sourceSummary", () => {
  const src = (kind: string, ref = ""): Source => ({ kind, ref, detail: "" });

  it("maps each source kind to plain language", () => {
    const out = sourceSummary([
      src("register", "FGI-001"),
      src("letter", "letter:lux.pdf"),
      src("board_update", "12"),
      src("finding", "x"),
    ]);
    expect(out).toBe("the register · lux.pdf · board notifications · review findings");
  });

  it("de-duplicates repeated sources", () => {
    const out = sourceSummary([src("register", "a"), src("register", "b")]);
    expect(out).toBe("the register");
  });

  it("strips the letter: prefix from filenames", () => {
    expect(sourceSummary([src("letter", "letter:netherlands.pdf")]))
      .toBe("netherlands.pdf");
  });

  it("returns an empty string for no sources", () => {
    expect(sourceSummary([])).toBe("");
  });
});
