#!/usr/bin/env python3
"""red-proof gate: mechanical enforcement for the red-proof methodology.

State machine per repository:
    CONTRACT_CREATED -> RED_CONFIRMED -> TESTS_FROZEN -> COMMIT_ISSUED

Evidence (targeted tests, full suite, attestation, commit gate) is bound
to a content fingerprint: HEAD plus the content of every modified or
untracked file. Staging (git add) does not change the fingerprint;
any real code change does, which invalidates prior evidence. Each entry
also carries a production fingerprint over the same tree minus the
non-production files, so a check can declare that only production changes
invalidate it (see staleness_policy).

A failed check records the tree it failed on, the command it ran and its
attempt count, so rerunning the same command on an untouched worktree is
refused instead of executed, while a corrected command still runs (see
guard_repeat_run).

Hook mode fails open on internal errors: this is process CI for the
agentic workflow, not a security boundary.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import time

CONFIG_DIR = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
BASE_DIR = os.path.join(CONFIG_DIR, "red-proof")
STATE_DIR = os.path.join(BASE_DIR, "state")
EXEMPT_LOG = os.path.join(BASE_DIR, "exemptions.log")
ERROR_LOG = os.path.join(BASE_DIR, "error.log")
DEFAULT_EXEMPT_HOURS = 4.0
# Failed runs of one check per cycle before the guard stops asking for
# another repair and points at re-planning instead.
DEFAULT_MAX_ATTEMPTS = 5
REPLAN_HINT = ("; the attempt budget for this check is used up: stop "
               "repairing and re-plan the package (workflow section 7)")

# --- metric extractors ----------------------------------------------------
# An extractor reads the captured output of a check and returns a dict of
# named numbers, or None when the output carries no measurement at all.

TOTAL_LINE_RE = re.compile(r"^[ \t]*TOTAL\b.*$", re.MULTILINE)
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)%")
KILLED_OUT_OF_RE = re.compile(r"\bKilled\s+(\d+)\s+out\s+of\s+(\d+)\b")
KILLED_RATIO_RE = re.compile(r"\b(\d+)\s*/\s*(\d+)\s+KILLED\b")
SEED_RE = re.compile(
    r"(?<![-\w])(?:--hypothesis-seed=|HYPOTHESIS_SEED=)(\d+(?:\.\d+)?)")


def extract_coverage(output):
    """Read the coverage percentage from a coverage.py TOTAL line.

    A run can print more than one report (per package, then the total run):
    the last TOTAL line that carries a percentage wins, so the number is the
    one the reader sees at the end. Returns None when no such line exists.
    """
    percent = None
    for line in TOTAL_LINE_RE.findall(output or ""):
        found = PERCENT_RE.findall(line)
        if found:
            percent = float(found[-1])
    if percent is None:
        return None
    return {"coverage_percent": percent}


def extract_mutation(output):
    """Read the mutation score from the output of a mutation run.

    Two shapes are understood, because the tools print both: the summary
    sentence "Killed K out of N", and a result row of the form "K/N KILLED"
    with whatever whitespace the tool chose. Like the coverage extractor,
    the last line that carries either shape wins, so a run that prints a
    progress line and then a summary is read at its end.

    The score is K/N as a percentage and is deliberately not rounded: the
    threshold comparison in check should see the measured number, and the
    display in format_metrics does the shortening.

    N == 0 is not a measurement but an empty run (no mutants generated), so
    it yields None, exactly like output that carries no result at all. With
    --min that turns into a failed check instead of a division by zero or a
    100% claim nobody measured.
    """
    killed = total = None
    for line in (output or "").splitlines():
        m = KILLED_OUT_OF_RE.search(line) or KILLED_RATIO_RE.search(line)
        if m:
            killed, total = int(m.group(1)), int(m.group(2))
    if not total:
        return None
    return {"mutation_score": killed / total * 100}


def extract_hypothesis_seed(command):
    """Read the seed a property run is pinned to, from its command string.

    This is the one extractor that reads the command instead of the output
    (see "extract_from" in CHECKS). The seed is an input to the run, not a
    result of it: a run may print whatever number it likes, while the
    command is what the caller actually chose and what a reader can repeat.

    Two spellings are understood, because both are how a seed reaches a
    property runner: the flag "--hypothesis-seed=<number>" and the
    environment assignment "HYPOTHESIS_SEED=<number>". Neither may be glued
    to a longer word, so "MY_HYPOTHESIS_SEED=3" is not a seed.

    When a command names several seeds, the last one wins. That is what the
    shell and an argument parser both do with a repeated assignment or a
    repeated flag, and it is the same rule the output extractors use.

    Returns None when the command names no seed at all, which is what check
    turns into a usage error before anything runs.
    """
    found = SEED_RE.findall(command or "")
    if not found:
        return None
    return {"hypothesis_seed": float(found[-1])}


# Registry of the evidence-producing checks. "evidence_key" is the key a
# check writes into state["evidence"]; "extract" turns text into a metrics
# dict. "extract_from" names the text that extractor reads: "output" is
# the captured output of the run, "command" is the command string itself,
# for a measurement that is an input to the run rather than something it
# prints (see extract_hypothesis_seed). A check with "command" is refused
# before it runs when its command carries no such measurement.
# The two fields together decide whether --min applies: a check needs an
# extractor to have a number at all, and that number has to come from the
# output, because a threshold on an input grades what the caller typed
# rather than what the run achieved (see parse_min).
# "staleness" says what invalidates the evidence: "strict" is any change to
# the tree, "production" is a change to production code only (see
# staleness_policy for the trade-off that buys).
# Reference commands for this repository:
#   RP check mutation --min 80 -- sh -c "mutmut run && mutmut results"
#   RP check property -- sh -c "HYPOTHESIS_SEED=1234 pytest -q tests/prop"
CHECKS = {
    "targeted": {"evidence_key": "targeted", "staleness": "strict",
                 "extract": None, "extract_from": "output"},
    "full-suite": {"evidence_key": "full_suite", "staleness": "strict",
                   "extract": None, "extract_from": "output"},
    "static": {"evidence_key": "static", "staleness": "strict",
               "extract": None, "extract_from": "output"},
    "quality": {"evidence_key": "quality", "staleness": "strict",
                "extract": None, "extract_from": "output"},
    "deps": {"evidence_key": "deps", "staleness": "strict",
             "extract": None, "extract_from": "output"},
    "e2e": {"evidence_key": "e2e", "staleness": "strict",
            "extract": None, "extract_from": "output"},
    "coverage": {"evidence_key": "coverage", "staleness": "strict",
                 "extract": extract_coverage, "extract_from": "output"},
    "mutation": {"evidence_key": "mutation", "staleness": "production",
                 "extract": extract_mutation, "extract_from": "output"},
    "property": {"evidence_key": "property", "staleness": "strict",
                 "extract": extract_hypothesis_seed,
                 "extract_from": "command"},
}

# A check whose metric comes from the command has to carry that number in
# the command: the run cannot produce it afterwards. Today that is
# "property", whose seed is what makes the run repeatable, so the message
# names both spellings the extractor accepts.
COMMAND_METRIC_USAGE = (
    "check %s needs its seed in the command: pass --hypothesis-seed=<number> "
    "or HYPOTHESIS_SEED=<number>, so the evidence records which seed was "
    "green. Nothing was run, no evidence recorded.")

# The same registry field also settles --min: the metric of such a check is
# an input the caller chose (a seed), not a quality the run achieved, so a
# threshold on it would grade the input. Refused as a usage error, before
# anything runs and without touching the state.
COMMAND_METRIC_NO_MIN = (
    "check '%s' measures its command, not its run: the number is an input "
    "the caller picked (a seed is an input value, not a quality), so --min "
    "cannot be applied to it (checks that accept --min: %s). Nothing was "
    "run, no evidence recorded.")

# Number of characters of captured output kept as evidence.
OUTPUT_TAIL_CHARS = 2000

# Evidence every cycle carries, whatever the contract declares on top.
BASE_EVIDENCE = ("targeted", "full_suite", "attest")

# The kinds of red a proof may claim. "contract" is a missing symbol or
# signature, "behavior" a wrong result, "scenario" a Gherkin scenario whose
# steps are missing or not yet green. Anything else is refused, so the red
# type stays a classification instead of a free-text field.
RED_TYPES = ("contract", "behavior", "scenario")

# Generated paths that never count towards a fingerprint. Two groups,
# because they need different precision:
#
# * FP_IGNORE_SUBSTRINGS matches anywhere in the path. Those entries name
#   artefact families whose real names vary around the entry (".coverage"
#   also appears as ".coverage.host.1234", ".egg-info" as a suffix of a
#   generated directory, ".mutmut-cache" with a sqlite journal next to it),
#   so a wider match is what makes them work.
# * FP_IGNORE_NAMES matches a whole path component, at the repository root
#   and at any depth. "mutants" (the tree mutmut copies the sources into)
#   needs that precision: as a substring it would also swallow a real
#   source file named "mutants_util.py".
#
# FP_IGNORE stays the full list of entries, for readers and for callers
# that only ask what is ignored, not how it is matched.
FP_IGNORE_SUBSTRINGS = ("__pycache__", ".pytest_cache", ".red-proof",
                        "node_modules", ".DS_Store", ".coverage",
                        ".mypy_cache", ".ruff_cache", ".venv", ".tox",
                        ".egg-info", ".mutmut-cache")
FP_IGNORE_NAMES = ("mutants",)
FP_IGNORE = FP_IGNORE_SUBSTRINGS + FP_IGNORE_NAMES

# What is not production code (see is_nonprod). ".feature" is on the suffix
# list because a Gherkin file is specification, not implementation: it is
# written before the code, in the same phase as the acceptance tests, so
# the edit hook must not demand a frozen cycle for it and a production
# staleness policy must not be re-armed by it. Its directory does not
# matter, exactly as for the other specification suffixes.
NONPROD_MARKERS = ("/tests/", "/test/", "/spec/", "/docs/", "/doc/",
                   "/examples/", "/.claude/", "/.red-proof/", "/scratchpad/")
NONPROD_PREFIXES = ("test_", "conftest")
NONPROD_SUFFIXES = (".md", ".rst", ".txt", ".feature", "_test.py", "_test.go",
                    ".spec.ts", ".spec.js", ".spec.tsx",
                    ".test.ts", ".test.js", ".test.tsx")

ALLOW_PATH_PREFIXES = (
    os.path.realpath(os.path.expanduser("~/.claude")),
    "/tmp", "/private/tmp", "/var/folders",
)

GIT_COMMIT_RE = re.compile(r"\bgit(\s+(-C\s+\S+|-c\s+\S+))*\s+commit\b")


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def repo_root(path):
    if not path:
        return None
    code, out, _ = run(["git", "-C", path, "rev-parse", "--show-toplevel"])
    if code != 0:
        return None
    return os.path.realpath(out.strip())


def state_path(root):
    key = hashlib.sha256(root.encode()).hexdigest()[:16]
    return os.path.join(STATE_DIR, key + ".json")


def load_state(root):
    try:
        with open(state_path(root)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(root, state):
    os.makedirs(STATE_DIR, exist_ok=True)
    state["repo"] = root
    with open(state_path(root), "w") as f:
        json.dump(state, f, indent=2)


def fp_skip(path):
    """True when a changed path is generated noise instead of code.

    Name entries have to match a whole path component, substring entries
    match anywhere in the path: see FP_IGNORE for why the list is split.
    Windows separators are tolerated, so callers may pass what the platform
    hands them.
    """
    rel = path.replace("\\", "/")
    if any(part in FP_IGNORE_NAMES for part in rel.split("/")):
        return True
    return any(tok in rel for tok in FP_IGNORE_SUBSTRINGS) or rel.endswith(".pyc")


def is_nonprod(rel_path):
    """True when a repository-relative path is not production code.

    One classification, two readers: the edit hook decides with it which
    files may change outside a cycle, and production_fingerprint decides
    with it which files a production-staleness policy ignores. Windows
    separators and a leading "./" are tolerated, so callers may pass what
    git or the platform hands them. Directory markers are matched with a
    leading slash, so "tests/x.py" reads the same as "pkg/tests/x.py".
    """
    rel = rel_path.replace("\\", "/").lstrip("/")
    while rel.startswith("./"):
        rel = rel[2:]
    rel = "/" + rel
    if any(m in rel for m in NONPROD_MARKERS):
        return True
    base = rel.rsplit("/", 1)[-1]
    return base.startswith(NONPROD_PREFIXES) or rel.endswith(NONPROD_SUFFIXES)


def changed_paths(root):
    code, out, _ = run(
        ["git", "status", "--porcelain=v1", "-z", "-uall"], root)
    if code != 0:
        raise RuntimeError("git status failed in " + root)
    toks = out.split("\0")
    paths, i = [], 0
    while i < len(toks):
        t = toks[i]
        if not t:
            i += 1
            continue
        status, p = t[:2], t[3:]
        paths.append(p)
        if status and status[0] in "RC":
            i += 1
            if i < len(toks) and toks[i]:
                paths.append(toks[i])
        i += 1
    return paths


def hash_tree(root, skip):
    """HEAD plus the content of every changed path that survives `skip`."""
    code, out, _ = run(["git", "rev-parse", "HEAD"], root)
    head = out.strip() if code == 0 else "NO_HEAD"
    h = hashlib.sha256(head.encode())
    for p in sorted(set(changed_paths(root))):
        if fp_skip(p) or skip(p):
            continue
        h.update(b"\0" + p.encode())
        full = os.path.join(root, p)
        if os.path.isfile(full):
            with open(full, "rb") as f:
                h.update(hashlib.sha256(f.read()).digest())
        else:
            h.update(b"ABSENT")
    return h.hexdigest()


def fingerprint(root):
    """The full code state: every changed or untracked file counts."""
    return hash_tree(root, lambda p: False)


def production_fingerprint(root):
    """The production part of the same state.

    Identical construction to fingerprint over the identical changed_paths
    source, with the non-production files left out. changed_paths yields
    repository-relative paths, which is what is_nonprod expects.
    """
    return hash_tree(root, is_nonprod)


def staged_patch_hash(root, paths):
    code, out, _ = run(["git", "diff", "--cached", "--"] + list(paths), root)
    if code != 0:
        raise RuntimeError("git diff --cached failed")
    return hashlib.sha256(out.encode()).hexdigest()


def verify_freeze(state, root):
    fr = state.get("freeze")
    if not fr:
        return False, "no freeze recorded (run: freeze after git add of acceptance tests)"
    paths = fr.get("paths", [])
    if staged_patch_hash(root, paths) != fr.get("patch_hash"):
        return False, "staged acceptance-test patch is not byte-identical to the frozen patch"
    code, out, _ = run(["git", "diff", "--name-only", "--"] + paths, root)
    dirty = [line for line in out.splitlines() if line.strip()]
    if dirty:
        return False, "working-tree modification of frozen tests: " + ", ".join(dirty)
    return True, "frozen acceptance-test patch intact"


def exempt_active(state):
    return state.get("exempt_until", 0) > time.time()


def log_line(path, text):
    os.makedirs(BASE_DIR, exist_ok=True)
    with open(path, "a") as f:
        f.write(text.rstrip() + "\n")


def fail(msg):
    print("red-proof: FAIL: " + msg)
    sys.exit(1)


def ok(msg):
    print("red-proof: " + msg)


def parse_opts(argv):
    opts, rest, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--":
            rest = argv[i + 1:]
            break
        if a.startswith("--"):
            key = a[2:].replace("-", "_")
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                opts[key] = argv[i + 1]
                i += 2
            else:
                opts[key] = True
                i += 1
        else:
            i += 1
    return opts, rest


def require_repo():
    root = repo_root(os.getcwd())
    if not root:
        fail("not inside a git repository")
    return root


def check_names():
    return ", ".join(CHECKS)


def required_evidence(spec):
    """Evidence keys a cycle must carry: the base set plus the --require names.

    Order follows the mention, duplicates collapse. An unknown name aborts
    before anything is written, so a rejected contract leaves the state as
    it was.
    """
    keys = list(BASE_EVIDENCE)
    if spec is None:
        return keys
    if spec is True:
        fail("usage: contract --file <contract.md> [--require <name>,<name>] "
             "[--max-attempts <n>] (valid: %s)" % check_names())
    for name in [part.strip() for part in str(spec).split(",")]:
        if name not in CHECKS:
            fail("unknown check in --require: '%s' (valid: %s)"
                 % (name, check_names()))
        key = CHECKS[name]["evidence_key"]
        if key not in keys:
            keys.append(key)
    return keys


def parse_max_attempts(spec):
    """Validate --max-attempts: a positive whole number, default 5.

    The budget is stored per cycle, so a package that is known to need a
    longer repair loop can raise it in its own contract without changing
    the default for everyone else.
    """
    if spec is None:
        return DEFAULT_MAX_ATTEMPTS
    try:
        value = int(str(spec))
    except (TypeError, ValueError):
        value = 0
    if value < 1:
        fail("--max-attempts expects a positive whole number, got '%s'" % spec)
    return value


def cmd_contract(argv):
    opts, _ = parse_opts(argv)
    path = opts.get("file")
    if not path or not os.path.isfile(path):
        fail("usage: contract --file <contract.md> [--require <name>,<name>] "
             "[--max-attempts <n>] (valid: %s)" % check_names())
    required = required_evidence(opts.get("require"))
    attempts = parse_max_attempts(opts.get("max_attempts"))
    root = require_repo()
    with open(path, "rb") as f:
        text = f.read()
    chash = hashlib.sha256(text).hexdigest()
    os.makedirs(STATE_DIR, exist_ok=True)
    copy = state_path(root).replace(".json", ".contract.md")
    with open(copy, "wb") as f:
        f.write(text)
    state = {
        "phase": "CONTRACT_CREATED",
        "contract_hash": chash,
        "contract_copy": copy,
        "created": time.time(),
        "red_proofs": [],
        "evidence": {},
        "required_evidence": required,
        "max_attempts": attempts,
        "gate_attempts": {},
    }
    save_state(root, state)
    ok("contract registered (%s), phase=CONTRACT_CREATED, required evidence: %s, "
       "%d attempts per check, previous cycle state replaced"
       % (chash[:12], ", ".join(required), attempts))


def cmd_red(argv):
    opts, cmd = parse_opts(argv)
    test = opts.get("test")
    red_type = opts.get("type")
    expected = opts.get("expected")
    if not (test and red_type in RED_TYPES and expected and cmd):
        fail("usage: red --test <name> --type %s --expected '<reason>' "
             "-- <test command>" % "|".join(RED_TYPES))
    root = require_repo()
    state = load_state(root)
    if state.get("phase") not in ("CONTRACT_CREATED", "RED_CONFIRMED"):
        fail("red requires phase CONTRACT_CREATED (current: %s)" % state.get("phase"))
    r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if r.returncode == 0:
        fail("expected red, but the test command exited 0: not a valid red")
    tail = (r.stdout + "\n" + r.stderr)[-2000:]
    state.setdefault("red_proofs", []).append({
        "test": test,
        "red_type": red_type,
        "expected_failure": expected,
        "actual_output_tail": tail,
        "command": " ".join(cmd),
        "exit_code": r.returncode,
        "ts": time.time(),
    })
    state["phase"] = "RED_CONFIRMED"
    save_state(root, state)
    ok("red confirmed for %s (exit %d). Verify the actual failure reason matches: %s"
       % (test, r.returncode, expected))


def cmd_freeze(argv):
    root = require_repo()
    state = load_state(root)
    if state.get("phase") != "RED_CONFIRMED":
        fail("freeze requires phase RED_CONFIRMED (current: %s)" % state.get("phase"))
    code, out, _ = run(["git", "diff", "--cached", "--name-only"], root)
    paths = [line for line in out.splitlines() if line.strip()]
    if code != 0 or not paths:
        fail("nothing staged: git add the acceptance tests first")
    state["freeze"] = {
        "paths": paths,
        "patch_hash": staged_patch_hash(root, paths),
        "head": run(["git", "rev-parse", "HEAD"], root)[1].strip(),
        "contract_hash": state.get("contract_hash"),
        "ts": time.time(),
    }
    state["phase"] = "TESTS_FROZEN"
    save_state(root, state)
    ok("acceptance tests frozen (%d files), phase=TESTS_FROZEN, implementation may begin" % len(paths))


def metric_value(metrics):
    """The number --min is compared against: the first one the extractor named.

    Extractors return a single measurement today; taking the first numeric
    value keeps the threshold rule the same for every future extractor.
    """
    for value in (metrics or {}).values():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def parse_min(value, name, spec):
    """Validate --min for a check: None, or a float on a check --min fits.

    Two refusals, both usage errors and both decided by the registry entry
    rather than by the name of the check, so a future check inherits them:
    a check without an extractor has no number to compare, and a check
    whose extractor reads the command has a number that the caller chose
    instead of one the run produced. Whether the flag applies at all is
    settled before its value is read, because a threshold on a check that
    cannot carry one is wrong whatever number follows it.
    """
    if value is None:
        return None
    if value is True or isinstance(value, str) and not value.strip():
        fail("usage: check %s --min <number> -- <command>" % name)
    if spec["extract"] is None:
        fail("check '%s' produces no metric, so --min cannot be applied to it "
             "(checks that accept --min: %s)" % (name, min_check_names()))
    if spec["extract_from"] == "command":
        fail(COMMAND_METRIC_NO_MIN % (name, min_check_names()))
    try:
        return float(value)
    except (TypeError, ValueError):
        fail("--min expects a number, got '%s'" % value)


def min_check_names():
    """The checks a threshold can be applied to, for the usage messages."""
    named = [n for n, spec in CHECKS.items()
             if spec["extract"] and spec["extract_from"] == "output"]
    return ", ".join(named) if named else "none"


def format_metrics(metrics):
    return ", ".join("%s=%g" % (k, v) for k, v in (metrics or {}).items()
                     if isinstance(v, (int, float)) and not isinstance(v, bool))


def max_attempts(state):
    """The attempt budget of the current cycle, defaulted for older state."""
    try:
        limit = int(state.get("max_attempts") or DEFAULT_MAX_ATTEMPTS)
    except (TypeError, ValueError):
        return DEFAULT_MAX_ATTEMPTS
    return limit if limit > 0 else DEFAULT_MAX_ATTEMPTS


def attempt_note(state, count):
    """The counter appended to a failing check, with the escalation hint.

    The hint appears as soon as the budget is reached, not one attempt
    later: the run that uses up the budget is the one whose message has to
    say that repairing is over.
    """
    limit = max_attempts(state)
    note = " (attempt %d of %d)" % (count, limit)
    return note + REPLAN_HINT if count >= limit else note


def gate_attempt(state, name):
    """The recorded failed-attempt entry of one check, empty when there is none."""
    return (state.get("gate_attempts") or {}).get(name) or {}


def store_gate_attempt(root, state, name, entry):
    state.setdefault("gate_attempts", {})[name] = entry
    save_state(root, state)


def same_command(prior, command):
    """True when a recorded failure was produced by this very command.

    An entry written before the command was recorded carries no "command"
    key. It reads as a match, the conservative direction: the guard keeps
    blocking exactly where it blocked before, instead of waving a rerun
    through on the strength of a field that was never written.
    """
    recorded = prior.get("command")
    return recorded is None or recorded == command


def guard_repeat_run(root, state, name, command):
    """Refuse to rerun a failed check on a worktree nobody has touched.

    Two things have to be identical for a run to count as a repeat: the
    tree and the command. Rerunning the same command on the same tree can
    only produce the same failure, while a corrected command is a real
    repair attempt and has to execute, since fixing a typo in the command
    changes no file. The attempt counter is not reset by that: it belongs
    to the check, not to one spelling of its command, so the next failure
    counts on from where the previous one left off.

    Returns the fingerprint the run is about to start from, which the fail
    path records. The comparison is always the full fingerprint, never the
    production one: a failing check is repaired by changing production code
    or tests, and both have to re-arm it, whatever staleness policy the
    check's evidence carries.
    """
    fp = fingerprint(root)
    prior = gate_attempt(state, name)
    if fp not in (prior.get("fail_fingerprint"), prior.get("post_fingerprint")):
        return fp
    if not same_command(prior, command):
        return fp
    entry = dict(prior)
    entry["count"] = int(prior.get("count") or 0) + 1
    store_gate_attempt(root, state, name, entry)
    fail("worktree unchanged since last failed %s run%s: change code or tests "
         "before re-running" % (name, attempt_note(state, entry["count"])))


def record_check_failure(root, state, name, started_from, command, msg):
    """Count a failed check, remember the tree it failed on, then fail.

    Two fingerprints are kept: the tree the command started from and the
    tree it left behind. A rerun counts as a repeat when the worktree
    matches either one, so a command that writes into its own worktree (a
    log, a cache the ignore list does not cover) is still recognised as
    unchanged instead of silently re-arming the guard. The command is kept
    with them, because the guard blocks a repeat of this command only.
    """
    count = int(gate_attempt(state, name).get("count") or 0) + 1
    store_gate_attempt(root, state, name, {
        "fail_fingerprint": started_from,
        "post_fingerprint": fingerprint(root),
        "command": command,
        "count": count,
    })
    fail(msg + attempt_note(state, count))


def guard_command_metric(name, spec, command):
    """Refuse a command-extracted check whose command carries no metric.

    Runs before the command does, and before the repeat guard: a command
    without its seed is a usage error, not a failed attempt. It must
    neither spend an attempt from the budget nor arm guard_repeat_run
    against the very rerun that adds the seed, since adding it does not
    change the worktree.
    """
    if spec["extract_from"] != "command":
        return
    if spec["extract"](command) is None:
        fail(COMMAND_METRIC_USAGE % name)


def measure(spec, command, output):
    """Run a check's extractor over the text its registry entry names."""
    extract = spec["extract"]
    if not extract:
        return None
    return extract(command if spec["extract_from"] == "command" else output)


