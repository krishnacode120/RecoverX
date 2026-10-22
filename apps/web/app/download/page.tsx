import Link from "next/link";
import { Brand } from "@/components/brand";
export default function Download() {
  return (
    <>
      <header className="site-nav wrap">
        <Brand />
        <Link href="/docs">Installation guide ↗</Link>
      </header>
      <main id="main" className="document">
        <div className="eyebrow">WINDOWS DESKTOP / EARLY RELEASE</div>
        <h1>Recovery starts on your machine.</h1>
        <p>
          The desktop engine scans raw images and explicitly authorized devices
          locally. It never requires a cloud account.
        </p>
        <div className="note">
          <h3>Signed installer not yet published</h3>
          <p>
            There is no verified public release artifact to download yet. Use
            the source build instructions until release qualification and
            signing are complete.
          </p>
        </div>
        <h2>Run from source</h2>
        <pre>{`python -m venv .venv\n.venv\\Scripts\\activate\npip install -e ".[desktop]"\nrecoverx-desktop`}</pre>
        <p>
          Requires Python 3.12+ on Windows x64. Packaging scripts are included
          in the repository. Do not install onto the affected disk.
        </p>
        <Link href="/docs">Read the complete recovery guide →</Link>
      </main>
    </>
  );
}
