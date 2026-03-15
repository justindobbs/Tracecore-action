from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main
from main import ActionError


@pytest.fixture(autouse=True)
def clear_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key in list(os.environ):
        if key.startswith("INPUT_") or key == "GITHUB_OUTPUT":
            monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)


def _read_outputs(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        payload[key] = value
    return payload


def test_build_verify_cmd_defaults_to_latest() -> None:
    cmd = main._build_verify_cmd(
        run_ref=None,
        bundle_ref=None,
        verify_latest=True,
        prefer_success=True,
        strict_spec=True,
        strict=False,
    )

    assert cmd == [
        "tracecore",
        "verify",
        "--json",
        "--latest",
        "--prefer-success",
        "--strict-spec",
    ]


def test_build_verify_cmd_uses_explicit_targets() -> None:
    cmd = main._build_verify_cmd(
        run_ref="run-123",
        bundle_ref=".agent_bench/baselines/run-123",
        verify_latest=False,
        prefer_success=False,
        strict_spec=False,
        strict=True,
    )

    assert cmd == [
        "tracecore",
        "verify",
        "--json",
        "--run",
        "run-123",
        "--bundle",
        ".agent_bench/baselines/run-123",
        "--strict",
    ]


def test_build_verify_cmd_does_not_mix_explicit_run_with_latest() -> None:
    cmd = main._build_verify_cmd(
        run_ref="run-123",
        bundle_ref=None,
        verify_latest=True,
        prefer_success=True,
        strict_spec=True,
        strict=False,
    )

    assert cmd == [
        "tracecore",
        "verify",
        "--json",
        "--run",
        "run-123",
        "--prefer-success",
        "--strict-spec",
    ]


def test_main_verify_only_emits_verify_outputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_path = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("INPUT_COMMAND", "verify")
    monkeypatch.setenv("INPUT_STRICT_SPEC", "true")

    calls: list[list[str]] = []

    def fake_run_subprocess(cmd: list[str], *, capture_json: bool = False):
        calls.append(cmd)
        payload = {
            "ok": True,
            "run": "run-verify-1",
            "bundle_dir": None,
            "checks": {"strict_spec": {"ok": True, "errors": [], "mode": "strict-spec"}},
            "errors": [],
        }
        return 0, json.dumps(payload), ""

    monkeypatch.setattr(main, "_run_subprocess", fake_run_subprocess)

    assert main.main() == 0

    assert calls == [["tracecore", "verify", "--json", "--latest", "--prefer-success", "--strict-spec"]]
    outputs = _read_outputs(output_path)
    assert outputs["success"] == "true"
    assert outputs["run-id"] == ""
    assert outputs["verify-ok"] == "true"
    assert json.loads(outputs["verify-report"])["run"] == "run-verify-1"


def test_main_run_and_verify_emits_run_and_verify_outputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_path = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("INPUT_COMMAND", "run-and-verify")
    monkeypatch.setenv("INPUT_AGENT", "agents/toy_agent.py")
    monkeypatch.setenv("INPUT_TASK", "filesystem_hidden_config@1")
    monkeypatch.setenv("INPUT_STRICT_SPEC", "true")

    calls: list[list[str]] = []

    def fake_run_subprocess(cmd: list[str], *, capture_json: bool = False):
        calls.append(cmd)
        if cmd[:2] == ["tracecore", "run"]:
            payload = {
                "run_id": "run-123",
                "artifact_hash": "sha256:abc",
                "success": True,
                "failure_type": None,
                "steps_used": 4,
                "tool_calls_used": 2,
            }
            return 0, json.dumps(payload), ""
        payload = {
            "ok": True,
            "run": "run-123",
            "bundle_dir": None,
            "checks": {"strict_spec": {"ok": True, "errors": [], "mode": "strict-spec"}},
            "errors": [],
        }
        return 0, json.dumps(payload), ""

    monkeypatch.setattr(main, "_run_subprocess", fake_run_subprocess)

    assert main.main() == 0

    assert calls[0][:2] == ["tracecore", "run"]
    assert calls[1] == [
        "tracecore",
        "verify",
        "--json",
        "--run",
        "run-123",
        "--prefer-success",
        "--strict-spec",
    ]
    outputs = _read_outputs(output_path)
    assert outputs["success"] == "true"
    assert outputs["run-id"] == "run-123"
    assert outputs["artifact-hash"] == "sha256:abc"
    assert outputs["steps-used"] == "4"
    assert outputs["tool-calls-used"] == "2"
    assert outputs["verify-ok"] == "true"


def test_main_run_requires_agent_and_task_for_run_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INPUT_COMMAND", "run")

    with pytest.raises(ActionError, match="agent is required"):
        main.main()


def test_main_strict_run_requires_replay_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INPUT_COMMAND", "run")
    monkeypatch.setenv("INPUT_AGENT", "agents/toy_agent.py")
    monkeypatch.setenv("INPUT_TASK", "filesystem_hidden_config@1")
    monkeypatch.setenv("INPUT_STRICT", "true")

    with pytest.raises(ActionError, match="--strict requested without --replay-bundle path"):
        main.main()


def test_main_strict_run_and_verify_requires_replay_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INPUT_COMMAND", "run-and-verify")
    monkeypatch.setenv("INPUT_AGENT", "agents/toy_agent.py")
    monkeypatch.setenv("INPUT_TASK", "filesystem_hidden_config@1")
    monkeypatch.setenv("INPUT_STRICT", "true")

    with pytest.raises(ActionError, match="--strict requested without --replay-bundle path"):
        main.main()


def test_main_verify_failure_raises_action_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    output_path = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_path))
    monkeypatch.setenv("INPUT_COMMAND", "verify")

    def fake_run_subprocess(cmd: list[str], *, capture_json: bool = False):
        payload = {
            "ok": False,
            "run": "run-verify-1",
            "bundle_dir": None,
            "checks": {},
            "errors": ["no prior runs found to verify"],
        }
        return 0, json.dumps(payload), ""

    monkeypatch.setattr(main, "_run_subprocess", fake_run_subprocess)

    with pytest.raises(ActionError, match="TraceCore verify failed"):
        main.main()

    outputs = _read_outputs(output_path)
    assert outputs["success"] == "false"
    assert outputs["verify-ok"] == "false"
