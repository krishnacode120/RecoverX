# Security model and release gates

Sources are opened read-only. Windows raw handles use GENERIC_READ and share flags; no write, format, repair, lock/dismount, or elevation APIs are called. The ordinary desktop requires authorization for scans, and a separate per-device authorization for imaging.

Destination mapping uses Windows volume disk extents, so separate drive letters on one physical disk are blocked. Unresolvable relationships fail closed. Explicit same-disk allowance applies only to image-file exports. Database/output source-path collisions are rejected by the CLI. Recovery names cannot escape the selected output folder. No overwrite or remote path API is provided.

Untrusted structures are bounded. Format validation can still involve third-party native parsers in-process. **Parser sandboxing and independent security review remain production release gates.** Previews only decode small images and show metadata; documents/macros/scripts/binaries are not executed. ZIPs are read for validation, never unpacked into the filesystem.

Cloud sign-in is optional. The web account endpoints check a signed session and ownership on every query, same-origin mutation checks, body limits, and strict schemas. No filenames, original paths or contents are sent by summary operations. Reports remain in memory unless the user explicitly exports them. The deployment must use HTTPS. CSP denies framing/objects; Next inline scripts require the current unsafe-inline allowance, with a nonce-based CSP a future hardening item.

The loopback report bridge uses a 256-bit random bearer token, 10-minute lifetime, exact Host/Origin allowlists, no cookies, no mutation endpoints and no path parameters. It is off by default. Transport is HTTP on loopback only; it is not a public API or a qualified cross-browser integration.

Known production gates: raw device safety qualification on disposable hardware, parser isolation, fuzzing, resource limits under hostile input, cloud integration tests against a real account/database, signed builds and installer review, dependency/license review, accessibility verification, release provenance, and retention policies for any future uploads. There is no claim that these gates have already passed.
