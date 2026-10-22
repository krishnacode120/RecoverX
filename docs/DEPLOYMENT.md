# Deployment

## Vercel web

Create a project for the repository, select **apps/web** as root and the Next.js framework. Use `npm ci` and `npm run build`; `vercel.json` is included. Set the deployment to Node 22 or 24. No native engine code runs in Vercel Functions. Confirm `/api/health`, `/`, `/docs`, `/download`, `/dashboard`, `/contact`, and `/account` after deployment.

For cloud accounts, provision a private PostgreSQL/Neon database and apply `database/migrations/0000_foundation.sql`. Set `DATABASE_URL`, a strong `AUTH_SECRET`, `AUTH_GITHUB_ID`, `AUTH_GITHUB_SECRET`, and `AUTH_URL` to the canonical HTTPS application origin. GitHub OAuth callback: `https://<your-domain>/api/auth/callback/github`. Do not commit `.env.local`.

Without credentials the public website and browser-local report workspace work, while the account page clearly reports unavailable cloud configuration. Cloud storage has not been verified until real sign-in, owner isolation, save and deletion have been tested. Migration includes connected-agent/recovery/audit tables reserved for future integration; current endpoints use users and scan_sessions.

The included GitHub workflow verifies source/builds on pushes and pull requests. Vercel Git integration can deploy after those checks. Publishing native artifacts is manual until signing credentials and a target repository are supplied. No workflow fabricates success or posts a download URL.

## Windows distribution

Run `scripts/package-windows.ps1` on Windows x64 with Python dependencies installed. It creates a PyInstaller app directory and invokes Inno Setup if found. Install as the current user by default. Raw device access remains an explicit administrator action. The installer includes an uninstaller and license notice. Public release requires actual Authenticode signing, independent safety tests, a checksum, and GitHub Release verification. Only then should the website expose the verified installer URL.

## Current blockers

No repository remote, Vercel project/authorization, GitHub OAuth client, database URL, production domain or signing certificate was supplied. A public deployment cannot be claimed from a local build. Inspect VERIFICATION.md for the current build/packaging outcome.

References consulted during implementation: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [Vercel Function limitations](https://vercel.com/docs/functions/limitations), [The Sleuth Kit licensing](https://www.sleuthkit.org/sleuthkit/licenses.php). Versioned installed dependencies and the lockfile are the implementation baseline.
