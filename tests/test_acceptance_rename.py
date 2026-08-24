"""Acceptance tests for contract pub-r1-rename: the harness is icca-harness.

ICCA names the four separated roles (Implementer, Checker, Control,
Auditor). The old product name disappears from every tracked file, the
skill moves, and product-binding vendor prose becomes model-neutral
while measured facts keep their model names.
"""

import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Built by concatenation so this file never matches its own needle.
OLD_NAME = "fable-context" + "-maxxing"
OLD_SUBSCRIPTION = "Fable " + "subscription"
OLD_TOKENS = "Fable " + "tokens"


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO,
                         capture_output=True, text=True, check=True)
    return [REPO / line for line in out.stdout.splitlines()]


def tracked_text():
    chunks = []
    for path in tracked_files():
        try:
            chunks.append((path, path.read_text(encoding="utf-8")))
        except (UnicodeDecodeError, IsADirectoryError):
            continue
    return chunks


# --- AC1: the old product name is gone --------------------------------------

def test_no_tracked_file_carries_the_old_name():
    hits = [str(p.relative_to(REPO)) for p, text in tracked_text()
            if OLD_NAME in text]
    assert hits == [], hits


# --- AC2: the skill moved ---------------------------------------------------

def test_the_skill_directory_moved():
    new = REPO / "skills" / "icca-harness"
    assert (new / "SKILL.md").exists()
    assert (new / "SKILL.de.md").exists()
    assert not (REPO / "skills" / OLD_NAME).exists()


def test_the_frontmatter_names_icca():
    for name in ("SKILL.md", "SKILL.de.md"):
        head = (REPO / "skills" / "icca-harness" / name).read_text()[:600]
        assert "name: icca-harness" in head, name
    english = (REPO / "skills" / "icca-harness" / "SKILL.md").read_text()
    assert "Implementer, Checker, Control, Auditor" in english[:1200]


# --- AC3: install.sh installs the new skill ---------------------------------

def test_install_targets_the_new_skill():
    text = (REPO / "install.sh").read_text()
    assert "skills/icca-harness" in text
    assert OLD_NAME not in text


# --- AC4: the README headline is model-neutral ------------------------------

def test_the_readme_headline_and_acronym():
    text = (REPO / "README.md").read_text()
    first_chunk = text[:600]
    assert "icca-harness" in first_chunk
    assert "40%" in first_chunk
    assert "expensive-model subscription" in first_chunk
    assert OLD_SUBSCRIPTION not in first_chunk
    intro = text[:2500]
    for role in ("Implementer", "Checker", "Control", "Auditor"):
        assert role in intro, role


# --- AC5: the gate CLI mirrors the lab ---------------------------------------

def test_the_gate_cli_is_byte_identical_to_the_lab():
    lab = Path.home() / "Desktop" / "icca-harness-lab" / "bin" / "red_proof.py"
    ours = REPO / "bin" / "red_proof.py"
    assert ours.read_bytes() == lab.read_bytes()


# --- AC6: neutral product prose, preserved measured facts -------------------

def test_product_binding_phrases_are_gone_but_facts_stay():
    subscription_hits = []
    token_hits = []
    fact_mentions = 0
    for path, text in tracked_text():
        rel = str(path.relative_to(REPO))
        if OLD_SUBSCRIPTION in text:
            subscription_hits.append(rel)
        if OLD_TOKENS in text:
            token_hits.append(rel)
        fact_mentions += text.count("claude-fable-5")
        fact_mentions += text.count("Claude Fable 5")
    assert subscription_hits == [], subscription_hits
    assert token_hits == [], token_hits
    assert fact_mentions >= 1, "measured facts must not be scrubbed"
