import Link from "next/link";
import {
  ArrowDown,
  ArrowUpRight,
  ArrowRight,
  Check,
  Fingerprint,
  HardDrive,
  LockKeyhole,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import { Brand } from "@/components/brand";
import { RecoveryDemo } from "@/components/recovery-demo";
import styles from "./home.module.css";

const questions = [
  [
    "Is a deleted file really gone?",
    "Deleting a file can leave its contents behind until the storage reuses that space. RecoverX looks for surviving filesystem records and readable content. Recovery depends on what remains; it is never guaranteed.",
  ],
  [
    "What about files deleted from an SSD?",
    "SSD TRIM can make deleted blocks inaccessible. No recovery software can recreate overwritten or TRIM-discarded bytes. Stop using the affected drive and preserve it before attempting recovery.",
  ],
  [
    "Does this website access my drive?",
    "No. Scanning and extraction run in the Windows desktop app. The web workspace only reads reports you choose to import. The animation above is an illustration, not a scan of your computer.",
  ],
  [
    "What can the current version recover?",
    "Version 0.3 supports conservative NTFS, FAT32 and exFAT deleted-entry analysis, plus signature-based carving of supported formats. Some filesystem layouts and file types remain unsupported. Read the documentation for the exact scope.",
  ],
  [
    "Is RecoverX ready for critical evidence?",
    "This is a development release tested on generated images and real Windows deletions on a disposable virtual disk. Hardware qualification, independent review and signed distribution remain outstanding. Use specialist support for irreplaceable data.",
  ],
];

export default function Home() {
  return (
    <div className={styles.home}>
      <header className={styles.nav}>
        <Brand />
        <nav aria-label="Main navigation">
          <Link href="#workflow">The process</Link>
          <Link href="/docs">Documentation</Link>
        </nav>
        <Link className={styles.navAction} href="/dashboard">
          Open workspace <ArrowUpRight size={16} />
        </Link>
      </header>
      <main id="main">
        <section className={styles.hero} aria-labelledby="hero-title">
          <div className={styles.heroCopy}>
            <div className={styles.eyebrow}>
              <span /> YOUR FILES. STILL WORTH LOOKING FOR.
            </div>
            <h1 id="hero-title">
              Not everything
              <br />
              lost is <em>gone.</em>
            </h1>
            <p>
              Find what remains. Recover what matters.
              <br />A local recovery engine that turns surviving data into files
              you can inspect, restore, and verify.
            </p>
            <div className={styles.actions}>
              <Link className={styles.primary} href="/download">
                Explore the desktop app <ArrowUpRight size={18} />
              </Link>
              <Link className={styles.textLink} href="#workflow">
                See how it works <ArrowDown size={16} />
              </Link>
            </div>
            <div className={styles.assurances}>
              <span>
                <ShieldCheck size={15} /> Read-only source access
              </span>
              <span>
                <LockKeyhole size={14} /> Local by default
              </span>
            </div>
          </div>
          <RecoveryDemo />
          <div className={styles.heroBottom}>
            <span>RECOVERX / DEVELOPMENT EDITION 0.3</span>
            <span>
              Built around the evidence. <ArrowDown size={14} />
            </span>
          </div>
        </section>
        <div className={styles.formats} aria-label="Supported source types">
          <span>
            LOOK BENEATH
            <br />
            THE FILESYSTEM
          </span>
          <strong>NTFS</strong>
          <strong>FAT32</strong>
          <strong>exFAT</strong>
          <strong>Raw images</strong>
          <span>
            Windows desktop
            <br />
            No account required
          </span>
        </div>
        <section
          id="workflow"
          className={styles.workflow}
          aria-labelledby="workflow-title"
        >
          <div className={styles.sectionHead}>
            <div>
              <div className={styles.eyebrow}>01 / THE PROCESS</div>
              <h2 id="workflow-title">
                From missing.
                <br />
                To found. To verified.
              </h2>
            </div>
            <p>
              Recovery should be understandable.
              <br />
              Follow the evidence at every step.
            </p>
          </div>
          <div className={styles.steps}>
            <article>
              <div className={styles.stepMark}>
                <HardDrive size={27} strokeWidth={1.3} />
                <span>01</span>
              </div>
              <h3>Choose the source.</h3>
              <p>
                Select a Windows drive or a raw disk image. The engine opens the
                source for reading, with explicit consent for direct drive
                access.
              </p>
              <Link href="/docs">
                Source & safety guide <ArrowUpRight size={15} />
              </Link>
            </article>
            <article>
              <div className={styles.stepMark}>
                <ScanLine size={27} strokeWidth={1.3} />
                <span>02</span>
              </div>
              <h3>Inspect what remains.</h3>
              <p>
                Find surviving deleted entries or recognizable file signatures.
                Review names, allocation evidence, and supported previews before
                exporting.
              </p>
              <Link href="/dashboard">
                Explore the report workspace <ArrowUpRight size={15} />
              </Link>
            </article>
            <article>
              <div className={styles.stepMark}>
                <Fingerprint size={27} strokeWidth={1.3} />
                <span>03</span>
              </div>
              <h3>Recover with evidence.</h3>
              <p>
                Export complete candidates to separate storage. SHA-256 checks
                verify that the exported bytes match the bytes you scanned.
              </p>
              <Link href="/docs#safety">
                Understand verification <ArrowUpRight size={15} />
              </Link>
            </article>
          </div>
        </section>
        <section className={styles.privacy} aria-labelledby="privacy-title">
          <div>
            <div className={styles.eyebrow}>02 / YOUR DATA STAYS YOURS</div>
            <h2 id="privacy-title">
              On your machine.
              <br />
              <span>In your control.</span>
            </h2>
            <p>
              Your disk is not a cloud upload. The desktop engine does the
              recovery work locally. Bring only the reports you choose into the
              web workspace.
            </p>
            <Link className={styles.textLink} href="/docs#safety">
              Our approach to safe recovery <ArrowUpRight size={17} />
            </Link>
          </div>
          <div className={styles.boundary}>
            <div className={styles.boundaryTop}>
              <LockKeyhole size={16} />
              <span>THE LOCAL BOUNDARY</span>
              <span>DESKTOP</span>
            </div>
            <div className={styles.boundaryFlow}>
              <div>
                <HardDrive size={30} strokeWidth={1.3} />
                <strong>Your source</strong>
                <small>Read only</small>
              </div>
              <ArrowRight size={20} />
              <div>
                <Fingerprint size={30} strokeWidth={1.3} />
                <strong>Your output</strong>
                <small>Separate storage</small>
              </div>
            </div>
            <div className={styles.boundaryLine}>
              <Check size={15} /> No source writes
            </div>
            <div className={styles.boundaryLine}>
              <Check size={15} /> No silent disk uploads
            </div>
            <div className={styles.boundaryLine}>
              <Check size={15} /> You choose every export
            </div>
            <div className={styles.boundaryFoot}>
              The website views reports. It cannot scan your drive.
            </div>
          </div>
        </section>
        <section className={styles.faq} aria-labelledby="faq-title">
          <div>
            <div className={styles.eyebrow}>03 / BEFORE YOU BEGIN</div>
            <h2 id="faq-title">
              A little clarity.
              <br />
              Before recovery.
            </h2>
            <p>
              Real possibilities.
              <br />
              Honest limitations.
            </p>
          </div>
          <div>
            {questions.map(([question, answer]) => (
              <details key={question}>
                <summary>
                  {question}
                  <span aria-hidden="true">+</span>
                </summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>
        <section className={styles.closing}>
          <div className={styles.eyebrow}>START WITH WHAT REMAINS</div>
          <h2>
            Give your files
            <br />a second look.
          </h2>
          <Link className={styles.primary} href="/download">
            Get started with RecoverX <ArrowUpRight size={19} />
          </Link>
          <p>
            Windows desktop · Development release · Recovery is not guaranteed
          </p>
        </section>
      </main>
      <footer className={styles.footer}>
        <Brand />
        <span>Built to recover. Designed to protect.</span>
        <Link href="/docs">Documentation</Link>
        <Link href="/contact">
          Contact <ArrowUpRight size={13} />
        </Link>
      </footer>
    </div>
  );
}
