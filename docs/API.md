# APIs

## Web

- `GET /api/health`: public version/health and explicit `diskAccess: false`, `uploads: false`.
- `/api/auth/*`: Auth.js GitHub sign-in/sign-out and session handlers when configured.
- `GET /api/reports`: signed-in user's latest 100 aggregate summaries. No-store response.
- `POST /api/reports`: authenticated, same-origin JSON, maximum 8 KiB. Zod strict schema rejects extra fields such as filenames. Saves aggregate scan counts and timing.
- `DELETE /api/reports`: authenticated, same-origin JSON `{id}` or `{all:true}`. Owner filtering is mandatory; all deletes the user's metadata row and cascading summaries.

No public raw disk, arbitrary path, upload, command execution, or native scanning endpoint exists. Error responses omit server paths and database secrets.

## Optional native report bridge

Launch explicitly: `python -m recoverx.agent history.sqlite SCAN_ID --origin https://your-approved-host --consent`. The terminal shows a random pairing token and selected loopback port. Do not paste tokens into logs. Close with Ctrl+C; expiration is ten minutes. Bind address is always 127.0.0.1. Every request requires an exact Host and approved Origin. GET requires the bearer token. Preflight exposes no data.

- `GET /health`: authenticated scope/lifetime.
- `GET /api/v1/scans/{selectedScanId}/results?offset=0`: 100 candidates at a time. No original paths.

All scan/recovery mutations are deliberately absent from the bridge. The default website uses report import and has no connect button; HTTPS-page to HTTP-loopback policies are browser-dependent and have not been qualified. No unauthenticated disk API exists.