def cmd_check(argv):
    if not argv:
        fail("usage: check freeze|%s [--min <number>] [-- <command>]"
             % "|".join(CHECKS))
    name = argv[0]
    opts, cmd = parse_opts(argv[1:])
    if name == "freeze":
        root = require_repo()
        good, msg = verify_freeze(load_state(root), root)
        if not good:
            fail(msg)
        ok(msg)
        return
    if name not in CHECKS:
        fail("unknown check: '%s' (valid: freeze, %s)" % (name, check_names()))
    spec = CHECKS[name]
    minimum = parse_min(opts.get("min"), name, spec)
    root = require_repo()
    state = load_state(root)
    if state.get("phase") not in ("TESTS_FROZEN", "COMMIT_ISSUED"):
        fail("check %s requires phase TESTS_FROZEN (current: %s)" % (name, state.get("phase")))
    if not cmd:
        fail("usage: check %s [--min <number>] -- <test command>" % name)
    command = " ".join(cmd)
    guard_command_metric(name, spec, command)
    started_from = guard_repeat_run(root, state, name, command)
    # Captured so the tail and any metric can be read, then handed straight
    # through so the caller still sees the run it asked for.
    r = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if r.stdout:
        print(r.stdout, end="")
    sys.stdout.flush()
    if r.stderr:
        sys.stderr.write(r.stderr)
        sys.stderr.flush()
    output = r.stdout + r.stderr
    if r.returncode != 0:
        record_check_failure(root, state, name, started_from, command,
                             "%s run exited %d: evidence NOT recorded"
                             % (name, r.returncode))
    metrics = measure(spec, command, output)
    if minimum is not None:
        measured = metric_value(metrics)
        if measured is None:
            record_check_failure(root, state, name, started_from, command,
                                 "%s: no metric found in the output, --min %g "
                                 "cannot be verified: evidence NOT recorded"
                                 % (name, minimum))
        if measured < minimum:
            record_check_failure(root, state, name, started_from, command,
                                 "%s below threshold: measured %g, --min %g: "
                                 "evidence NOT recorded"
                                 % (name, measured, minimum))
    state.setdefault("evidence", {})[spec["evidence_key"]] = {
        "fingerprint": fingerprint(root),
        "production_fingerprint": production_fingerprint(root),
        "command": command,
        "ts": time.time(),
        "output_tail": output[-OUTPUT_TAIL_CHARS:],
        "metrics": metrics,
        "min": minimum,
        # Only the green path reaches this record: every failure above
        # counts an attempt and exits. The flag states that in the entry
        # itself, so a reader of the state file does not have to know the
        # code to tell what an existing entry means.
        "passed": True,
    }
    # A green run closes the repair loop for this check: the next failure
    # starts counting from one again.
    state.setdefault("gate_attempts", {}).pop(name, None)
    save_state(root, state)
    detail = format_metrics(metrics)
    ok("%s green%s, evidence bound to current code fingerprint"
       % (name, " (%s)" % detail if detail else ""))


