# icca-harness

**Get about 40% more out of an expensive-model subscription: on
implementation-heavy work this workflow spends 28% fewer tokens on the
expensive model, at an identical success rate.** The orchestrator's
context holds decisions; the volume (implementation, search, test output,
audit) runs in delegated or fresh contexts.

ICCA names the four separated roles that carry the method: Implementer,
Checker, Control, Auditor. The harness is the machinery around them, not
an agent itself.

Measured over 16 paired runs, not estimated: cost is read from the `usage`
field of every response and the raw per-run data ships in this repository.

Three things that number does not say, stated here rather than in a
footnote, because they decide whether it is worth anything to you:

- **It spends more tokens overall, not fewer.** Delegation moves work to
  the cheaper model rather than removing it, and it adds a briefing and a
  cold start: across both models the large task used 37% *more* tokens.
  It is a win when the strongest model is the scarce resource, which is
  the normal case on a subscription, and a loss when you are counting
  every token you buy.
- **It costs more on small tasks.** On a one-module fix the same
  measurement shows 7% more tokens on the expensive model and 119% more
  across both. The break-even is real and it is documented below.
- **It was measured on small synthetic repositories**, at roughly 5 tool
  calls and $0.22 per run. Nothing here has been measured at the scale of
  a large production codebase.

Doing that safely needs one thing: if the strongest model is not reading
every line the implementer wrote, something other than trust has to
verify the result. So this ships with an evidence-gated commit cycle
that a hook actually enforces, called red-proof.

## Why the context window is the scarce resource

The strongest model in a subscription is also the one you run out of
first. And the default agentic loop spends it in the worst possible way:
one model does everything in one context that only ever grows.

Look at where the tokens actually go in a single feature. Locating the
right code, reading files that turn out to be irrelevant, three failed
attempts at a fix, the full output of a test suite, then a summary of
all of it so the next round still has the thread. That is tens of
thousands of tokens of tool output feeding a decision that is worth a
few hundred. Every one of them sits in the expensive window, and every
one of them is re-sent with the next request.

The fix is not a shorter prompt. It is putting the volume somewhere
else.

## How the tokens are saved

1. **Implementation is delegated.** Production code is written by an
   Opus subagent in its own fresh context. Search runs, dead ends, file
   reads and test output land there, not in the orchestrator's window.
   The orchestrator receives a compact structured return: changed files,
   criteria met, decisions, risks. This is by far the largest effect.
2. **Contract handoffs instead of carried history.** Each delegation is
   a small self-contained commit contract. The codebase is not
   re-explained every round, and the orchestrator does not have to hold
   the implementation details of previous rounds to stay coherent.
3. **Index navigation instead of file dumps.** A code-intelligence index
   answers "where is this" and "what calls this" with targeted snippets,
   so full files are read only for the hunks that actually get reviewed.
4. **An evidence ledger instead of reconstruction.** Each commit leaves a
   compact structured record: contract hash, red proof, frozen test
   hash, test results, fingerprints. Later audits navigate that instead
   of re-reading old agent transcripts, which is the single most
   expensive way to remember something.
5. **Bounded repair loops.** At most two repairs per defect, then
   re-plan. An unbounded fix loop is the worst token sink in agentic
   development, because its context grows with every failed attempt and
   its chance of success falls at the same time.
6. **A fresh audit context.** Final acceptance runs in its own agent. It
   costs nothing from the main window and it is less anchored, since it
   never sees the "all done" summaries.
7. **Process state on disk.** Phases, fingerprints and evidence live in
   files. The orchestrator never has to hold or repeat them, and a
   compaction cannot lose them.

Those are the mechanisms. What they are actually worth was measured, and
the answer is smaller than the list makes it sound. See the next section.

## What it is worth, measured

