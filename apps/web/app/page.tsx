import Link from "next/link";
import {
  ArrowUpRight,
  ArrowRight,
  ShieldCheck,
  HardDrive,
  Fingerprint,
  ScanLine,
  FileCheck2,
  LockKeyhole,
  Monitor,
  Check,
} from "lucide-react";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
export default function Home() {
  return (
    <>
      <header className="site-nav wrap">
        <Brand />
        <nav aria-label="Main navigation">
          <Link href="#workflow">How it works</Link>
          <Link href="/docs">Documentation</Link>
          <Link href="/download">Desktop app</Link>
        </nav>
        <Button asChild variant="outline">
          <Link href="/dashboard">
            Open workspace <ArrowUpRight size={16} />
          </Link>
        </Button>
      </header>
      <main id="main">
        <section className="hero wrap">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="live-dot" /> LOCAL-FIRST DATA RECOVERY
            </div>
            <h1>
              Some things
              <br />
              are worth
              <br />
              <span>recovering.</span>
            </h1>
            <p>
              Find the files that still remain. Analyze disk images, inspect the
              evidence, and restore your data with a recovery engine that keeps
              you in control.
            </p>
            <div className="hero-actions">
              <Button asChild>
                <Link href="/download">
                  <Monitor size={18} /> Get the desktop app{" "}
                  <ArrowRight size={16} />
                </Link>
              </Button>
              <Button asChild variant="ghost">
                <Link href="/dashboard">
                  Explore workspace <ArrowUpRight size={16} />
                </Link>
              </Button>
            </div>
            <div className="hero-assurances">
              <span>
                <Check size={14} /> Read-only analysis
              </span>
              <span>
                <Check size={14} /> No account required locally
              </span>
            </div>
          </div>
          <div className="hero-visual" aria-label="Recovery workflow diagram">
            <div className="visual-top">
              <span>
                <span className="live-dot" /> RECOVERY ARCHITECTURE
              </span>
              <span>01 — 03</span>
            </div>
            <div className="orbital">
              <div className="orbit orbit-one" />
              <div className="orbit orbit-two" />
              <div className="disk-core">
                <HardDrive size={66} strokeWidth={1} />
                <div>YOUR DATA</div>
                <small>stays on your machine</small>
              </div>
              <span className="floating-label tag-one">
                <LockKeyhole size={14} /> Read-only source
              </span>
              <span className="floating-label tag-two">
                <Fingerprint size={14} /> SHA-256 verification
              </span>
            </div>
            <div className="visual-pipeline">
              <div>
                <span>01</span> Image source
              </div>
              <ArrowRight size={16} />
              <div>
                <span>02</span> Find evidence
              </div>
              <ArrowRight size={16} />
              <div>
                <span>03</span> Verify export
              </div>
            </div>
            <div className="visual-foot">
              <ShieldCheck size={15} /> No source writes. No silent uploads.
            </div>
          </div>
        </section>
        <div className="compatibility wrap">
          <span>BUILT AROUND YOUR STORAGE</span>
          <div>Raw disk images</div>
          <div>FAT32 metadata</div>
          <div>exFAT metadata</div>
          <div>Windows desktop</div>
        </div>
        <section id="workflow" className="section wrap">
          <div className="section-heading">
            <div>
              <div className="eyebrow">A CLEAR PATH BACK</div>
              <h2>Recovery you can inspect.</h2>
            </div>
            <p>
              Every result has evidence. Every export is checked.
              <br />
              You decide what happens next.
            </p>
          </div>
          <div className="steps">
            {[
              {
                icon: HardDrive,
                n: "01",
                title: "Start with a safe source",
                text: "Open a raw disk image, or explicitly authorize read-only imaging of a Windows device onto separate storage.",
              },
              {
                icon: ScanLine,
                n: "02",
                title: "Look beneath the surface",
                text: "Read deleted directory entries or scan raw bytes. Inspect file boundaries, allocation evidence, and validation results.",
              },
              {
                icon: FileCheck2,
                n: "03",
                title: "Restore. Then verify.",
                text: "Export selected candidates to a separate destination. SHA-256 checks confirm the output matches the scanned bytes.",
              },
            ].map((s) => (
              <article key={s.n}>
                <div className="step-top">
                  <s.icon size={26} />
                  <span>{s.n}</span>
                </div>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="privacy-band wrap">
          <div className="privacy-icon">
            <ShieldCheck size={46} strokeWidth={1.2} />
          </div>
          <div>
            <div className="eyebrow">PRIVATE BY DESIGN</div>
            <h2>Your storage isn’t a cloud upload.</h2>
            <p>
              The desktop engine performs recovery locally. The web workspace
              reads only the scan reports you choose to import. Disk contents
              and recovered files stay with you.
            </p>
          </div>
          <Link href="/docs#safety">
            Read the safety guide <ArrowUpRight size={17} />
          </Link>
        </section>
        <section className="section wrap">
          <div className="section-heading">
            <div>
              <div className="eyebrow">KNOW BEFORE YOU SCAN</div>
              <h2>Clear expectations. Better decisions.</h2>
            </div>
          </div>
          <div className="faq">
            {[
              [
                "Can RecoverX recover every deleted file?",
                "No. Recovery depends on readable bytes that still exist. Overwritten data, SSD TRIM-discarded blocks, inaccessible encryption, and physical media failure cannot be reversed by this software.",
              ],
              [
                "Can the website scan my USB drive?",
                "No. Device access runs in the Windows desktop application. This website is a report viewer and documentation platform; it has no physical sector access.",
              ],
              [
                "Which files can it find?",
                "The initial engine validates common images and ZIP-based documents, and structurally carves PDF, RIFF media, SQLite, ISO media, and 7z. Some other signatures remain unresolved. See the capability matrix for exact limits.",
              ],
              [
                "Is this release ready for critical evidence?",
                "This is an experimental first release with generated-image tests. Physical-device qualification, independent security review, and signed distribution are release gates. Preserve original media and use specialist support for irreplaceable data.",
              ],
            ].map(([q, a]) => (
              <details key={q}>
                <summary>
                  {q}
                  <span>+</span>
                </summary>
                <p>{a}</p>
              </details>
            ))}
          </div>
        </section>
      </main>
      <footer className="wrap footer">
        <Brand />
        <span>Built to recover. Designed to protect.</span>
        <Link href="/docs">Documentation</Link>
        <Link href="/contact">Contact & support</Link>
      </footer>
    </>
  );
}