def cmd_attest(argv):
    opts, _ = parse_opts(argv)
    if not (opts.get("diff_reviewed") and opts.get("contract_ok")):
        fail("usage: attest --diff-reviewed --contract-ok (only after actually reading every changed hunk and checking each acceptance criterion)")
    root = require_repo()
    state = load_state(root)
    if state.get("phase") not in ("TESTS_FROZEN", "COMMIT_ISSUED"):
        fail("attest requires phase TESTS_FROZEN (current: %s)" % state.get("phase"))
    state.setdefault("evidence", {})["attest"] = {
        "fingerprint": fingerprint(root),
        "production_fingerprint": production_fingerprint(root),
        "diff_reviewed": True,
        "contract_ok": True,
        "ts": time.time(),
    }
    save_state(root, state)
    ok("attestation recorded, bound to current code fingerprint")


def staleness_policy(key):
    """The staleness policy of an evidence key, looked up through CHECKS.

    Trade-off, deliberately taken: a "production" key survives edits to
    tests, fixtures and documentation, so evidence that is expensive to
    produce (a mutation run) does not have to be repeated for a docstring
    fix or an added regression test. That is weaker than "strict", and it
    is not the mechanism that protects the frozen acceptance tests: the
    freeze check does that, by comparing the staged patch byte for byte
    and rejecting any working-tree edit of a frozen file. Anything CHECKS
    does not name (attest, commit_ready) stays strict.
    """
    for spec in CHECKS.values():
        if spec["evidence_key"] == key:
            return spec["staleness"]
    return "strict"


