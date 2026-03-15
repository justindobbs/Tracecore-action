from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from badge import render_badge


class ActionError(RuntimeError):
    """Raised when the GitHub Action needs to fail early."""


def _env(key: str, *, required: bool = False, default: str | None = None) -> str:
    try:
        value = os.environ[key]
    except KeyError:
        if required:
            raise ActionError(f"Missing required environment variable: {key}")
        if default is None:
            raise ActionError(f"Environment variable {key} is not set and no default provided")
        return default
    return value


def _env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _run_subprocess(cmd: list[str], *, capture_json: bool = False) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Command failed ({proc.returncode}): {' '.join(shlex.quote(c) for c in cmd)}", file=sys.stderr)
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        raise ActionError(f"Command failed with exit code {proc.returncode}")
    if capture_json and not proc.stdout.strip():
        raise ActionError(f"Command produced no JSON output: {' '.join(cmd)}")
    return proc.returncode, proc.stdout, proc.stderr


def _parse_json(payload: str) -> dict[str, Any]:
    try:
        return json.loads(payload.strip())
    except json.JSONDecodeError as exc:
        raise ActionError(f"Failed to parse JSON output: {exc}\nPayload was:\n{payload}") from exc


def _append_output(name: str, value: Any) -> None:
    target = os.environ.get("GITHUB_OUTPUT")
    serialized = "" if value is None else str(value)
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={serialized}\n")
    else:
        print(f"::set-output name={name}::{serialized}")


def _ensure_parent(path: Path) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def _build_run_cmd(
    *,
    agent: str,
    task: str,
    seed: str,
    timeout: str,
    strict_spec: bool,
    replay_bundle: str | None,
    strict: bool,
) -> list[str]:
    cmd = ["tracecore", "run", "--agent", agent, "--task", task, "--seed", seed]
    if timeout:
        cmd += ["--timeout", timeout]
    if strict_spec:
        cmd.append("--strict-spec")
    if replay_bundle:
        cmd += ["--replay-bundle", replay_bundle]
    if strict:
        cmd.append("--strict")
    return cmd


def _build_verify_cmd(
    *,
    run_ref: str | None,
    bundle_ref: str | None,
    verify_latest: bool,
    prefer_success: bool,
    strict_spec: bool,
    strict: bool,
) -> list[str]:
    cmd = ["tracecore", "verify", "--json"]
    if run_ref:
        cmd += ["--run", run_ref]
    if bundle_ref:
        cmd += ["--bundle", bundle_ref]
    if not run_ref and not bundle_ref and verify_latest:
        cmd.append("--latest")
    if prefer_success:
        cmd.append("--prefer-success")
    if strict_spec:
        cmd.append("--strict-spec")
    if strict:
        cmd.append("--strict")
    return cmd


def _seal_bundle(run_id: str) -> str:
    cmd = ["tracecore", "bundle", "seal", "--format", "json", "--run", run_id]
    _, stdout, _ = _run_subprocess(cmd, capture_json=True)
    report = _parse_json(stdout)
    ok = report.get("ok", True)
    if not ok:
        raise ActionError(f"bundle seal failed: {json.dumps(report, indent=2)}")
    bundle_dir = report.get("bundle_dir")
    if not bundle_dir:
        raise ActionError("bundle seal did not return bundle_dir")
    return bundle_dir


def _run_verify(
    *,
    run_ref: str | None,
    bundle_ref: str | None,
    verify_latest: bool,
    prefer_success: bool,
    strict_spec: bool,
    strict: bool,
) -> dict[str, Any]:
    verify_cmd = _build_verify_cmd(
        run_ref=run_ref,
        bundle_ref=bundle_ref,
        verify_latest=verify_latest,
        prefer_success=prefer_success,
        strict_spec=strict_spec,
        strict=strict,
    )
    print(f"Running TraceCore verify: {' '.join(shlex.quote(arg) for arg in verify_cmd)}", file=sys.stderr)
    _, stdout, stderr = _run_subprocess(verify_cmd, capture_json=True)
    if stderr:
        print(stderr, file=sys.stderr)
    return _parse_json(stdout)


