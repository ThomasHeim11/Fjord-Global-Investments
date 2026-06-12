import { describe, expect, it } from "vitest";
import { cleanTitle, formatDate, sourceParts } from "../src/format";
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

describe("sourceParts", () => {
  const src = (kind: string, ref = ""): Source => ({ kind, ref, detail: "" });

  it("maps each source kind to a label, with a file on letters", () => {
    const out = sourceParts([
      src("register", "FGI-001"),
      src("letter", "letter:lux.pdf"),
      src("board_update", "12"),
      src("finding", "x"),
    ]);
    expect(out).toEqual([
      { label: "the register", file: undefined },
      { label: "lux.pdf", file: "lux.pdf" },
      { label: "board notifications", file: undefined },
      { label: "review findings", file: undefined },
    ]);
  });

  it("de-duplicates repeated sources", () => {
    expect(sourceParts([src("register", "a"), src("register", "b")]))
      .toEqual([{ label: "the register", file: undefined }]);
  });

  it("strips the letter: prefix to get the filename", () => {
    expect(sourceParts([src("letter", "letter: netherlands.pdf")]))
      .toEqual([{ label: "netherlands.pdf", file: "netherlands.pdf" }]);
  });

  it("returns an empty list for no sources", () => {
    expect(sourceParts([])).toEqual([]);
  });
});