def is_stale(item, key, fp, prod_fp):
    """True when an evidence entry no longer describes the current code.

    Evidence written before the production fingerprint existed carries no
    "production_fingerprint": it is judged strictly, so an older state file
    can never weaken the gate.
    """
    recorded = item.get("production_fingerprint")
    if recorded and staleness_policy(key) == "production":
        return recorded != prod_fp
    return item.get("fingerprint") != fp


def cmd_commit_gate(argv):
    root = require_repo()
    state = load_state(root)
    if state.get("phase") not in ("TESTS_FROZEN", "COMMIT_ISSUED"):
        fail("commit-gate requires phase TESTS_FROZEN (current: %s)" % state.get("phase"))
    problems = []
    good, msg = verify_freeze(state, root)
    if not good:
        problems.append("freeze: " + msg)
    if not state.get("red_proofs"):
        problems.append("no red proof recorded")
    fp = fingerprint(root)
    prod_fp = production_fingerprint(root)
    ev = state.get("evidence", {})
    for key in state.get("required_evidence", list(BASE_EVIDENCE)):
        item = ev.get(key)
        if not item:
            problems.append("missing evidence: " + key)
        elif is_stale(item, key, fp, prod_fp):
            problems.append("stale evidence (code changed since): " + key)
    if problems:
        fail("commit gate NOT passed:\n  - " + "\n  - ".join(problems))
    ev["commit_ready"] = {"fingerprint": fp, "ts": time.time()}
    state["evidence"] = ev
    save_state(root, state)
    ok("COMMIT GATE PASSED, exactly one git commit is now allowed for this code state")


