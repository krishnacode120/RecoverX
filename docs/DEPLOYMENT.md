# Deployment

## Vercel web

Create a project for the repository, select **apps/web** as root and the Next.js framework. Use `npm ci` and `npm run build`; `vercel.json` is included. Set the deployment to Node 22 or 24. No native engine code runs in Vercel Functions. Confirm `/api/health`, `/`, `/docs`, `/download`, `/dashboard`, `/contact`, and `/account` after deployment.

For cloud accounts, provision a private PostgreSQL/Neon database and apply `database/migrations/0000_foundation.sql`. Set `DATABASE_URL`, a strong `AUTH_SECRET`, `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET`, and `AUTH_URL` to the canonical HTTPS application origin. GitHub OAuth callback: `https://<your-domain>/api/auth/callback/github`. Do not commit `.env.local`.

Without credentials the public website and browser-local report workspace work, while the account page clearly reports unavailable cloud configuration. Cloud storage has not been verified until real sign-in, owner isolation, save and deletion have been tested. Migration includes connected-agent/recovery/audit tables reserved for future integration; current endpoints use users and scan_sessions.

The included GitHub workflow verifies source/builds on pushes and pull requests. The private repository is [krishnacode120/RecoverX](https://github.com/krishnacode120/RecoverX), default branch `main`. Vercel Git integration can deploy after those checks. Publishing native artifacts is manual until signing and release qualification are complete. No workflow fabricates success or posts a download URL.

## Windows distribution

Run `scripts/package-windows.ps1` on Windows x64 with Python dependencies installed. It creates a PyInstaller app directory and invokes Inno Setup if found. Install as the current user by default. Raw device access remains an explicit administrator action. The installer includes an uninstaller and license notice. Public release requires actual Authenticode signing, independent safety tests, a checksum, and GitHub Release verification. Only then should the website expose the verified installer URL.

## Verified deployment — 2026-10-24

The public website is live at [recoverx-flax.vercel.app](https://recoverx-flax.vercel.app). The Vercel project `recover_x` previously failed with `PYTHON_ENTRYPOINT_NOT_FOUND` because its root directory was empty and its framework preset was Python. Its root directory is now `apps/web`, framework Next.js, and Node version 24.x. The checked-in `apps/web/vercel.json` supplies `npm ci` and `npm run build`.

[Production deployment 4eJBHLaDGxzsYu9D4QytAgqDPBwj](https://vercel.com/krishnas-projects-2e3bf37a/recover_x/4eJBHLaDGxzsYu9D4QytAgqDPBwj) rebuilt commit `393ca6cb9a1a071139131ae0804e6e96423d3e71` successfully with the corrected project settings. Both `Vercel – web` and `Vercel – recover_x` report success for that commit. `/api/health`, `/`, `/docs`, `/download`, `/dashboard`, `/contact`, and `/account` each returned HTTP 200 on the production domain; the homepage was also inspected in a browser. Health reported `status: ok`, `diskAccess: false`, and `uploads: false`. The web service retains its independent 0.1.0 package version; the desktop recovery package is 0.3.0.

These checks verify deployment and route availability, not authenticated database behavior. The account page explicitly reports that cloud service is not configured; GitHub OAuth, AUTH_SECRET, and PostgreSQL configuration are still required. Owner isolation, cloud save/delete integration, hardware qualification, and signing remain separate release gates. No authentication or deployment protection settings were weakened to repair the build.

References consulted during implementation: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [Vercel Function limitations](https://vercel.com/docs/functions/limitations), [The Sleuth Kit licensing](https://www.sleuthkit.org/sleuthkit/licenses.php). Versioned installed dependencies and the lockfile are the implementation baseline.
