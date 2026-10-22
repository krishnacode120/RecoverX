"use client";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useReports } from "@/lib/store";
import { Button } from "./ui/button";
type Summary = {
  id: string;
  mode: string;
  candidateCount: number;
  createdAt: string;
};
export function CloudAccount() {
  const { reports, active } = useReports();
  const report = reports.find((r) => r.scan.id === active);
  const [message, setMessage] = useState("");
  const client = useQueryClient();
  const query = useQuery<Summary[]>({
    queryKey: ["cloud-summaries"],
    queryFn: async () => {
      const r = await fetch("/api/reports");
      if (!r.ok)
        throw Error("Cloud history is unavailable. Check database setup.");
      return r.json();
    },
    retry: false,
  });
  async function change(method: string, body: unknown) {
    setMessage("");
    try {
      const response = await fetch("/api/reports", {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok)
        throw Error("The request failed; no success has been confirmed.");
      setMessage(
        method === "POST"
          ? "Aggregate summary saved. No filenames or contents uploaded."
          : "Cloud metadata deleted.",
      );
      await client.invalidateQueries({ queryKey: ["cloud-summaries"] });
    } catch (e) {
      setMessage(String(e));
    }
  }
  function save() {
    if (!report) return;
    void change("POST", {
      scanId: report.scan.id,
      mode: report.scan.mode,
      status: report.scan.status,
      totalBytes: report.scan.total,
      candidates: report.candidates.length,
      verified: report.candidates.filter((c) => c.status === "Verified intact")
        .length,
      likely: report.candidates.filter((c) => c.status === "Likely recoverable")
        .length,
      startedAt: report.scan.started_at,
    });
  }
  return (
    <section>
      <h2>Private cloud summaries</h2>
      <p>
        Save only the selected report’s aggregate counts, source size, scan mode
        and timestamps. Filenames, paths, file bytes and candidate hashes are
        excluded.
      </p>
      <div className="account-actions">
        <Button disabled={!report} onClick={save}>
          Save selected report summary
        </Button>
        <Button
          variant="outline"
          onClick={() => void change("DELETE", { all: true })}
        >
          Delete all my cloud metadata
        </Button>
      </div>
      <p aria-live="polite">{message}</p>
      {query.isPending ? (
        <p>Loading cloud history…</p>
      ) : query.isError ? (
        <p role="alert">{query.error.message}</p>
      ) : query.data.length ? (
        query.data.map((r) => (
          <div key={r.id} className="cloud-row">
            <span>
              {r.mode} · {r.candidateCount} candidates ·{" "}
              {new Date(r.createdAt).toLocaleDateString()}
            </span>
            <Button
              variant="ghost"
              onClick={() => void change("DELETE", { id: r.id })}
            >
              Delete
            </Button>
          </div>
        ))
      ) : (
        <p>No cloud summaries saved.</p>
      )}
    </section>
  );
}
