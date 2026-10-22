import { z } from "zod";
const integer = z.number().int().nonnegative().max(Number.MAX_SAFE_INTEGER);
export const statuses = [
  "Verified intact",
  "Likely recoverable",
  "Partially recoverable",
  "Damaged",
  "Uncertain",
  "Unrecoverable with currently accessible information",
] as const;
export const reportSchema = z
  .object({
    version: z.literal(1),
    scan: z
      .object({
        id: z.string().regex(/^[a-f0-9]{32}$/),
        mode: z.enum(["quick", "deep"]),
        status: z.enum(["running", "complete", "cancelled", "failed"]),
        checkpoint: integer,
        total: integer,
        started_at: z.string().datetime({ offset: true }),
      })
      .refine((s) => s.checkpoint <= s.total, "Progress exceeds source size"),
    candidates: z
      .array(
        z.object({
          id: z.string().regex(/^[a-f0-9]{32}$/),
          name: z.string().max(1024),
          kind: z.string().max(32),
          size: integer,
          status: z.enum(statuses),
          method: z.string().max(128),
          reasons: z.array(z.string().max(2048)).max(32),
          extents: z
            .array(z.object({ offset: integer, length: integer }))
            .max(131072),
          sha256: z
            .string()
            .regex(/^[a-f0-9]{64}$/)
            .nullable(),
        }),
      )
      .max(10000),
    privacy: z.string().max(1024).optional(),
  })
  .superRefine((report, ctx) => {
    const ids = new Set<string>();
    report.candidates.forEach((c, i) => {
      if (ids.has(c.id))
        ctx.addIssue({
          code: "custom",
          path: ["candidates", i],
          message: "Duplicate candidate ID",
        });
      ids.add(c.id);
      if (c.extents.some((e) => e.offset + e.length > report.scan.total))
        ctx.addIssue({
          code: "custom",
          path: ["candidates", i],
          message: "Extent outside source",
        });
    });
  });
export type Report = z.infer<typeof reportSchema>;
export function bytes(n: number) {
  if (n === 0) return "0 B";
  const p = Math.min(4, Math.floor(Math.log(n) / Math.log(1024)));
  return `${(n / 1024 ** p).toFixed(p ? 1 : 0)} ${["B", "KB", "MB", "GB", "TB"][p]}`;
}
export const summarySchema = z
  .object({
    scanId: z.string().regex(/^[a-f0-9]{32}$/),
    mode: z.enum(["quick", "deep"]),
    status: z.enum(["running", "complete", "cancelled", "failed"]),
    totalBytes: integer,
    candidates: integer.max(10000),
    verified: integer.max(10000),
    likely: integer.max(10000),
    startedAt: z.string().datetime({ offset: true }),
  })
  .strict()
  .refine((s) => s.verified + s.likely <= s.candidates, "Invalid totals");