def cmd_exempt(argv):
    opts, _ = parse_opts(argv)
    reason = opts.get("reason")
    if not reason or reason is True:
        fail("usage: exempt --reason '<why this task is exempt>' [--hours N]")
    hours = float(opts.get("hours", DEFAULT_EXEMPT_HOURS))
    root = require_repo()
    state = load_state(root)
    state["exempt_until"] = time.time() + hours * 3600
    state["exempt_reason"] = reason
    save_state(root, state)
    log_line(EXEMPT_LOG, "%s  %s  %.1fh  %s"
             % (time.strftime("%Y-%m-%d %H:%M:%S"), root, hours, reason))
    ok("exemption recorded for %.1fh: %s (logged to %s)" % (hours, reason, EXEMPT_LOG))


def cmd_status(argv):
    root = require_repo()
    state = load_state(root)
    good, msg = (verify_freeze(state, root) if state.get("freeze") else (None, "no freeze"))
    out = {
        "repo": root,
        "phase": state.get("phase"),
        "contract_hash": state.get("contract_hash"),
        "red_proofs": [r.get("test") for r in state.get("red_proofs", [])],
        "frozen_paths": state.get("freeze", {}).get("paths"),
        "freeze_check": msg,
        "required_evidence": list(state.get("required_evidence", BASE_EVIDENCE)),
        "evidence": {k: {"fingerprint": v.get("fingerprint", "")[:12], "ts": v.get("ts")}
                     for k, v in state.get("evidence", {}).items()},
        "current_fingerprint": fingerprint(root)[:12],
        "exempt_until": state.get("exempt_until"),
        "exempt_reason": state.get("exempt_reason"),
    }
    print(json.dumps(out, indent=2))


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