The headline: on implementation-heavy work the delegated cycle spends
**28% fewer tokens on the expensive model**, at the same success rate.
Read as reach, the same measurement says the expensive model's budget
lasts **about 40% longer**. On a small, well-scoped fix it is slightly
worse than doing the work inline. And the total number of tokens goes up,
not down: delegation moves work to the cheaper model rather than removing
it.

Everything below is counted in tokens. Dollars are left out on purpose:
they depend on which models you pair and on cache pricing, and they made
a token claim look like a cost claim.

### Setup

Two arms run the same task with the same tools, the same effort level and
the same turn cap. The only difference is whether implementation is
delegated to a subagent. Success is a passing test suite, so a cheap
failure cannot be counted as a saving. Orchestrator: Claude Fable 5.
Implementer: Claude Opus 5. Effort `medium`. 16 runs, 4 per cell, all 16
successful, no cost-gate aborts. Cost is computed from the `usage` field
of every single response, not estimated.

Two tasks of the same kind and different size, chosen to sit on either
side of the break-even point:

- **small** (`duration`): write one new module against 11 failing tests.
- **large** (`feature`): write three new modules against 27 failing tests.

### Results

Large task, mean of 4 runs per arm:

| Measure (tokens) | inline | delegated | change |
|---|---|---|---|
| **on the expensive model, total** | **16,576** | **11,864** | **-28%** |
| of that, context re-sent | 14,596 | 10,607 | -27% |
| of that, output including thinking | 1,981 | 1,258 | -37% |
| context peak, single request | 4,136 | 3,706 | -10% |
| across both models | 16,576 | 22,632 | **+37%** |
| success | 4/4 | 4/4 | equal |

The ranges do not overlap on the headline measure, so the effect is not
noise. Note the last two rows together: the expensive model does 28% less
work, and the system as a whole does 37% more, because the implementer
starts cold and has to be briefed.

Small task, mean of 4 runs per arm:

| Measure (tokens) | inline | delegated | change |
|---|---|---|---|
| **on the expensive model, total** | **6,934** | **7,407** | **+7%** |
| of that, context re-sent | 6,126 | 6,636 | +8% |
| context peak, single request | 2,016 | 2,202 | +9% |
| across both models | 6,934 | 15,201 | **+119%** |
| success | 4/4 | 4/4 | equal |

Here delegation is simply worse, and the ranges are separated on that
too, so it is not noise either. The orchestrator still has to understand
the problem well enough to brief and to verify, so the briefing round
trip and the implementer's cold start are pure overhead. This matches the
skill's own rule: do not delegate work you could finish in a handful of
tool calls.

### Two things this does not say

**It does not say the workflow uses fewer tokens.** It uses more: 37%
more on the large task, 119% more on the small one. What drops is the
share carried by the expensive model. Read "saves" as "saves the scarce
allowance", never as "saves total consumption".

**It does not extrapolate.** The measured mechanism scales with the
number of implementer turns, and in these tasks that was three, so this
sits at the low end of where the effect exists at all. Whether it grows
with longer implementations is untested here. Only the 28% is evidence.

