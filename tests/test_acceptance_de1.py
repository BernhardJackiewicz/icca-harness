"""Acceptance tests for contract pub-backport-3: deps and e2e gates.

Two new opt-in CHECKS entries with exactly the shape of static and
quality: exit-code gated, no --min, strict staleness, snapshot guard
and attempt budget inherited. The tests drive the real CLI in scratch
repositories through the shared fixtures.
"""

import sys
from pathlib import Path

import pytest
from conftest import freeze_cycle, read_state

BIN_DIR = str(Path(__file__).resolve().parents[1] / "bin")
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

import red_proof  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
NEW_CHECKS = ("deps", "e2e")


# --- AC1: the registry entries ----------------------------------------------

@pytest.mark.parametrize("name", NEW_CHECKS)
def test_registry_shape(name):
    spec = red_proof.CHECKS[name]
    assert spec == {"evidence_key": name, "staleness": "strict",
                    "extract": None, "extract_from": "output"}
    assert name in red_proof.check_names()
    assert name not in red_proof.min_check_names()


# --- AC2: the pass path -----------------------------------------------------

@pytest.mark.parametrize("name", NEW_CHECKS)
def test_pass_records_evidence(rp, claude_home, git_repo, name):
    repo = freeze_cycle(rp, claude_home, git_repo())
    r = rp(["check", name, "--", sys.executable, "-c", "print('ok')"],
           env=claude_home, cwd=repo)
    assert r.returncode == 0, r.stdout + r.stderr
    state = read_state(claude_home, repo)
    assert state["evidence"][name]["passed"] is True


# --- AC3: the fail path arms the snapshot guard -----------------------------

@pytest.mark.parametrize("name", NEW_CHECKS)
def test_failure_counts_and_guards(rp, claude_home, git_repo, name):
    repo = freeze_cycle(rp, claude_home, git_repo())
    fail_cmd = [sys.executable, "-c", "raise SystemExit(1)"]
    r = rp(["check", name, "--", *fail_cmd], env=claude_home, cwd=repo)
    assert r.returncode != 0
    again = rp(["check", name, "--", *fail_cmd], env=claude_home, cwd=repo)
    assert again.returncode != 0
    out = (again.stdout + again.stderr).lower()
    assert "unchanged" in out or "attempt" in out


# --- AC4: --min is refused before anything runs -----------------------------

@pytest.mark.parametrize("name", NEW_CHECKS)
def test_min_is_refused(rp, claude_home, git_repo, name):
    repo = freeze_cycle(rp, claude_home, git_repo())
    r = rp(["check", name, "--min", "5", "--",
            sys.executable, "-c", "print('never')"],
           env=claude_home, cwd=repo)
    assert r.returncode != 0
    out = r.stdout + r.stderr
    assert "no metric" in out
    assert "never" not in out


# --- AC5: both requirable, both gate the commit -----------------------------

def test_required_deps_and_e2e_block_the_gate_until_green(rp, claude_home,
                                                          git_repo):
    repo = freeze_cycle(rp, claude_home, git_repo(),
                        contract_args=("--require", "deps,e2e"))
    state = read_state(claude_home, repo)
    assert "deps" in state["required_evidence"]
    assert "e2e" in state["required_evidence"]
    ok = [sys.executable, "-c", "print('ok')"]
    for name in ("targeted", "full-suite"):
        r = rp(["check", name, "--", *ok], env=claude_home, cwd=repo)
        assert r.returncode == 0, r.stdout + r.stderr
    r = rp(["attest", "--diff-reviewed", "--contract-ok"],
           env=claude_home, cwd=repo)
    assert r.returncode == 0
    blocked = rp(["commit-gate"], env=claude_home, cwd=repo)
    assert blocked.returncode != 0
    assert "deps" in (blocked.stdout + blocked.stderr)
    r = rp(["check", "deps", "--", *ok], env=claude_home, cwd=repo)
    assert r.returncode == 0
    still = rp(["commit-gate"], env=claude_home, cwd=repo)
    assert still.returncode != 0
    assert "e2e" in (still.stdout + still.stderr)
    r = rp(["check", "e2e", "--", *ok], env=claude_home, cwd=repo)
    assert r.returncode == 0
    passed = rp(["commit-gate"], env=claude_home, cwd=repo)
    assert passed.returncode == 0, passed.stdout + passed.stderr


# --- AC6: documented as built but unmeasured --------------------------------

def test_the_reference_commands_are_documented():
    readme = (REPO_ROOT / "README.md").read_text()
    assert "RP check deps -- " in readme
    assert "RP check e2e -- " in readme
    tail = readme.split("RP check deps")[1]
    assert "unmeasured" in tail[:2500]
    for name in ("SKILL.md", "SKILL.de.md"):
        body = (REPO_ROOT / "skills" / "icca-harness" / name).read_text()
        assert "check deps" in body, name
        assert "check e2e" in body, name