CLI = "python3 " + os.path.join(BASE_DIR, "red_proof.py")


def hook_edit(data):
    tool_input = data.get("tool_input") or {}
    path = tool_input.get("file_path")
    if not path:
        return
    path = os.path.realpath(os.path.expanduser(path))
    if any(path.startswith(p) for p in ALLOW_PATH_PREFIXES):
        return
    root = repo_root(os.path.dirname(path))
    if not root:
        return
    if is_nonprod(os.path.relpath(path, root)):
        return
    state = load_state(root)
    if exempt_active(state):
        return
    phase = state.get("phase")
    if phase == "TESTS_FROZEN":
        return
    if phase in ("CONTRACT_CREATED", "RED_CONFIRMED"):
        deny("red-proof: acceptance tests are not frozen yet (phase %s). "
             "Complete the red phase (%s red ... -- <cmd>), then git add the "
             "acceptance tests and run: %s freeze. Production code may only "
             "change in phase TESTS_FROZEN." % (phase, CLI, CLI))
    if phase == "COMMIT_ISSUED":
        deny("red-proof: the previous commit cycle is closed. Start a new "
             "Commit Contract before further production changes: "
             "%s contract --file <contract.md>" % CLI)
    deny("red-proof: no active cycle for this repository. Production-code "
         "changes require the red-proof cycle (load the icca-harness skill). "
         "Start with: %s contract --file <contract.md>. For an exempt task "
         "(research, docs-only, trivial typo), classify it explicitly: "
         "%s exempt --reason '<why>'" % (CLI, CLI))


