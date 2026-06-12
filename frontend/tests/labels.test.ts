import { describe, expect, it } from "vitest";
import { CATEGORY_LABELS, SEVERITY_LABELS, SOURCE_LABELS } from "../src/labels";

describe("labels", () => {
  it("maps severities to the High/Medium/Low risk scale", () => {
    expect(SEVERITY_LABELS.critical).toBe("High");
    expect(SEVERITY_LABELS.warning).toBe("Medium");
    expect(SEVERITY_LABELS.info).toBe("Low");
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
