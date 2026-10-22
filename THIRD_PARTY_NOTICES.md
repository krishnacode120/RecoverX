# Third-party dependency review

This source uses the licenses of its dependencies; retain their notices in redistributed builds. Before a public release, produce a complete versioned SBOM from the installed environment/lockfile and have distribution obligations reviewed.

- Python: PSF license. Pillow: HPND-style license; bundled codec notices also apply.
- Qt / PySide6 / shiboken6: LGPLv3/GPLv3 or commercial terms as applicable. This application uses Essentials dynamically. Redistribution must preserve notices and applicable relinking/replacement rights; do not assume a frozen app automatically satisfies LGPL obligations.
- PyInstaller: GPL exception permits bundling applications; preserve bootloader notices.
- pybind11: BSD-style license; C++ runtime obligations depend on the build toolchain.
- Next.js, React, Tailwind, Zustand, TanStack Query, Zod, Motion, Recharts, Drizzle, Auth.js and Radix packages: inspect exact installed package license metadata and transitive notices. Most direct packages use permissive licenses; do not infer licenses of all bundled assets from that statement.
- Lucide: ISC license.
- The Sleuth Kit: mixed source-file licenses (IBM Public License/Common Public License and other components); not bundled or enabled in this release. Optional pytsk3 packaging/architecture requires separate qualification.
- libewf: not bundled; licensing and native dependencies require review before enabling EWF support.

Authoritative TSK source: https://www.sleuthkit.org/sleuthkit/licenses.php

This file is a review checklist and disclosure, not a completed legal certification. Source ownership/license for RecoverX itself must be selected by its owner before public distribution.