def strip_quoted(cmd):
    cmd = re.sub(r"'[^']*'", "''", cmd)
    cmd = re.sub(r'"[^"]*"', '""', cmd)
    return cmd


def bash_target_root(command, cwd):
    # A "git -C <dir>" hint counts only when that same invocation is the
    # commit: a -C on another subcommand does not move the commit. Apart from
    # that, only a leading "cd <dir>" counts. Subshells, variables, chained cd
    # and pushd stay out of scope and keep the reported cwd, as does any hint
    # that is not a git repository.
    word = r"'[^']*'|\"[^\"]*\"|[^\s;&|<>]+"
    sp = r"(?:[ \t]|\\\n)+"
    opt = r"-[cC]" + sp + r"(?:" + word + r")|--?[A-Za-z][-\w]*(?:=\S+)?"
    opts = r"(?:" + sp + r"(?:" + opt + r"))*"
    for m in (re.search(r"\bgit" + opts + sp + r"-C" + sp + r"(" + word +
                        r")" + opts + sp + r"commit\b", command),
              re.search(r"^\s*cd\s+(" + word + r")", command)):
        if not m:
            continue
        d = m.group(1)
        if len(d) > 1 and d[0] == d[-1] and d[0] in "'\"":
            d = d[1:-1]
        d = os.path.expanduser(d)
        if not os.path.isabs(d):
            d = os.path.join(cwd, d)
        if not os.path.isdir(d):
            continue
        root = repo_root(d)
        if root:
            return root
    return repo_root(cwd)