def main() -> int:
    command = _env("INPUT_COMMAND", default="run").strip().lower()
    agent = os.environ.get("INPUT_AGENT", "")
    task = os.environ.get("INPUT_TASK", "")
    seed = _env("INPUT_SEED", default="0")
    timeout = _env("INPUT_TIMEOUT", default="")
    strict_spec = _env_bool("INPUT_STRICT_SPEC", True)
    replay_bundle = os.environ.get("INPUT_REPLAY_BUNDLE") or ""
    strict = _env_bool("INPUT_STRICT", False)
    verify_run = os.environ.get("INPUT_VERIFY_RUN") or ""
    verify_bundle = os.environ.get("INPUT_VERIFY_BUNDLE") or ""
    verify_latest = _env_bool("INPUT_VERIFY_LATEST", True)
    prefer_success = _env_bool("INPUT_PREFER_SUCCESS", True)
    seal_baseline = _env_bool("INPUT_SEAL_BASELINE", False)
    generate_badge = _env_bool("INPUT_GENERATE_BADGE", True)
    badge_output = os.environ.get("INPUT_BADGE_OUTPUT", ".tracecore-badge.md")

    if command not in {"run", "verify", "run-and-verify"}:
        raise ActionError(f"Unsupported command {command!r}; expected run, verify, or run-and-verify")

    if strict and command in {"run", "run-and-verify"} and not replay_bundle:
        raise ActionError("--strict requested without --replay-bundle path")

    if command in {"run", "run-and-verify"}:
        if not agent:
            raise ActionError("agent is required for run and run-and-verify commands")
        if not task:
            raise ActionError("task is required for run and run-and-verify commands")

    run_result: dict[str, Any] | None = None
    verify_report: dict[str, Any] | None = None

    run_id = ""
    artifact_hash = ""
    steps_used: Any = ""
    tool_calls_used: Any = ""
    success = True

    if command in {"run", "run-and-verify"}:
        run_cmd = _build_run_cmd(
            agent=agent,
            task=task,
            seed=seed,
            timeout=timeout,
            strict_spec=strict_spec,
            replay_bundle=replay_bundle if replay_bundle else None,
            strict=strict,
        )

        print(f"Running TraceCore: {' '.join(shlex.quote(arg) for arg in run_cmd)}", file=sys.stderr)
        _, stdout, stderr = _run_subprocess(run_cmd, capture_json=True)
        if stderr:
            print(stderr, file=sys.stderr)
        run_result = _parse_json(stdout)

        run_id = run_result.get("run_id") or ""
        artifact_hash = run_result.get("artifact_hash", "")
        steps_used = run_result.get("steps_used")
        tool_calls_used = run_result.get("tool_calls_used")
        success = bool(run_result.get("success")) and run_result.get("failure_type") is None

    bundle_path = ""
    if seal_baseline:
        if not run_id:
            raise ActionError("Cannot seal baseline: run_id missing from TraceCore result")
        if not success:
            raise ActionError("Cannot seal baseline from a failed run")
        bundle_path = _seal_bundle(run_id)
        print(f"Sealed bundle: {bundle_path}", file=sys.stderr)

    if command in {"verify", "run-and-verify"}:
        verify_run_ref = verify_run or (run_id if run_id else None)
        verify_bundle_ref = verify_bundle or (bundle_path if bundle_path else None)
        verify_report = _run_verify(
            run_ref=verify_run_ref,
            bundle_ref=verify_bundle_ref,
            verify_latest=verify_latest,
            prefer_success=prefer_success,
            strict_spec=strict_spec,
            strict=strict,
        )
        success = success and bool(verify_report.get("ok"))

    badge_markdown = ""
    if generate_badge:
        badge = render_badge(success, strict_spec=strict_spec)
        badge_markdown = badge.markdown
        target_path = Path(badge_output)
        _ensure_parent(target_path)
        target_path.write_text(badge_markdown + "\n", encoding="utf-8")
        print(f"Badge written to {target_path}", file=sys.stderr)

    _append_output("success", str(success).lower())
    _append_output("run-id", run_id)
    _append_output("artifact-hash", artifact_hash)
    _append_output("steps-used", steps_used if steps_used is not None else "")
    _append_output("tool-calls-used", tool_calls_used if tool_calls_used is not None else "")
    _append_output("bundle-path", bundle_path)
    _append_output("verify-ok", "" if verify_report is None else str(bool(verify_report.get("ok"))).lower())
    _append_output("verify-report", "" if verify_report is None else json.dumps(verify_report, separators=(",", ":")))
    _append_output("badge-markdown", badge_markdown)

    if run_result is not None and not (bool(run_result.get("success")) and run_result.get("failure_type") is None):
        failure_type = run_result.get("failure_type") or "unknown"
        reason = run_result.get("failure_reason") or "TraceCore run failed"
        raise ActionError(f"TraceCore run failed ({failure_type}): {reason}")

    if verify_report is not None and not verify_report.get("ok"):
        raise ActionError(f"TraceCore verify failed: {json.dumps(verify_report, indent=2)}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ActionError as exc:
        print(f"::error::{exc}")
        raise SystemExit(1)
