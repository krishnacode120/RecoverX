import { describe, it, expect } from "vitest";
import { reportSchema, summarySchema, bytes } from "../lib/report";
import generatedReport from "./fixtures/recovery-report.json";
const base = {
  version: 1,
  scan: {
    id: "a".repeat(32),
    mode: "deep",
    status: "complete",
    checkpoint: 1024,
    total: 1024,
    started_at: "2026-10-22T00:00:00+00:00",
  },
  candidates: [],
};
describe("untrusted report validation", () => {
  it("accepts an actual Python scan with microsecond timestamps and extents", () => {
    const report = reportSchema.parse(generatedReport);
    expect(report.candidates).toHaveLength(2);
    expect(report.candidates[0].sha256).toBe("b2b635e8592e2c53fd99cb89db5515c1b694e5ade929bd08f93c905ca651ce00");
  });
  it("accepts an actual empty scan", () =>
    expect(reportSchema.safeParse(base).success).toBe(true));
  it("rejects invented progress", () =>
    expect(
      reportSchema.safeParse({
        ...base,
        scan: { ...base.scan, checkpoint: 2048 },
      }).success,
    ).toBe(false));
  it("rejects unknown versions", () =>
    expect(reportSchema.safeParse({ ...base, version: 2 }).success).toBe(
      false,
    ));
  it("blocks filenames from cloud summary", () =>
    expect(
      summarySchema.safeParse({
        scanId: "a".repeat(32),
        mode: "deep",
        status: "complete",
        totalBytes: 10,
        candidates: 1,
        verified: 1,
        likely: 0,
        startedAt: base.scan.started_at,
        filename: "private.txt",
      }).success,
    ).toBe(false));
  it("formats measured bytes", () => {
    expect(bytes(0)).toBe("0 B");
    expect(bytes(1024)).toBe("1.0 KB");
  });
});
