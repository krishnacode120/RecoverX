# Installation

Install Python 3.12 or newer on Windows x64. Use another physical disk from the media being recovered. Create a virtual environment at the repository root and run `pip install -e ".[desktop]"`. Launch `recoverx-desktop`. No administrator rights are needed for ordinary raw image files.

Raw physical disk reads can require an explicitly launched administrator session. RecoverX never elevates itself, formats, repairs, dismounts or writes a source. Device enumeration uses Windows Storage cmdlets. If they are unavailable, image-file analysis still works.

Use `recoverx devices` to inspect OS-provided device properties. To image an explicitly authorized disk, choose its observed number, a destination on another physical disk, and run `recoverx image-device NUMBER E:\disk.img --consent`. Reconfirm disk identity before use. This release stops at the first unreadable range; it does not retry failing hardware aggressively.

For development, install `.[desktop,dev]`. Windows packaging uses `scripts/package-windows.ps1`. Inno Setup 6 is required for the installer step. Signing requires an organization-controlled certificate and timestamp service; no certificate or public download is supplied.

The web app requires Node 20.9+ and npm. Use `npm ci` in `apps/web`, then `npm run dev`. GitHub OAuth and PostgreSQL are optional and only needed for cloud summaries.
