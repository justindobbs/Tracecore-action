# TraceCore GitHub Action
  
  Run deterministic TraceCore validation in GitHub Actions with a stable, copy-paste wrapper around the published `tracecore` CLI. `tracecore-action` installs a known-good TraceCore version, executes `tracecore run` and/or `tracecore verify`, optionally seals bundles, and emits a "TraceCore Verified" badge snippet for downstream docs or status surfaces.

  `tracecore-action` is designed for teams who want a GitHub-native entry point into TraceCore without rebuilding install, invocation, output parsing, and verification wiring in every workflow.

  ## Why use the action?

  - standardizes TraceCore install + invocation in CI
  - exposes stable workflow outputs for downstream steps
  - keeps versioning explicit through a known-good TraceCore default
  - supports both direct verification and run-then-verify flows
  - has been validated externally against the published `@v1` action contract

  ## Validated workflow shapes

  The current action contract has been validated in a separate consumer repo for three common workflow shapes:

  - basic smoke usage against the published action
  - combined `run-and-verify` wrapper usage
  - app-shaped downstream usage where later steps consume action outputs

  For external consumer-validation fixtures and rendered badge examples, see [`tracecore-test`](https://github.com/justindobbs/tracecore-action-test).

  ## Scope

  `tracecore-action` v1 intentionally stays thin:

  - it wraps authoritative TraceCore CLI flows
  - it supports `run`, `verify`, and `run-and-verify`
  - it targets known-good TraceCore versions first

  For runtime semantics, spec rules, and CLI behavior, treat the main TraceCore repo as authoritative.

  ## When to use this action vs direct CLI

  Use `tracecore-action` when you want:

  - a reusable GitHub Actions step with stable outputs
  - a documented `@v1` integration surface for downstream workflows
  - a simpler path for teams standardizing TraceCore usage across repos

  Call `tracecore` directly in workflow scripts when you want:

  - highly custom shell orchestration
  - experimental runtime flags not yet surfaced here
  - a workflow that is already deeply CLI-native and does not benefit from action outputs

  ## Quick start

  Recommended first path:

  ```yaml
  name: tracecore-ci

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: justindobbs/tracecore-action@v1
        with:
          command: run-and-verify
          agent: ./agents/my_prod_agent.py
          task: filesystem_hidden_config@1
          strict-spec: true
  ```

  This is the best default if you want one step that both executes and verifies a TraceCore run.

  Verify an existing run or bundle directly:

  ```yaml
  - uses: actions/checkout@v5
  - uses: justindobbs/tracecore-action@v1
    with:
      command: verify
      verify-run: run_1234567890
      strict-spec: true
  ```

  GitHub App-shaped downstream usage:

  ```yaml
  - uses: actions/checkout@v5
  - id: tracecore
    uses: justindobbs/tracecore-action@v1
    with:
      command: run-and-verify
      agent: ./agents/app_agent.py
      task: filesystem_hidden_config@1
      strict-spec: true

  - name: Build downstream summary
    run: |
      cat <<EOF > tracecore-summary.json
      {
        "success": "${{ steps.tracecore.outputs.success }}",
        "run_id": "${{ steps.tracecore.outputs.run-id }}",
        "verify_ok": "${{ steps.tracecore.outputs.verify-ok }}"
      }
      EOF
  ```

  Add a matrix to cover multiple agents/tasks:

  ```yaml
  strategy:
  fail-fast: false
  matrix:
    agent: [./agents/a.py, ./agents/b.py]
    task: [filesystem_hidden_config@1, log_alert_triage@1]

  steps:
    - uses: actions/checkout@v5
    - uses: justindobbs/tracecore-action@v1
      with:
        command: run-and-verify
        agent: ${{ matrix.agent }}
        task: ${{ matrix.task }}
        strict-spec: true
  ```

  Consume verification outputs in later steps:

  ```yaml
  - uses: actions/checkout@v5
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

  Strict replay / bundle-gated usage:

  ```yaml
  - uses: actions/checkout@v5
  - uses: justindobbs/tracecore-action@v1
    with:
      command: run-and-verify
      agent: ./agents/my_prod_agent.py
      task: filesystem_hidden_config@1
      strict-spec: true
      replay-bundle: .agent_bench/baselines/filesystem_hidden_config@1
      strict: true
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

  ## Support contract

  `tracecore-action` v1 is intentionally narrow and supportable:

  - the action is a thin wrapper over authoritative TraceCore CLI flows
  - `@v1` is the stable major channel for vetted updates
  - immutable tags such as `@v1.0.1` are the safest choice when you need exact reproducibility
  - the default `tracecore-version` represents a known-good release that has been validated with this wrapper
  - new action features should follow existing TraceCore runtime behavior rather than inventing action-only semantics

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

  ## Trust signals

  Before this action was positioned for broader public use, it was validated across:

  - source-repo CI in `tracecore-action`
  - external consumer-validation flows in `tracecore-test`
  - published `@v1` usage from a separate repo
  - badge generation and downstream-output consumption paths

  If you are evaluating whether to adopt the action, the recommended proof points are:

  - pin `@v1` for a vetted major channel
  - inspect immutable release tags for exact reproducibility
  - review `CHANGELOG.md` for release-facing changes
  - review `tracecore-test` for external-consumer examples and validation shape

  ## License

  MIT © 2026 Justin Dobbs.
