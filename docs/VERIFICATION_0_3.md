# RecoverX 0.3.0 verification — 2026-10-24 (Asia/Kolkata)

Validation for [PR #2](https://github.com/krishnacode120/RecoverX/pull/2) is in progress. This document will record the completed run and actual results before the PR is merged.

The upgrade adds native search/sort, persistent-history migration, bounded worker previews, NTFS parent-path validation and conservative Recycle Bin name pairing. CI adds real Windows file deletion on an isolated, disposable fixed VHD and silent installer lifecycle checks.

Development and tests remain on GitHub. The user's local checkout and installed application are unchanged. No user storage device is scanned by these tests. Signing, live deployment/auth/database configuration, physical hardware qualification, and the advanced capabilities listed in LIMITATIONS.md remain outstanding.
