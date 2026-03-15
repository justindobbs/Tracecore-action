# TraceCore GitHub Action
  
  Run TraceCore deterministic verification inside any GitHub workflow with a single step. This action is a thin wrapper around the published `tracecore` CLI: it installs a known-good TraceCore version, executes `tracecore run` and/or `tracecore verify`, optionally seals bundles, and emits a "TraceCore Verified" badge snippet for your README.

  ## Scope

  `tracecore-action` v1 intentionally stays thin:

  - it wraps authoritative TraceCore CLI flows
  - it supports `run`, `verify`, and `run-and-verify`
  - it targets known-good TraceCore versions first

  For runtime semantics, spec rules, and CLI behavior, treat the main TraceCore repo as authoritative.

  ## Quick start

  ```yaml
  name: tracecore-ci

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: justindobbs/tracecore-action@v1
        with:
          command: run-and-verify
          agent: ./agents/my_prod_agent.py
          task: filesystem_hidden_config@1
          strict-spec: true
          replay-bundle: .agent_bench/baselines/filesystem_hidden_config@1
          strict: true
  ```

  Verify an existing run or bundle directly:

  ```yaml
  - uses: actions/checkout@v4
  - uses: justindobbs/tracecore-action@v1
    with:
      command: verify
      verify-run: run_1234567890
      strict-spec: true
  ```

  Add a matrix to cover multiple agents/tasks:

  ```yaml
  strategy:
  fail-fast: false
  matrix:
    agent: [./agents/a.py, ./agents/b.py]
    task: [filesystem_hidden_config@1, log_alert_triage@1]

  steps:
    - uses: actions/checkout@v4
    - uses: justindobbs/tracecore-action@v1
      with:
        command: run-and-verify
        agent: ${{ matrix.agent }}
        task: ${{ matrix.task }}
        strict-spec: true
  ```

  Consume verification outputs in later steps:

  ```yaml
  - uses: actions/checkout@v4
  - id: tracecore
    uses: justindobbs/tracecore-action@v1
    with:
      command: run-and-verify
      agent: ./agents/my_prod_agent.py
      task: filesystem_hidden_config@1

  - name: Show verify report
    run: |
      echo 'verify_ok=${{ steps.tracecore.outputs.verify-ok }}'
      echo '${{ steps.tracecore.outputs.verify-report }}'
  ```

  ## Inputs

  | Name | Required | Default | Description |
  | --- | --- | --- | --- |
  | `command` |  | `run` | TraceCore flow to execute: `run`, `verify`, or `run-and-verify`. |
  | `agent` | for `run` / `run-and-verify` | — | Path to the agent file/module to run. |
  | `task` | for `run` / `run-and-verify` | — | Task reference (`id@version`). |
  | `seed` |  | `0` | Deterministic seed passed to TraceCore. |
  | `timeout` |  | `300` | Wall-clock timeout (seconds). |
  | `strict-spec` |  | `true` | Enforce TraceCore strict spec compliance. |
  | `replay-bundle` |  | `""` | Path to a sealed baseline bundle used for replay gating. |
  | `strict` |  | `false` | Enable strict replay checks; for `run` and `run-and-verify` this requires `replay-bundle`. |
  | `verify-run` |  | `""` | Run artifact path or run_id to verify. |
  | `verify-bundle` |  | `""` | Bundle directory to verify against. |
  | `verify-latest` |  | `true` | When verifying, target the latest run if no explicit run/bundle is supplied. |
  | `prefer-success` |  | `true` | When using latest resolution, prefer the latest successful run. |
  | `seal-baseline` |  | `false` | Seal the run as a new bundle when it succeeds. |
  | `tracecore-version` |  | `1.1.2` | Known-good TraceCore version to `pip install`. |
  | `generate-badge` |  | `true` | Emit a shields.io badge snippet tied to the run result. |
  | `badge-output` |  | `.tracecore-badge.md` | File that receives the badge markdown. |

  ## Outputs

  | Name | Description |
  | --- | --- |
  | `success` | `true` when the run passed and met gating criteria. |
  | `run-id` | TraceCore `run_id` for the execution. |
  | `artifact-hash` | SHA-256 hash embedded in the artifact. |
  | `steps-used` | Steps consumed. |
  | `tool-calls-used` | Tool calls consumed. |
  | `bundle-path` | Path to the sealed bundle (when `seal-baseline` is enabled). |
  | `verify-ok` | `true` when the verify stage passed, empty when no verify stage was executed. |
  | `verify-report` | JSON report emitted by `tracecore verify`, empty when no verify stage was executed. |
  | `badge-markdown` | Shield snippet pointing to TraceCore. |

  ## Version policy

  This action currently targets known-good TraceCore releases rather than `latest` by default. Widen compatibility only after adding stronger cross-version CI coverage.

  ## Releases and tags

  Release tags should follow `vMAJOR.MINOR.PATCH`.

  Small pre-releases can use `vMAJOR.MINOR.PATCH-rc.N`.

  - consumers who want immutable behavior should pin a full release tag
  - `@v1` should be maintained as a floating major tag that points to the latest vetted `v1.x.y` release
  - update `CHANGELOG.md`, README examples, and the action contract before cutting a release tag
  - verify CI is green before moving the floating major tag
  - prerelease tags should publish as GitHub prereleases and should not move the floating major tag until vetted

  Example consumption:

  - stable major channel: `justindobbs/tracecore-action@v1`
  - immutable release: `justindobbs/tracecore-action@v1.0.1`
  - prerelease candidate: `justindobbs/tracecore-action@v1.0.0-rc.1`

  ## Pre-release checklist

  Before cutting the first public tag:

  - run the focused local tests
  - confirm README examples still match `action.yml`
  - confirm the known-good `tracecore-version` default is the one you intend to support
  - review `CHANGELOG.md` for the release summary
  - cut a prerelease tag first if you want one final GitHub-hosted validation pass before `v1.0.0`

  ## GitHub App and permissions

  This action is suitable for GitHub App-driven workflows because it does not require special GitHub API permissions by itself.

  - the action runs locally in the job and shells out to the `tracecore` CLI
  - the action itself does not need repository write access
  - if later workflow steps post comments, upload artifacts, or update checks, grant only the additional permissions those steps require

  ## Self-hosted runners

  The action targets `ubuntu-latest` by default but works on any runner that can:

  1. Provide Python 3.12 + `pip`.
  2. Install `tracecore` from PyPI.
  3. Persist `.agent_bench/` artifacts between steps when using verify or bundle flows that rely on prior run state.

  Ensure the runner user has permission to write to the workspace and outbound network access to PyPI.

  ## License

  MIT © 2026 Justin Dobbs.
