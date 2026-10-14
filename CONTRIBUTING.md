# Contributing to Ailang-Self-Hosting-

Thank you for your interest in improving Ailang-Self-Hosting-.

This project is licensed under the Sean Collins Software License (SCSL v1.0). The project is intentionally designed to discourage public forks, incompatible derivative versions, and unmanaged variation. We prefer changes to be submitted upstream for review and integration rather than released as competing forks.

By contributing, you agree to the project’s license and contribution model.

## Contribution model

We are not accepting public forks as a normal development workflow.

The preferred model is:

- keep work in a local branch or private fork for development
- submit a pull request to the upstream repository
- allow maintainers to review and decide whether the change is accepted
- do not publish or distribute alternate versions of the project without written permission

If you want to use the project commercially, please contact the maintainer directly for a paid license rather than creating a separate public distribution.

## What kind of contributions are welcome

We welcome:

- bug fixes
- compiler/runtime correctness fixes
- test coverage
- documentation improvements
- performance tuning
- compatibility fixes
- build and portability improvements

We especially value changes that:

- preserve the project’s design goals and compatibility model
- improve correctness and stability
- reduce fragmentation or incompatible forks
- maintain a clear upstream path for review and integration

## Before you start

For large or architectural changes, please first open an issue or contact the maintainer to discuss the change. This helps ensure the work fits the project direction and avoids duplicated or conflicting work.

Major changes should include:

- motivation and problem statement
- proposed design or approach
- impact on compatibility, performance, or compiler behavior
- migration or compatibility notes if relevant

## Pull request expectations

When submitting a pull request:

- target the upstream repository default branch
- keep the scope narrow and reviewable
- explain why the change is needed
- include tests where practical
- describe any compatibility implications
- ensure the patch is consistent with the project’s goals and code style

Do not submit PRs that are intended to create a public alternate distribution, a competing fork, or a rebranded version of the project.

## Coding standards

Please keep patches:

- focused and readable
- consistent with the surrounding codebase
- well tested where feasible
- conservative when changing semantics or ABI boundaries

Performance-sensitive changes should include benchmark or validation notes where appropriate.

## Documentation

If your change modifies behavior, interfaces, or expected usage, update the relevant documentation in the repository as part of the same change.

## Reporting issues

Use issues for:

- bugs
- design discussions
- requests for clarification
- possible improvements

Please provide:

- reproduction steps
- expected result
- actual result
- environment details
- minimal examples when possible

## Security

If you discover a security issue or a concern that could affect users in a serious way, do not open a public issue first. Please contact the maintainer privately and allow time for a responsible fix.

## Commercial use and licensing

Commercial use is not permitted without a written commercial license.

If your organization wants to use the project in a business, production, or commercial context, contact:

Sean Collins
smc.collins1977@gmail.com

Reasonable paid licensing terms are available for commercial use.

## Maintainer rights

The maintainer reserves the right to:

- accept or reject any contribution
- request changes before acceptance
- decline changes that would fragment the project ecosystem or create incompatible variants
- require additional review for large or sensitive changes

## Final note

The goal of this project is to keep a coherent, reviewable upstream codebase rather than allow endless incompatible variants. We value thoughtful, well-scoped changes that improve the project without creating parallel distributions.

Thank you for helping keep Ailang coherent, stable, and maintainable.
