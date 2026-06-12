import { describe, expect, it } from "vitest";
import { CATEGORY_LABELS, SEVERITY_LABELS, SOURCE_LABELS } from "../src/labels";

describe("labels", () => {
  it("maps severities to the plain-language urgency names", () => {
    expect(SEVERITY_LABELS.critical).toBe("Act now");
    expect(SEVERITY_LABELS.warning).toBe("Review soon");
    expect(SEVERITY_LABELS.info).toBe("For awareness");
  });

  it("translates internal categories to legal-friendly labels", () => {
    expect(CATEGORY_LABELS.mandate).toBe("Board mandate");
    expect(CATEGORY_LABELS.conflict).toBe("Records disagree");
    expect(CATEGORY_LABELS.unknown_entity).toBe("Unknown entity");
  });

  it("explains each detection source in human terms", () => {
    expect(SOURCE_LABELS["llm:reconciliation"]).toContain("Agent letter");
    expect(SOURCE_LABELS["llm:analysis"]).toContain("Register");
  });
});