### Reproducing it

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...          # billed per token, no subscription credits
python3 bench/bench.py feature duration
```

All 16 runs cost $2.55 in total. The harness gates spend hard: it aborts
a single run at `PER_RUN_CAP` and the whole benchmark at `GLOBAL_CAP`, so
a runaway agent cannot empty the account. Raw per-run data, including
token counts and cost per model, is in `bench/results.json`; the method
and its limits are in `bench/README.md`.

## What you get on top: verification that does not depend on trust

Delegating implementation only works if acceptance is real. Agentic
coding tools fail in a specific, repeatable way: the agent that writes
the code is also the agent that decides whether the code is acceptable.
Under that arrangement the cheapest path to "done" is not always to make
the code correct.

- a test gets weakened, skipped, or its expectation rewritten,
- a test is red because of a broken import, the implementation fixes the
  import, and the actual behavior is never verified,
- the full suite passes, two more lines get changed, and the commit
  ships against a code state that was never tested,
- a repair loop runs forever because nobody decided when to stop
  patching and start re-planning,
- the final report says "all requirements met" because the tests are
  green, which only proves conformance with the tests.

Three roles remove the incentive structurally:

| Role | Owns |
|---|---|
| Orchestrator | requirements, commit contracts, acceptance tests, red proof, review, verification, staging, commits |
| Implementer (Opus subagent) | production code and repairs, nothing else |
| Checker agents (one fresh context per gate) | running the declared stage gates themselves; they never see implementer transcripts and never repair |
| Control agent (optional, larger plans) | reviewing a finished cycle against its contract before the block audit |
| Auditor (fresh context) | independent requirement-first completeness acceptance |

The rule that carries the whole thing: the agent that implements never
decides whether its own implementation is accepted.

### The cycle per commit

1. **Commit contract.** Small enough to stay atomic, independently
   checkable and revertible. Every acceptance criterion is traced back
   to its origin, so no criterion can be back-derived from code that
   already exists.
2. **Red phase, before any implementation.** The orchestrator writes the
   binding acceptance tests and proves they fail for the right reason.
   Three kinds of red are legitimate: *behavior red* for an interface
   that already exists, *contract red* for a symbol the contract
   deliberately introduces, where `ModuleNotFoundError` is the expected
   proof rather than a setup error, and *scenario red* for acceptance
   criteria written as Gherkin scenarios, where a failing step or a
   missing step definition is the proof and the `.feature` file is
   frozen together with its step skeletons as specification, not
   production code. Syntax errors, wrong import paths
   and broken fixtures are never valid red. This is why the orchestrator
   never has to write a production stub.
3. **Mechanical freeze.** The acceptance tests are staged and
   fingerprinted. Only the orchestrator touches the git index. A
   modified frozen test is detected by hash, not by someone noticing.
4. **Delegated implementation.** The subagent gets the contract, the
   provenance, the red proof, the expected change surface and the
   explicit non-goals.
5. **Verification gate.** Freeze check first, because a violation makes
   all further review worthless. Then targeted tests, a direct read of
   every changed hunk, a per-criterion proof, and a scope review.
6. **Bounded repair.** A precise defect contract goes back to the
   implementer. The full suite is not required on every iteration unless
   the repair touches shared core code, public interfaces, persistence,
   audit behavior, security boundaries or idempotency. After two failed
   repairs the commit goes back to planning instead of being patched
   again.
7. **Commit gate.** Full suite, complete diff reviewed, contract met, no
   scope creep, atomic and revertible. Then the commit.
8. **Requirement-first audit.** In a fresh context, without repair
   justifications or previous summaries. The auditor interprets the
   original requirements independently, runs the tests and demos itself,
   and grades each requirement as met and proven, partially met, not
   met, or not provable.

A green test run is necessary and not sufficient. The final claim is
never "the feature is correct" but "the feature demonstrably matches the
specified requirements, to the extent audit and verification cover
them".

## The whole harness on one page

Bottom line up front: this is a mechanically enforced
maker-checker-auditor workflow around every commit, with a recorded
self-triage in front of it. No model accepts its own work, and every
piece of evidence is bound to the exact code state instead of being
asserted. Everything below exists today; which parts have measured
value is stated further down, honestly.

**Decision layer**
1. Self-triage (Part 0 of the skill): solo, light or full, decided by
   the agent itself, always logged, overridable with a word.

**Specification layer**
2. Commit contracts with requirement provenance, so no acceptance
   criterion can be back-derived from code that already exists.
3. Red proof with three red kinds: behavior red, contract red, and
   scenario red (Gherkin feature files as frozen specification with
   step skeletons). The CLI refuses to record a red that exited 0.
4. Mechanical freeze of the acceptance tests by patch fingerprint,
   with a lint pass over the files before they freeze.

**Role separation**
5. The implementer (a delegated subagent in a fresh context) writes
   production code and nothing else: never stages, never commits,
   never touches frozen tests.
6. Checker agents, one fresh context per declared gate, run their
   check themselves and never repair.
7. A control agent on larger plans, and a requirement-first auditor in
   a fresh context that interprets the original requirements itself
   and never sees "all done" summaries.

**Stage gates, opt-in per contract**
8. Static analysis, quality ceilings (complexity and module size,
   built but unmeasured) and coverage with a mechanical threshold.
9. A mutation gate (kill-rate floor, evidence survives test-only
   edits) and a seed-enforced property gate. Both measured: each
   converts an occasional blind spot, neither earned its cost, so
   they belong on block-closing contracts of critical code only.

**Mechanical enforcement**
10. Hooks deny production edits without an active cycle or logged
    exemption, and `git commit` without a passed gate.
11. A content fingerprint binds all evidence to HEAD plus file
    contents: one edited line after verification invalidates the
    gate. One gate, exactly one commit.
12. A snapshot guard and bounded repair loops: two repairs per
    defect, then re-planning instead of an endless patch loop.
13. An evidence ledger entry per commit.

**The science layer behind the claims**
14. The numbers in this README come from a development benchmark:
    paired runs against hidden test suites the agent never sees, with
    reference and witness implementations proving each fixture can
    separate right from plausibly wrong, and decision rules registered
    before the first run.
15. The workflow improves itself only through a refinement loop of
    typed, judged, rollbackable proposals, in which a proposal that
    loosens any gate cannot even enter the ledger without declaring a
    measurement obligation. The loop's first round is on record,
    including one proposal its own judge rejected.

## Install

Requires Claude Code, Python 3.8 or newer, and git.

```bash
git clone https://github.com/BernhardJackiewicz/icca-harness.git
cd icca-harness
./install.sh
```

The installer copies the skill to `~/.claude/skills/`, the gate CLI to
`~/.claude/red-proof/`, and merges the two `PreToolUse` hooks into
`~/.claude/settings.json` after making a backup. It is idempotent.

Then add the block from `examples/CLAUDE.md.snippet` to your global
`~/.claude/CLAUDE.md`, so the skill is loaded before the first
production-code change instead of after it.

Verify in a fresh terminal: `/skills` lists the skill, `/hooks` shows
both gates.

## Usage

### What happens when you just ask for a change

You do not invoke any of this by hand. You state the task; the skill
loads because it is registered as the mandatory workflow; its Part 0
triage runs as the first step and the agent classifies the task
itself:

- **solo**: the agent records a logged exemption with a
  `triage: solo` reason and implements directly in the session.
- **light**: the agent runs the full cycle below (contract, red,
  freeze, delegated implementation, suites, diff review, commit gate)
  with no extra gates. This is the default for real work.
- **full**: only when the criteria demand it, the cycle additionally
  declares `--require` gates run by independent checker agents.

The classification is a logged judgment, not a classifier program:
every path leaves a record (an exemption line or a contract), the
hooks refuse production edits before one exists, and a word from you
("solo", "full cycle") overrides the triage. When the call is
genuinely borderline, the agent takes the higher tier: a too-careful
classification costs tokens, a too-loose one ships unchecked code.

### The gate CLI underneath

```bash
RP() { python3 ~/.claude/red-proof/red_proof.py "$@"; }

