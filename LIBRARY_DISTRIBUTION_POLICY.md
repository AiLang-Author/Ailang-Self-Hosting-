AiLang Generic Library Distribution & Branding Policy
====================================================

Purpose
-------
AiLang publishes a set of generic/system libraries to encourage reuse, contribution,
and ecosystem growth while avoiding confusion about what is an "official" AiLang
library or release. This policy explains how modified libraries may be published
and how branding/naming must be handled to prevent accidental impersonation or
fragmentation.

Scope
-----
Applies to any library files that are NOT core compiler or core-language components
(i.e., supporting system libraries, utility libraries, std-like helpers) that were
originally published by AiLang or within the AiLang organization.

Policy summary (short)
----------------------
- Generic libraries are licensed permissively (MIT/BSD) to encourage reuse.
- If you publish a modified copy, you MUST rename it and include a clear
  prominent disclaimer that it is NOT the official AiLang library.
- Do NOT use AiLang trademarks, logos, or naming that implies endorsement
  without express written permission.
- Keep original copyright and license notices intact.
- Contributors must accept the project CLA or contributor grant so the project
  can relicense, rebrand or commercialize as needed downstream.

Required rules for publishing modified libraries
-----------------------------------------------
If you publish, distribute, or register a modified version of any AiLang generic
library, you MUST follow these rules:

1) Rename the library/package
   - Give it a distinct package name or vendor prefix (examples):
     - yourorg-<libname>
     - <libname>-fork
     - <libname>-community
   - Do NOT use the original package name or any confusingly similar name that
     would reasonably lead users to believe the package is the official AiLang release.

2) Add a clear, prominent disclaimer
   - The repository README, package metadata (package.json, setup.py, PyPI description, etc.),
     and release notes MUST include this exact statement or an equivalent that is equally prominent:
     "This is a modified/unofficial build and is NOT an official AiLang release. For the official
     library, see https://github.com/AiLang-Author/<official-repo>."
   - Example README banner:
     > WARNING: This is an unofficial fork of AiLang/<libname>. It is not endorsed or maintained by the official AiLang project. For the official library visit https://github.com/AiLang-Author/<official-repo>.

3) Do not use AiLang branding or logos
   - Do NOT use the project name "AiLang", the AiLang logo, or other brand assets in the package name,
     logo, or marketing materials in any way that implies official status or endorsement without written permission.

4) Preserve copyright and license
   - Preserve original copyright headers and include the library's LICENSE (MIT/BSD)
     file in the published package and repository.

5) Package metadata requirements
   - When publishing to package registries include the disclaimer in the package description.
   - Add a prominent note in the package README and on the package landing page that the package is unofficial.

6) When you must request an exception
   - If you need to publish under the original name (for compatibility reasons) you MUST request
     written permission in advance by contacting: Sean Collins — smc.collins1977@gmail.com.
   - Permission may be granted with conditions (vendor prefix, trademark license, or revenue share).

Contributor and relicense requirements
-------------------------------------
- Contributors to generic libraries should sign the project CLA (see CLA.md) or accept a contributor
  license grant in CONTRIBUTING.md. That grant allows the project to relicense or redistribute
  collected contributions (for example, to include them in commercial releases or under different
  terms later).
- By contributing code you represent you have the authority to license that code and that your
  contribution does not infringe third-party rights.

Enforcement and remedies
------------------------
- This is an express distribution policy of the AiLang project. The project reserves the right to:
  - Request removal of misleading packages that violate this policy.
  - Enforce naming, trademark, and distribution requirements through takedown requests to hosts and
    package registries, and by trademark or contract claims where applicable.
- If you receive a request from the AiLang project asking you to comply (rename, relabel, or take down),
  please cooperate or contact the maintainer to discuss an exception.

Trademark & branding
--------------------
- "AiLang" and the AiLang logo are trademarks of Sean Collins / 2 Paws Machine and Engineering.
- Use of the AiLang name, logo, or any variant that implies official endorsement requires express written permission.

Recommended good practices
--------------------------
- Prefer vendor prefixes for published binaries to avoid accidental collisions.
- Keep change logs and clear versioning to help users choose a release.
- Preserve and run the same test-suite so modifications are clearly validated.

Contact for permissions and commercial licenses
-----------------------------------------------
For exceptions, commercial licensing, or trademark requests contact:
Sean Collins — smc.collins1977@gmail.com

Agent checklist: relicensing and applying policy to library files
----------------------------------------------------------------
If you (or an automation agent) are going to relicense or apply this policy across many library directories, follow these steps:

1) Identify candidate directories
   - Find directories that contain library code (not core/compiler). Candidate heuristics:
     - repos or subdirs labeled "lib", "stdlib", "sys", "platform", "utils".
     - not containing core compiler sources (language, parser, codegen).

2) For each candidate directory:
   a) Confirm original license/attribution — record current LICENSE and any third-party notices.
   b) If dependency content is under incompatible third-party terms, skip or flag for manual review.
   c) Add/replace LICENSE file with chosen permissive license (recommended: MIT). Keep and merge any required third-party notices (e.g., zlib, BSD).
   d) Add SPDX identifiers to top-of-file headers where practical (e.g., // SPDX-License-Identifier: MIT).
   e) Add LIBRARY_DISTRIBUTION_POLICY.md (or link) to the repo root if not present.
   f) Add README note and package metadata disclaimer template (see "Package metadata requirements" above).

3) Commit & review
   - Create a branch named like: policy/relicense-<libname>
   - Commit changes with message: "Apply MIT license and Library Distribution Policy to <libname>"
   - Open a PR for maintainer review. Include a checklist of third-party components and any manual exceptions.

4) Post-merge actions
   - If publishing to registries, include the disclaimer and updated metadata.
   - Notify contributors about CLA/Contributor Grant expectations.

Notes & legal reality
---------------------
- This policy separates code license (MIT) from branding/trademark and distribution policy. A license with embedded renaming restrictions is non-standard and harms adoption — the policy + trademark + CLA approach balances openness and brand control.
- If you want stronger enforceability (license-level restrictions), consult counsel and expect reduced adoption.

Revision history
----------------
Version 1.0 — initial policy (Sean Collins, 2026)
