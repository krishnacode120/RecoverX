"use client";
import { useRef, useState } from "react";
import Link from "next/link";
import { motion } from "motion/react";
import {
  AreaChart,
  LayoutDashboard,
  HardDrive,
  Disc3,
  ScanLine,
  FolderCheck,
  History,
  FileText,
  Settings2,
  ShieldCheck,
  Upload,
  ArrowUpRight,
  Search,
  X,
  CircleHelp,
  Download,
  CheckCheck,
  File,
  AlertCircle,
} from "lucide-react";
import { BarChart, Bar, XAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Brand } from "./brand";
import { Button } from "./ui/button";
import { bytes, reportSchema, type Report } from "@/lib/report";
import { useReports } from "@/lib/store";

const sections = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Devices", icon: HardDrive },
  { name: "Disk images", icon: Disc3 },
  { name: "Recovery results", icon: FolderCheck },
  { name: "Scan history", icon: History },
  { name: "Reports", icon: FileText },
  { name: "Settings", icon: Settings2 },
];
export function Workspace() {
  const { reports, active, add, select, clear } = useReports();
  const [section, setSection] = useState("Overview"),
    [query, setQuery] = useState(""),
    [filter, setFilter] = useState("all"),
    [page, setPage] = useState(0),
    [error, setError] = useState(""),
    [detail, setDetail] = useState<Report["candidates"][number] | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const report = reports.find((r) => r.scan.id === active),
    candidates = report?.candidates;
  const filtered = [...(candidates ?? [])]
    .filter(
      (c) =>
        c.name.toLowerCase().includes(query.toLowerCase()) &&
        (filter === "all" || c.status === filter),
    )
    .sort((a, b) => a.name.localeCompare(b.name));
  const verified = (candidates ?? []).filter(
    (c) => c.status === "Verified intact",
  ).length;
  const extractable = (candidates ?? []).filter((c) => c.sha256).length;
  const chart = Object.entries(
    (candidates ?? []).reduce(
      (a, c) => ({ ...a, [c.kind]: (a[c.kind] ?? 0) + 1 }),
      {} as Record<string, number>,
    ),
  )
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);
  async function importReport(file: File) {
    try {
      setError("");
      if (file.size > 10 * 1024 * 1024)
        throw Error("Reports must be 10 MB or smaller.");
      const parsed = reportSchema.safeParse(JSON.parse(await file.text()));
      if (!parsed.success)
        throw Error("This file is not a valid RecoverX v1 scan report.");
      add(parsed.data);
      setPage(0);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not read report");
    }
  }
  function download() {
    if (!report) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `recoverx-${report.scan.id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <div className="workspace">
      <aside className="sidebar">
        <Brand />
        <div className="workspace-label">
          LOCAL WORKSPACE <span>01</span>
        </div>
        <nav aria-label="Workspace">
          {sections.map((s, i) => (
            <button
              key={s.name}
              className={section === s.name ? "active" : ""}
              onClick={() => {
                setSection(s.name);
                setPage(0);
              }}
            >
              <s.icon size={18} />
              {s.name}
              {i === 3 && !!candidates?.length && (
                <small>{candidates.length}</small>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-guide">
          <ShieldCheck size={22} />
          <h4>Safe by default.</h4>
          <p>
            Recovery runs locally.
            <br />
            Your data stays yours.
          </p>
          <Link href="/docs">
            Read the recovery guide <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">RX</span>
          <div>
            Personal workspace<small>Report viewer · v0.1</small>
          </div>
          <Link href="/account" aria-label="Account settings">
            <Settings2 size={18} />
          </Link>
        </div>
      </aside>
      <div className="workspace-main">
        <header className="workspace-top">
          <div>
            Workspace <span>/</span> <strong>{section}</strong>
          </div>
          <div>
            <span className="local-badge">
              <span className="live-dot" /> Browser-local reports
            </span>
            <Link href="/docs" aria-label="Help">
              <CircleHelp size={19} />
            </Link>
          </div>
        </header>
        <main id="main" className="workspace-content">
          <div className="workspace-heading">
            <div className="eyebrow">YOUR RECOVERY CONTROL CENTER</div>
            <div className="heading-row">
              <div>
                <h1>
                  {section === "Overview"
                    ? "A clearer path to your files."
                    : section}
                </h1>
                <p>
                  Inspect real scan evidence. Keep every recovery decision in
                  your hands.
                </p>
              </div>
              <Button onClick={() => input.current?.click()}>
                <Upload size={16} /> Import scan report
              </Button>
            </div>
          </div>
          <input
            type="file"
            accept=".json,application/json"
            ref={input}
            className="sr-only"
            aria-label="Import RecoverX JSON report"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void importReport(file);
              e.target.value = "";
            }}
          />
          {error && (
            <div role="alert" className="error-banner">
              <AlertCircle size={18} />
              {error}
              <button onClick={() => setError("")} aria-label="Dismiss error">
                <X size={16} />
              </button>
            </div>
          )}
          <div className="agent-banner">
            <div className="agent-icon">
              <HardDrive size={22} />
            </div>
            <div>
              <strong>Your recovery engine lives on your computer.</strong>
              <p>
                Open the desktop app to scan a device or disk image, then bring
                its report here.
              </p>
            </div>
            <Button asChild variant="outline">
              <Link href="/download">
                Desktop setup <ArrowUpRight size={15} />
              </Link>
            </Button>
          </div>
          {section === "Overview" && (
            <>
              <div className="stats">
                {[
                  {
                    label: "Imported scans",
                    value: reports.length,
                    icon: ScanLine,
                    sub: "In this browser session",
                  },
                  {
                    label: "File candidates",
                    value: candidates?.length ?? 0,
                    icon: File,
                    sub: "From the selected report",
                  },
                  {
                    label: "Verified structures",
                    value: verified,
                    icon: CheckCheck,
                    sub: "Decoder or checksum evidence",
                  },
                  {
                    label: "Extractable candidates",
                    value: extractable,
                    icon: FolderCheck,
                    sub: "Extent bytes hashed during scan",
                  },
                ].map((s, i) => (
                  <motion.article
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                    key={s.label}
                  >
                    <div>
                      <span>{s.label}</span>
                      <s.icon size={17} />
                    </div>
                    <strong>{s.value.toLocaleString()}</strong>
                    <small>{s.sub}</small>
                  </motion.article>
                ))}
              </div>
              <div className="overview-grid">
                <section className="panel">
                  <div className="panel-heading">
                    <h2>Scan activity</h2>
                    <span className="subtle-label">
                      {report
                        ? report.scan.mode.toUpperCase()
                        : "AWAITING A REPORT"}
                    </span>
                  </div>
                  {report ? (
                    <div className="scan-progress">
                      <div>
                        <strong>{report.scan.status}</strong>
                        <span>
                          {bytes(report.scan.checkpoint)} /{" "}
                          {bytes(report.scan.total)}
                        </span>
                      </div>
                      <progress
                        max={report.scan.total || 1}
                        value={report.scan.checkpoint}
                      />
                      <p>
                        Captured{" "}
                        {new Date(report.scan.started_at).toLocaleString()} ·
                        This is a saved report, not a live device connection.
                      </p>
                    </div>
                  ) : (
                    <div className="empty-activity">
                      <div className="scan-empty-icon">
                        <ScanLine size={31} strokeWidth={1.3} />
                      </div>
                      <h3>Your next recovery starts locally.</h3>
                      <p>
                        When you import a scan report, its actual progress
                        <br />
                        and discovered candidates appear here.
                      </p>
                      <button onClick={() => input.current?.click()}>
                        Import your first report <ArrowRightIcon />
                      </button>
                    </div>
                  )}
                </section>
                <section className="panel">
                  <div className="panel-heading">
                    <h2>File types</h2>
                    <AreaChart size={17} />
                  </div>
                  {chart.length ? (
                    <div className="chart">
                      <ResponsiveContainer width="100%" height={190}>
                        <BarChart data={chart}>
                          <XAxis
                            dataKey="name"
                            stroke="#8c9db5"
                            fontSize={11}
                          />
                          <Tooltip
                            contentStyle={{
                              background: "#101d31",
                              border: "1px solid #30435e",
                              borderRadius: 8,
                            }}
                          />
                          <Bar
                            dataKey="count"
                            fill="#398af6"
                            radius={[4, 4, 0, 0]}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  ) : (
                    <div className="empty-chart">
                      <div className="chart-placeholder">
                        <i />
                        <i />
                        <i />
                        <i />
                        <i />
                      </div>
                      <strong>No file data yet</strong>
                      <p>A breakdown appears after import.</p>
                    </div>
                  )}
                </section>
              </div>
            </>
          )}
          {["Overview", "Recovery results", "Reports"].includes(section) && (
            <section className="panel results-panel">
              <div className="panel-heading">
                <h2>
                  {section === "Reports"
                    ? "Report details"
                    : "Recovery candidates"}{" "}
                  <span>{candidates?.length ?? 0}</span>
                </h2>
                <div className="panel-actions">
                  {reports.length > 0 && (
                    <select
                      aria-label="Select imported scan"
                      value={active ?? ""}
                      onChange={(e) => {
                        select(e.target.value);
                        setPage(0);
                      }}
                    >
                      {reports.map((r) => (
                        <option key={r.scan.id} value={r.scan.id}>
                          {r.scan.mode} · {r.scan.id.slice(0, 8)}
                        </option>
                      ))}
                    </select>
                  )}
                  <Button variant="ghost" disabled={!report} onClick={download}>
                    <Download size={15} /> Export report
                  </Button>
                </div>
              </div>
              <div className="table-toolbar">
                <div className="search">
                  <Search size={16} />
                  <input
                    placeholder="Search filenames…"
                    aria-label="Search filenames"
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setPage(0);
                    }}
                  />
                </div>
                <select
                  aria-label="Filter recovery status"
                  value={filter}
                  onChange={(e) => {
                    setFilter(e.target.value);
                    setPage(0);
                  }}
                >
                  <option value="all">All statuses</option>
                  {[
                    "Verified intact",
                    "Likely recoverable",
                    "Uncertain",
                    "Damaged",
                  ].map((s) => (
                    <option key={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>File name ↑</th>
                      <th>Type</th>
                      <th>Size</th>
                      <th>Recovery status</th>
                      <th>Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.slice(page * 25, (page + 1) * 25).map((c) => (
                      <tr key={c.id}>
                        <td>
                          <File size={16} />
                          {c.name}
                        </td>
                        <td>{c.kind.toUpperCase()}</td>
                        <td>{bytes(c.size)}</td>
                        <td>
                          <span
                            className={
                              c.status === "Verified intact"
                                ? "status good"
                                : "status"
                            }
                          >
                            {c.status}
                          </span>
                        </td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() => setDetail(c)}
                          >
                            Inspect <ArrowUpRight size={13} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!filtered.length && (
                <div className="table-empty">
                  <FolderCheck size={26} />
                  <strong>
                    {report
                      ? "No matching candidates"
                      : "No recovery candidates yet"}
                  </strong>
                  <p>
                    {report
                      ? "Try another filter or review the scan’s scope."
                      : "Import a genuine desktop scan report to review files and their evidence."}
                  </p>
                </div>
              )}
              <div className="table-foot">
                <span>
                  {filtered.length
                    ? `${page * 25 + 1}–${Math.min((page + 1) * 25, filtered.length)} of ${filtered.length}`
                    : "Only actual scan results appear here."}
                </span>
                <div>
                  <button
                    disabled={page === 0}
                    onClick={() => setPage(page - 1)}
                  >
                    Previous
                  </button>
                  <button
                    disabled={(page + 1) * 25 >= filtered.length}
                    onClick={() => setPage(page + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </section>
          )}
          {section === "Scan history" && (
            <section className="panel history-list">
              <h2>Imported in this session</h2>
              {reports.length ? (
                reports.map((r) => (
                  <button
                    key={r.scan.id}
                    onClick={() => {
                      select(r.scan.id);
                      setSection("Recovery results");
                    }}
                  >
                    <ScanLine size={20} />
                    <span>
                      {r.scan.id}
                      <small>
                        {new Date(r.scan.started_at).toLocaleString()} ·{" "}
                        {r.scan.mode}
                      </small>
                    </span>
                    <span>{r.candidates.length} candidates</span>
                    <ArrowUpRight size={16} />
                  </button>
                ))
              ) : (
                <p>
                  Import a scan report to start your history. Closing this page
                  clears local report data.
                </p>
              )}
            </section>
          )}
          {["Devices", "Disk images"].includes(section) && (
            <section className="panel feature-empty">
              <Disc3 size={44} />
              <h2>
                {section === "Devices"
                  ? "Device access stays native."
                  : "Analyze your disk image locally."}
              </h2>
              <p>
                {section === "Devices"
                  ? "The website cannot read physical disk sectors. Discover devices and explicitly authorize imaging in the desktop app."
                  : "Open a raw .img, .raw, or .dd file in the desktop app. Cloud disk-image uploads are not enabled in this release."}
              </p>
              <Button asChild>
                <Link href="/docs">
                  View the recovery procedure <ArrowUpRight size={16} />
                </Link>
              </Button>
            </section>
          )}
          {section === "Settings" && (
            <section className="panel feature-empty">
              <ShieldCheck size={40} />
              <h2>You control your reports.</h2>
              <p>
                Imported filenames and offsets stay in browser memory. Nothing
                is uploaded automatically. Clear this session at any time. Cloud
                summaries require a separate sign-in and an explicit save.
              </p>
              <Button
                variant="outline"
                onClick={() => {
                  clear();
                  setDetail(null);
                  setPage(0);
                }}
              >
                Clear all imported reports
              </Button>
              <Link href="/account" className="text-button">
                Manage cloud account <ArrowUpRight size={15} />
              </Link>
            </section>
          )}
          <div className="workspace-footer">
            <ShieldCheck size={14} /> Imported reports stay in browser memory.
            <span>
              Recovery isn’t guaranteed.{" "}
              <Link href="/docs#limitations">
                Understand the limits <ArrowUpRight size={12} />
              </Link>
            </span>
          </div>
          {detail && (
            <div className="detail-backdrop" onClick={() => setDetail(null)}>
              <section
                role="dialog"
                aria-modal="true"
                aria-label="Candidate evidence"
                className="detail-modal"
                onClick={(e) => e.stopPropagation()}
              >
                <Button
                  autoFocus
                  variant="ghost"
                  className="close-detail"
                  onClick={() => setDetail(null)}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") setDetail(null);
                  }}
                >
                  <X size={19} /> Close
                </Button>
                <div className="eyebrow">CANDIDATE EVIDENCE</div>
                <h2>{detail.name}</h2>
                <p className="status">{detail.status}</p>
                <ul>
                  {detail.reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
                <dl>
                  <dt>Method</dt>
                  <dd>{detail.method}</dd>
                  <dt>Scanned content SHA-256</dt>
                  <dd className="hash">
                    {detail.sha256 ?? "No complete extractable content"}
                  </dd>
                  <dt>Resolved extents</dt>
                  <dd>{detail.extents.length}</dd>
                </dl>
                <p>
                  Recovery and file preview are available in the native app. A
                  scan hash identifies observed bytes; it does not prove they
                  match the original lost file.
                </p>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
function ArrowRightIcon() {
  return <span aria-hidden="true">→</span>;
}