def hook_bash(data):
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or ""
    if not GIT_COMMIT_RE.search(strip_quoted(command)):
        return
    root = bash_target_root(command, data.get("cwd") or os.getcwd())
    if not root:
        return
    state = load_state(root)
    if exempt_active(state):
        log_line(EXEMPT_LOG, "%s  %s  commit under exemption: %s"
                 % (time.strftime("%Y-%m-%d %H:%M:%S"), root,
                    state.get("exempt_reason")))
        return
    ev = state.get("evidence", {})
    ready = ev.get("commit_ready")
    # The re-check at commit time stays strict on the full fingerprint, on
    # purpose: commit_ready binds the exact code state the gate saw, so any
    # later edit, production or not, has to go back through commit-gate.
    # That equality also settles every required key, whatever its policy,
    # because the tree is byte-identical to the one the gate accepted.
    if ready and ready.get("fingerprint") == fingerprint(root):
        good, msg = verify_freeze(state, root)
        if good:
            del ev["commit_ready"]
            state["evidence"] = ev
            state["phase"] = "COMMIT_ISSUED"
            save_state(root, state)
            return
        deny("red-proof: freeze violated at commit time: " + msg)
    if ready:
        deny("red-proof: Commit Gate evidence is stale, code changed since "
             "verification. Re-run checks and %s commit-gate." % CLI)
    deny("red-proof: Commit Gate has not passed for this repository. "
         "Required: %s check targeted -- <cmd>; check full-suite -- <cmd>; "
         "attest --diff-reviewed --contract-ok; commit-gate. For an exempt "
         "task: %s exempt --reason '<why>'" % (CLI, CLI))


def main():
    argv = sys.argv[1:]
    if not argv:
        fail("usage: contract|red|freeze|check|attest|commit-gate|exempt|status|hook")
    cmd = argv[0]
    if cmd == "hook":
        try:
            data = json.load(sys.stdin)
            if len(argv) > 1 and argv[1] == "edit":
                hook_edit(data)
            elif len(argv) > 1 and argv[1] == "bash":
                hook_bash(data)
        except SystemExit:
            raise
        except Exception as e:
            try:
                log_line(ERROR_LOG, "%s  hook error: %r"
                         % (time.strftime("%Y-%m-%d %H:%M:%S"), e))
            except OSError:
                pass
        sys.exit(0)
    handlers = {
        "contract": cmd_contract,
        "red": cmd_red,
        "freeze": cmd_freeze,
        "check": cmd_check,
        "attest": cmd_attest,
        "commit-gate": cmd_commit_gate,
        "exempt": cmd_exempt,
        "status": cmd_status,
    }
    fn = handlers.get(cmd)
    if not fn:
        fail("unknown command: " + cmd)
    fn(argv[1:])


if __name__ == "__main__":
    main()
