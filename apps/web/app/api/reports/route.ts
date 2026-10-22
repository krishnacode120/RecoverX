import { auth, authConfigured } from "@/lib/auth";
import { database, users, scans } from "@/lib/db";
import { summarySchema } from "@/lib/report";
import { and, desc, eq } from "drizzle-orm";
import { randomUUID } from "node:crypto";
async function identity() {
  if (!authConfigured || !process.env.DATABASE_URL) return null;
  return (await auth())?.user?.id;
}
function sameOrigin(request: Request) {
  return (
    request.headers.get("origin") === new URL(request.url).origin &&
    request.headers.get("content-type")?.startsWith("application/json")
  );
}
async function boundedJson(request: Request) {
  const reader = request.body?.getReader();
  if (!reader) throw Error("Body missing");
  let size = 0;
  const chunks: Uint8Array[] = [];
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > 8192) throw Error("Body too large");
      chunks.push(value);
    }
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } finally {
    await reader.cancel();
  }
}
export async function GET() {
  const id = await identity();
  if (!id)
    return Response.json(
      { error: "Sign in and configure cloud storage" },
      { status: 401 },
    );
  try {
    const results = await database()
      .select()
      .from(scans)
      .where(eq(scans.userId, id))
      .orderBy(desc(scans.createdAt))
      .limit(100);
    return Response.json(results, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json(
      { error: "Cloud storage unavailable" },
      { status: 503 },
    );
  }
}
export async function POST(request: Request) {
  const id = await identity();
  if (!id) return Response.json({ error: "Unauthorized" }, { status: 401 });
  if (!sameOrigin(request))
    return Response.json({ error: "Origin rejected" }, { status: 403 });
  let parsed;
  try {
    parsed = summarySchema.safeParse(await boundedJson(request));
  } catch {
    return Response.json(
      { error: "Invalid or oversized request" },
      { status: 400 },
    );
  }
  if (!parsed.success)
    return Response.json({ error: "Invalid summary" }, { status: 400 });
  const s = parsed.data;
  try {
    const db = database();
    await db.insert(users).values({ id }).onConflictDoNothing();
    await db
      .insert(scans)
      .values({
        id: randomUUID(),
        userId: id,
        localScanId: s.scanId,
        mode: s.mode,
        status: s.status,
        totalBytes: s.totalBytes,
        candidateCount: s.candidates,
        verifiedCount: s.verified,
        likelyCount: s.likely,
        startedAt: new Date(s.startedAt),
      });
    return Response.json({ saved: true }, { status: 201 });
  } catch {
    return Response.json(
      { error: "Cloud storage unavailable" },
      { status: 503 },
    );
  }
}
export async function DELETE(request: Request) {
  const id = await identity();
  if (!id) return Response.json({ error: "Unauthorized" }, { status: 401 });
  if (!sameOrigin(request))
    return Response.json({ error: "Origin rejected" }, { status: 403 });
  try {
    const body = await boundedJson(request);
    const db = database();
    if (body.all === true) await db.delete(users).where(eq(users.id, id));
    else if (typeof body.id === "string")
      await db
        .delete(scans)
        .where(and(eq(scans.id, body.id), eq(scans.userId, id)));
    else return Response.json({ error: "Specify id or all" }, { status: 400 });
    return Response.json({ deleted: true });
  } catch {
    return Response.json({ error: "Deletion failed" }, { status: 503 });
  }
}
