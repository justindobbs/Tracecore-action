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
