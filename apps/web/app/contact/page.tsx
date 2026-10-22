import Link from "next/link";
import { Brand } from "@/components/brand";
export default function Contact() {
  return (
    <>
      <header className="site-nav wrap">
        <Brand />
        <Link href="/docs">Documentation ↗</Link>
      </header>
      <main id="main" className="document">
        <h1>Help with RecoverX.</h1>
        <p>
          This early release has no hosted support inbox. For local
          troubleshooting, consult the recovery guide and repository
          documentation.
        </p>
        <h2>Prepare a useful issue report</h2>
        <p>
          Record the app version, operation, error category and a minimal
          reproduction on disposable test data. Do not share disk images,
          recovered files, sensitive filenames or private storage paths.
        </p>
        <h2>Irreplaceable or physically damaged media</h2>
        <p>
          Stop using the source. Repeated reads can worsen some hardware
          failures. Seek a qualified data recovery laboratory before attempting
          further scans.
        </p>
        <Link href="/docs">Open the troubleshooting guide →</Link>
      </main>
    </>
  );
}
