"""Acceptance tests for contract pub-backport-2: the quality gate entry.

Quality metrics become their own opt-in gate: an exit-code-gated CHECKS
entry that inherits the generic machinery untouched (no --min, strict
staleness, snapshot guard, --require). The tests drive the real CLI in
scratch repositories through the shared fixtures.
"""

import sys
from pathlib import Path

from conftest import freeze_cycle, read_state

BIN_DIR = str(Path(__file__).resolve().parents[1] / "bin")
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

import red_proof  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


# --- AC1: the registry entry ------------------------------------------------

def test_quality_registry_shape():
    spec = red_proof.CHECKS["quality"]
    assert spec == {"evidence_key": "quality", "staleness": "strict",
                    "extract": None, "extract_from": "output"}
    assert "quality" in red_proof.check_names()
    assert "quality" not in red_proof.min_check_names()


# --- AC2: the pass path -----------------------------------------------------

def test_quality_pass_records_evidence(rp, claude_home, git_repo):
    repo = freeze_cycle(rp, claude_home, git_repo())
    r = rp(["check", "quality", "--", sys.executable, "-c", "print('ok')"],
           env=claude_home, cwd=repo)
    assert r.returncode == 0, r.stdout + r.stderr
    state = read_state(claude_home, repo)
    assert state["evidence"]["quality"]["passed"] is True


# --- AC3: the fail path arms the snapshot guard -----------------------------

def test_quality_failure_counts_and_guards(rp, claude_home, git_repo):
    repo = freeze_cycle(rp, claude_home, git_repo())
    fail_cmd = [sys.executable, "-c", "raise SystemExit(1)"]
    r = rp(["check", "quality", "--", *fail_cmd], env=claude_home, cwd=repo)
    assert r.returncode != 0
    again = rp(["check", "quality", "--", *fail_cmd],
               env=claude_home, cwd=repo)
    assert again.returncode != 0
    out = (again.stdout + again.stderr).lower()
    assert "unchanged" in out or "attempt" in out


# --- AC4: --min is refused before anything runs -----------------------------

def test_quality_refuses_min(rp, claude_home, git_repo):
    repo = freeze_cycle(rp, claude_home, git_repo())
    r = rp(["check", "quality", "--min", "5", "--",
            sys.executable, "-c", "print('never')"],
           env=claude_home, cwd=repo)
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "no metric" in out
    assert "never" not in out


# --- AC5: quality is requirable and gates the commit ------------------------

def test_required_quality_blocks_the_gate_until_green(rp, claude_home,
                                                      git_repo):
    repo = freeze_cycle(rp, claude_home, git_repo(),
                        contract_args=("--require", "quality"))
    state = read_state(claude_home, repo)
    assert "quality" in state["required_evidence"]
    ok = [sys.executable, "-c", "print('ok')"]
    for name in ("targeted", "full-suite"):
        r = rp(["check", name, "--", *ok], env=claude_home, cwd=repo)
        assert r.returncode == 0, r.stdout + r.stderr
    r = rp(["attest", "--diff-reviewed", "--contract-ok"],
           env=claude_home, cwd=repo)
    assert r.returncode == 0
    blocked = rp(["commit-gate"], env=claude_home, cwd=repo)
    assert blocked.returncode != 0
    assert "quality" in (blocked.stdout + blocked.stderr)
    r = rp(["check", "quality", "--", *ok], env=claude_home, cwd=repo)
    assert r.returncode == 0
    passed = rp(["commit-gate"], env=claude_home, cwd=repo)
    assert passed.returncode == 0, passed.stdout + passed.stderr


# --- AC6: the gate is documented --------------------------------------------

def test_the_reference_command_is_documented():
    readme = (REPO_ROOT / "README.md").read_text()
    assert "RP check quality -- " in readme
    assert "xenon" in readme.split("RP check quality")[1][:200]
    for name in ("SKILL.md", "SKILL.de.md"):
        body = (REPO_ROOT / "skills" / "fable-context-maxxing" / name).read_text()
        assert "check quality" in body
