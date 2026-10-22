import Link from "next/link";
import { Brand } from "@/components/brand";
export const metadata = { title: "Recovery guide" };
export default function Docs() {
  return (
    <>
      <header className="site-nav wrap">
        <Brand />
        <Link href="/dashboard">Open workspace ↗</Link>
      </header>
      <main id="main" className="document">
        <div className="eyebrow">DOCUMENTATION / V0.1</div>
        <h1>A careful approach to recovery.</h1>
        <p>
          RecoverX analyzes readable raw disk images locally. This release
          prioritizes verifiable output and conservative metadata
          interpretation.
        </p>
        <h2 id="safety">Before you begin</h2>
        <ol>
          <li>
            Stop using the affected storage. New writes may overwrite deleted
            content.
          </li>
          <li>
            Install RecoverX on another disk. Save images and recovered files to
            separate physical storage.
          </li>
          <li>
            If the disk disconnects, clicks, or repeatedly fails reads, stop and
            consult a specialist. This release stops imaging at the first read
            error.
          </li>
          <li>
            Work from an image. Do not repair, format, or run recovery tests on
            the original.
          </li>
        </ol>
        <h2>Install and run</h2>
        <p>
          Use Python 3.12+ and the project source while signed builds are being
          prepared. Local operation requires no account.
        </p>
        <pre>{`python -m venv .venv\n.venv\\Scripts\\activate\npip install -e ".[desktop]"\nrecoverx-desktop`}</pre>
        <h2>Scan an image</h2>
        <p>
          Choose a raw .img, .dd, or .raw file. Quick scan inspects FAT32/exFAT
          deleted entries. Deep scan searches raw bytes and validates supported
          file structures. Pause or cancel in the desktop app; deep scans can
          resume from committed checkpoints.
        </p>
        <pre>{`recoverx scan disk.img --mode deep --db history.sqlite --report scan.json\nrecoverx recover disk.img SCAN_ID E:\\Recovered --db history.sqlite`}</pre>
        <h2>Understand the evidence</h2>
        <ul>
          <li>
            <strong>Verified intact:</strong> the configured decoder or checksum
            checks passed. This is format-level evidence, not proof of the
            file’s original identity.
          </li>
          <li>
            <strong>Likely recoverable:</strong> extents or structural
            boundaries are resolved, with limitations shown in the evidence.
          </li>
          <li>
            <strong>Uncertain or damaged:</strong> a signature or filename was
            found, but this release cannot safely export complete bytes.
          </li>
          <li>
            <strong>Export verified:</strong> the saved file’s SHA-256 matches
            bytes hashed during the scan. Metadata-only candidates may still
            contain overwritten content.
          </li>
        </ul>
        <h2>View a report here</h2>
        <p>
          Export JSON in the desktop app, then import it in{" "}
          <Link href="/dashboard">the workspace</Link>. Reports contain
          filenames and offsets. They stay in browser memory and disappear on
          reload. Optional account storage saves only aggregate counts after an
          explicit action.
        </p>
        <h2 id="limitations">Current capability limits</h2>
        <ul>
          <li>
            FAT32: active directory traversal and deleted short-name entries.
            Only unallocated single-cluster files have extractable extents.
            Missing multi-cluster chains are not guessed.
          </li>
          <li>
            exFAT: deleted root-directory files, explicit contiguous allocation
            or surviving FAT chains, checked against the allocation bitmap.
            Nested directory recovery is not yet supported.
          </li>
          <li>
            PNG, JPEG, BMP and WebP: image decoding; PNG also checks CRCs. GIF
            checks structure and first frame. ZIP and Office containers: bounded
            member CRC validation.
          </li>
          <li>
            PDF, WAV, AVI, MP4/MOV, SQLite and 7z: limited structural carving;
            full document/media/database decoding is not performed.
          </li>
          <li>
            TIFF, RAR, MKV, MP3 and FLAC: signature discovery only, without
            extraction. Plain text requires metadata.
          </li>
          <li>
            Carving is contiguous and capped at 32 MiB per candidate.
            Metadata-guided extraction streams larger files subject to extent
            limits.
          </li>
          <li>
            NTFS/ext4 metadata, EWF, VHD/VHDX and QCOW containers are not
            qualified for this release. Supply a raw image.
          </li>
          <li>
            Overwritten data, SSD TRIM, inaccessible encryption and physical
            damage are outside RecoverX’s recovery capabilities.
          </li>
        </ul>
        <h2>Troubleshooting</h2>
        <p>
          “No supported filesystem” means quick scan could not find a supported
          volume; deep scan may still find readable structures. “Source changed”
          means the image was modified or replaced; restart analysis.
          “Destination exists” requires a different folder or filename.
          Permission-denied raw access requires an authorized administrator
          session; the app never elevates itself.
        </p>
        <p>
          <Link href="/download">Desktop distribution status →</Link>
        </p>
      </main>
    </>
  );
}
