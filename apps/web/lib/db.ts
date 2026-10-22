import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";
import {
  pgTable,
  text,
  timestamp,
  integer,
  bigint,
  index,
} from "drizzle-orm/pg-core";
export const users = pgTable("users", {
  id: text("id").primaryKey(),
  createdAt: timestamp("created_at", { withTimezone: true })
    .defaultNow()
    .notNull(),
});
export const scans = pgTable(
  "scan_sessions",
  {
    id: text("id").primaryKey(),
    userId: text("user_id")
      .references(() => users.id, { onDelete: "cascade" })
      .notNull(),
    localScanId: text("local_scan_id").notNull(),
    mode: text("mode").notNull(),
    status: text("status").notNull(),
    totalBytes: bigint("total_bytes", { mode: "number" }).notNull(),
    candidateCount: integer("candidate_count").notNull(),
    verifiedCount: integer("verified_count").notNull(),
    likelyCount: integer("likely_count").notNull(),
    startedAt: timestamp("started_at", { withTimezone: true }).notNull(),
    createdAt: timestamp("created_at", { withTimezone: true })
      .defaultNow()
      .notNull(),
  },
  (t) => [index("scans_user_created_idx").on(t.userId, t.createdAt)],
);
export function database() {
  if (!process.env.DATABASE_URL)
    throw Error("Cloud metadata storage is not configured");
  return drizzle(neon(process.env.DATABASE_URL));
}
