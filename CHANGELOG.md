# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses Semantic Versioning for immutable release tags.

## [Unreleased]

### Added
- Thin-wrapper support for `tracecore verify` and `run-and-verify`
- Known-good TraceCore version pinning in the action contract
- Focused `pytest` coverage for wrapper command routing and error handling
- Stub and real-runtime CI coverage for verify flows
- Tag-driven GitHub release workflow for publishable action releases
- Automatic GitHub prerelease handling for hyphenated tags like `v1.0.0-rc.1`

### Changed
- Updated action and workflow dependencies to current GitHub Actions majors, including `actions/checkout@v5` and `actions/setup-python@v6`
- Updated README examples to point at the validated immutable `v1.0.1` release
- Modernized consumer validation workflows in the external `tracecore-test` repository to current GitHub Actions majors
- Refined README positioning around trust, externally validated workflow shapes, support policy, and copy-paste adoption paths

### Fixed
- Removed unsupported YAML anchors from the published action manifest so external consumers can resolve `action.yml` correctly
- Corrected published tag alignment so `@v1` points at the validated action revision
- Removed Python package cache usage in the action install path to avoid external consumer install failures
- Added badge rendering coverage and workflow assertions for success, failure, and verify outputs
- Fixed CI workflow fixture scripts and self-test agent behavior so source-repo validation passes reliably on `main`
- Validated external consumer scenarios for basic smoke, `run-and-verify`, and app-shaped GitHub App-style usage