RP contract --file <contract.md>          # phase CONTRACT_CREATED, resets the cycle
RP red --test <name> --type contract|behavior --expected "<reason>" -- <testcmd>
git add <acceptance-tests> && RP freeze   # phase TESTS_FROZEN, patch fingerprint
# implementation happens in a delegated subagent here
RP check freeze
RP check targeted -- <testcmd>
RP check full-suite -- <suitecmd>
RP attest --diff-reviewed --contract-ok
RP commit-gate                            # binds all evidence to the current code state
git commit ...                            # allowed now, exactly one commit per gate
RP status                                 # phase, fingerprints, evidence
RP exempt --reason "<why>"                # classified exceptions only, logged
```

Note for zsh users: put the CLI in a shell function as shown. A variable
holding the command is not word-split.

## What is actually enforced

The distinction matters, so it is stated plainly.

**Instructed**, meaning the model can in principle deviate: everything
in the skill body. Contract quality, review depth, audit rigor.

**Enforced**, meaning a hook denies the tool call:

- production-code edits in a repository with no active cycle, or with
  the acceptance tests not yet frozen,
- `git commit` without a passed commit gate,
- `git commit` when the code changed after verification, because all
  evidence is bound to a content fingerprint (HEAD plus the content of
  every modified and untracked file). Staging does not change that
  fingerprint, so `git add` of reviewed production code is fine, while a
  single edited line invalidates the gate,
- a second commit on the same gate: one gate, one commit,
- any modification of a frozen acceptance test, detected by comparing
  the staged patch hash.

**Produced by the tool, not claimed by the model:** the red proof (the
CLI runs the command and refuses to record a red that exited 0), the
targeted and full-suite results, and the fingerprints. The only
model-attested items are `--diff-reviewed` and `--contract-ok`, because
reading a diff and checking a criterion cannot be delegated to a script.

## Stage gates in this repository

Beyond the base cycle, contracts can declare constraint gates with
`--require`. Each declared gate is run by an independent checker agent
with fresh context (see the skill, section 6.6) and recorded as
fingerprint-bound evidence. The reference tool choice for this
repository:

```
RP check static -- sh -c "ruff check bin/ bench/*.py && xenon --max-absolute C bin/"
RP check quality -- sh -c "xenon --max-absolute C --max-modules B --max-average A bin/ && python3 -c \"import pathlib, sys; big = [str(p) for p in pathlib.Path('bin').rglob('*.py') if len(p.read_text().splitlines()) > 1200]; sys.exit(1 if big else print('module sizes ok'))\""
RP check coverage --min 40 -- sh -c "python3 -m coverage run -m pytest -q tests/ && python3 -m coverage report --include='bin/red_proof.py'"
RP check mutation --min 80 -- sh -c "mutmut run && mutmut results"
RP check property -- python3 -m pytest -q tests/ --hypothesis-seed=1234
```

A failed check arms a worktree snapshot guard: rerunning the same
command on an unchanged tree does not execute it, the attempt still
counts (`contract --max-attempts`, default 5), and exhausting the budget
tells the cycle to stop repairing and re-plan. A corrected command does
run on that same tree, because a wrong command is repaired without
touching a file, and its failure counts on from the previous attempt.

`--min` applies to the gates whose number comes out of the run. The
property gate is not one of them: its metric is the seed the caller
passed in, and a threshold on an input grades the input instead of the
run, so `--min` on it is refused before anything is executed.

`quality` is the ceilings gate (complexity and module size), separate
from `static`, which carries the lint ruleset; a ceiling belongs in the
command, so the gate is exit-code gated and refuses `--min` like every
check without an extractor. The ceilings above are this repository's
honest current numbers: the worst block in `bin/` ranks C, the module
average ranks A, and the only module under `bin/` is 1072 lines against
the 1200-line cap.

Thresholds are set per contract, not globally: a cheap gate runs on
every declaring commit, an expensive one only on block-closing
contracts. Two honest notes on the numbers above. The complexity
ceiling is C because four long-standing blocks in the gate CLI sit
there today; tightening to B is a refactoring goal, not a claim. And
the coverage floor is 40 because the measured line coverage of
`bin/red_proof.py` is 43% today. That figure is low for a reason worth
knowing rather than hiding: `tests/` drives the CLI through
subprocesses, and line coverage does not see what runs in a child
process, so the suite is credited with far less than it actually
exercises. Both numbers are this project's choices at this point in its
life. They are not floors anyone else should adopt: pick thresholds
your own repository can meet honestly. The mutation and property lines
are tool-choice examples rather than gates this repository currently
meets: neither mutmut nor the hypothesis plugin is a dependency here,
so copy them only into a project that carries those tools.

One more honesty note, because this section would otherwise imply more
than was measured. Whether these gates pay for themselves has been
tested in a private development extension of this repository: a paired
benchmark against hidden test suites the agent never sees, under
pre-registered decision rules, nine registered hypotheses of which
eight carry verdicts. The short version is narrow. The stage-1 gate (visible suite plus coverage floor)
earned its accept only for a weak implementer model working from an
example-specified task, where it converts plausible near-misses into
hidden passes; the same gate showed no effect for frontier or mid-tier
implementers, and none when the task states its rules outright. The
mutation and property stages each converted an occasional blind spot of
the stage-1 gate but neither earned its cost under the registered
rules. The fix-shaped task class, long unmeasurable because the
default orchestrator refused at the sight of bug code, became
measurable under a recorded orchestrator choice and showed the same
picture: both arms hidden-green throughout, nothing for the gate to
convert. And on the small-task class, implementing directly in the
session lost no hidden passes against delegation at less than half
the median cost, which is why the skill now opens with a recorded
self-triage (Part 0: solo, light, full) instead of a blanket rule.
Treat the gates above as mechanisms with a narrow, measured
value window, not as universally paid-for protection, and expect their
main worth on real work to be the discipline they enforce rather than a
measured defect reduction.

## Tested and untested, in one place

Everything below was measured in the development benchmark: paired
runs against hidden test suites the agent never sees, decision rules
registered before the first run, every verdict re-derived by a fresh
context from the raw data.

Measured:

- **Delegation pays on implementation-heavy work, and only there.**
  28% fewer tokens on the expensive model at an identical success rate
  (16,576 to 11,864), while total tokens across both models rose 37%.
  On the small one-module task the same setup cost 7% more on the
  expensive model and 119% more in total.
- **Small, fully specified tasks do not need the harness.** Direct
  implementation in the session lost no hidden-suite passes against
  delegation over 12 pairs, at 0.45x the median cost, all runs
  hidden-green. This is the measured basis of the solo tier in the
  skill's Part 0.
- **The stage-1 gate has one narrow value window.** It converted
  plausible near-misses into hidden passes only for a weak implementer
  working from an example-specified task (net +4 over 25 pairs, 1.48x
  cost). With a frontier implementer: net 0. With a mid-tier
  implementer: net -1 over 12 pairs. On tasks that state their rules
  outright: all ties.
- **Mutation and property stages do not earn their cost.** Each
  converted an occasional blind spot the cheaper gates missed; the
  mutation stage did it at 3.08x the cost median against a registered
  2.0x limit, the property stage's evidence never left 1.5 against an
  accept threshold of 20 before the registered budget stop.
- **Fix-shaped tasks are solvable without a gate.** Once measurable
  under a recorded orchestrator choice (zero refusal aborts in 64
  runs), both arms were hidden-green throughout: 32 ties out of 32
  pairs, nothing for the gate to convert.

Not measured, stated as such:

- **The quality-ceilings gate.** Built and documented above; its
  hypothesis is registered but unfunded. Until measured it is a
  mechanism, not a claim.
- **The real Claude Code loop.** All numbers come from a harness that
  imitates the loop. Running the same tasks through real sessions on
  two separate keys would close the gap and has not been done.
- **Realistic repositories.** The benchmark runs on small synthetic
  packages; one brownfield fixture (a working multi-module package
  with a feature ask) exists as measurement surface and has not been
  measured on.
- **Dependency-structure and end-to-end stages.** Design documents
  only.
- **Field causality.** A descriptive field report can count cycles,
  gate runs and findings; whether the workflow reduces regressions in
  real work has no comparison arm and therefore no number. A
  prospective design exists on paper.
- **Transfer to other pairings.** The numbers are bound to the
  measured model pairs and to one developer's tasks and style. Other
  orchestrators and implementers, including local models, inherit the
  mechanics, not the numbers.

## Limits

Stated deliberately, because a workflow that overclaims is the thing
this repository argues against.

- The measured saving is 28% of expensive-model tokens on one task shape,
  from 16 runs on two synthetic tasks in throwaway repositories, driven by
  a harness that imitates the Claude Code loop rather than being it, at a
  fixed `medium` effort and with contexts under 5000 tokens. It is a
  first, narrow measurement, not a benchmark suite. Nothing in it supports
  a larger number, and it says nothing about total cost, which did not
  drop.
- The measurement ran through a harness that imitates the Claude Code
  loop rather than being it. Running the same tasks through real Claude
  Code sessions billed to two separate API keys would close that gap and
  has not been done.
- The hooks are process CI, not a security boundary. They fail open on
  internal errors and can be switched off locally by whoever owns the
  machine.
- Commits made from a plain terminal outside Claude Code are not gated.
  Add a `pre-commit` hook or CI if you need that.
- The commit gate has to decide which repository a shell command commits
  into, and it does that without a shell parser. It honors a leading
  `cd <dir>` and a `git -C <dir>` that belongs to the commit invocation
  itself. Everything else falls back to the reported working directory:
  a non-leading `cd` (`ls && cd other && git commit`), chained `cd`,
  subshells, variables or escaped spaces in the path, aliases, and
  environment-prefixed invocations. In those shapes a commit into a
  second repository is judged against the session repository, which can
  allow an ungated commit. Keep one repository per session, or add a
  `pre-commit` hook for a guarantee that does not depend on reading the
  command line.
- The attestation step remains model-attested.
- The method proves conformance with the specification that was checked.
  It does not prove the specification was right. A misunderstood
  requirement can be implemented perfectly and pass every gate. The
  requirement-first audit is the mitigation, not a guarantee.
- State is keyed per repository, not per session, so a delegated
  subagent and the orchestrator see the same gate.
- Tested on macOS. Path handling for temporary directories is
  POSIX-oriented.

## Repository layout

| Path | Purpose |
|---|---|
| `skills/icca-harness/SKILL.md` | the workflow as an installable Claude Code skill (English, default) |
| `skills/icca-harness/SKILL.de.md` | the same skill in German, the language it was written in |
| `bin/red_proof.py` | gate CLI and hook entry point, no dependencies |
| `examples/settings-hooks.json` | the hook block, for manual merging |
| `examples/CLAUDE.md.snippet` | the global instruction that triggers the skill |
| `tests/` | the gate CLI's own pytest suite, 324 tests covering the state machine, the checks, the fingerprints and the hooks |
| `test/smoke_test.sh` | 21 checks covering every deny path, the happy path and repository resolution |
| `install.sh` | idempotent installer with a settings backup |
| `bench/bench.py` | the paired benchmark, with hard cost gates |
| `bench/results.json` | raw per-run data for the 16 reported runs |
| `bench/README.md` | the method, and what it cannot tell you |

Two names, one thing: the skill and this repository are `icca-harness`,
after the four separated roles the method rests on (Implementer,
Checker, Control, Auditor) and the harness that keeps them apart; the
name is model-neutral on purpose, because the mechanics are. The
verification mechanism inside is called red-proof, after the
part of it that is unusual: it is not enough that tests exist, the red
itself has to be established as a valid proof before implementation
starts.

## Language

English is the default. The installer picks which skill body it writes:

```bash
./install.sh              # English (default)
./install.sh --lang de    # the German original
SKILL_LANG=de ./install.sh
```

Both files live in `skills/icca-harness/` as `SKILL.md` and
`SKILL.de.md`, and both carry the same English frontmatter description,
which is what triggers automatic loading, so auto-invocation behaves
identically either way. The German file is the original the method was
written in and is kept in sync rather than archived. Another language is
welcome as a pull request: add `SKILL.<code>.md` and one line to the
`case` in `install.sh`.

## License

MIT. See [LICENSE](LICENSE).
