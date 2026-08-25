# icca-harness

![version](https://img.shields.io/badge/version-1.0.0-blue)
![tests](https://img.shields.io/badge/tests-347%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-lightgrey)

**Get about 40% more out of an expensive-model subscription: on implementation-heavy work this workflow spends 28% fewer tokens on the expensive model, at an identical success rate.** The orchestrator's context holds decisions; the volume (implementation, search, test output, audit) runs in delegated or fresh contexts.

ICCA is an evidence-gated maker-checker-auditor workflow for agentic development. The name comes from the four separated roles that carry the method:

**Implementer · Checker · Control · Auditor**

The harness is the machinery around those roles, not an agent itself.

The central rule is simple:

> **The agent that implements never decides whether its own implementation is accepted.**

That separation does two things at once:

1. it keeps high-volume implementation work out of the scarce orchestrator context;
2. it makes delegation safe enough to use by binding acceptance evidence to the exact code state that was verified.

The first effect is measured. The second is mechanically enforced in the places where a script can enforce it, and explicitly model-attested where it cannot.

---

## The workflow at a glance

```text
                              the task
                                 |
                                 v
                Part 0 self-triage: solo | light | full
               (no harness / plain cycle / cycle + gates)
                                 |
                                 v
  +-----------------------------------------------------------------+
  |  ORCHESTRATOR                                                   |
  |  commit contract with requirement provenance; acceptance tests  |
  |  written FIRST and proven red (behavior red, contract red, or   |
  |  scenario red), then frozen by patch fingerprint so nobody can  |
  |  weaken them later                                              |
  +--------------------------------+--------------------------------+
                                   |
                         delegate, fresh context
                                   v
  +-----------------------------------------------------------------+
  |  I  IMPLEMENTER                                                 |
  |     the only role that writes production code                   |
  |                                                                 |
  |     never stages                                                |
  |     never commits                                               |
  |     cannot touch frozen tests                                   |
  |     never accepts its own work                                  |
  +--------------------------------+--------------------------------+
                                   |
                  the gauntlet: gates declared per contract
                                   |
                                   v
  +-----------------------------------------------------------------+
  |  C  CHECKER agents                                              |
  |     one fresh context per gate                                  |
  |     never see the implementer's transcript                      |
  |     never repair                                                |
  |                                                                 |
  |     unit tests + coverage        static analysis                |
  |     quality ceilings             mutation testing               |
  |     property tests               dependency structure           |
  |     e2e scenarios                                               |
  +--------------------------------+--------------------------------+
                                   |
          finding -> defect contract -> back to Implementer
          at most two repairs per defect, then re-planning
                                   |
                                   v
  +-----------------------------------------------------------------+
  |  C  CONTROL agent                                               |
  |     optional on larger plans                                    |
  |     checks the completed cycle against its contract             |
  |     fresh context                                               |
  +--------------------------------+--------------------------------+
                                   |
                                   v
         commit gate: evidence is fingerprint-bound to the exact
               code state; one gate, exactly one commit
                                   |
                                   v
  +-----------------------------------------------------------------+
  |  A  AUDITOR                                                     |
  |     fresh context                                               |
  |     interprets the original requirements independently         |
  |     runs tests and builds its own probes                        |
  |     never sees an "all done" summary                            |
  +-----------------------------------------------------------------+
```

---

## What the measurement actually says

On the larger, implementation-heavy benchmark task:

| Measure                           |     Inline |  Delegated |   Change |
| --------------------------------- | ---------: | ---------: | -------: |
| **Expensive-model tokens, total** | **16,576** | **11,864** | **-28%** |
| Context re-sent                   |     14,596 |     10,607 |     -27% |
| Output including thinking         |      1,981 |      1,258 |     -37% |
| Peak context, single request      |      4,136 |      3,706 |     -10% |
| **Tokens across both models**     | **16,576** | **22,632** | **+37%** |
| Success                           |        4/4 |        4/4 |    equal |

The same expensive-model allowance therefore lasts about **40% longer**:

`16,576 / 11,864 ≈ 1.40`

That does **not** mean the workflow uses fewer tokens overall. It does not.

Delegation moves volume away from the scarce model and onto the implementer model, while adding briefing and cold-start overhead.

On the small task, that overhead dominates:

| Measure                           |    Inline |  Delegated |    Change |
| --------------------------------- | --------: | ---------: | --------: |
| **Expensive-model tokens, total** | **6,934** |  **7,407** |   **+7%** |
| Context re-sent                   |     6,126 |      6,636 |       +8% |
| Peak context, single request      |     2,016 |      2,202 |       +9% |
| **Tokens across both models**     | **6,934** | **15,201** | **+119%** |
| Success                           |       4/4 |        4/4 |     equal |

So the measured rule is not “delegate everything.”

It is:

> **Delegate implementation-heavy work when the strongest model is the scarce resource. Do small, well-scoped work directly.**

Three limits belong next to the headline rather than in a footnote:

* **Total token consumption goes up.** On the large task it rose 37% across both models.
* **Delegation loses on small tasks.** The small benchmark used 7% more expensive-model tokens and 119% more total tokens.
* **The measurement is narrow.** It comes from small synthetic repositories, with contexts under 5,000 tokens, roughly five tool calls per run, not a large production codebase. The README also characterizes this scale as roughly $0.22 per run; the reproduced 16-run benchmark below reports $2.55 total across all runs.

Only the **28% reduction on the expensive model for the measured implementation-heavy task** is evidence for the headline. Everything beyond that is either mechanism, interpretation, or an explicitly untested hypothesis.

---

## Credits

This repository exists because of one tweet:

> I’m significantly older than you. I started coding in the late 60s. My
> current strategy is to not read any of the code written by my agents.
> That’s the only way I can take advantage of their productivity. What I
> do instead is to surround the agents with extreme constraints. Unit
> tests, gherkin tests, QA procedures, quality metrics, mutation
> testing, test coverage, and a plethora of others. In the end, I have
> very high confidence in the code they produce because they’ve had to
> run the gauntlet of all of my constraints and tests.
>
> [Uncle Bob Martin, @unclebobmartin, July 23, 2026](https://x.com/unclebobmartin/status/2080257779395154409)

Robert Cecil Martin (Uncle Bob), author of *Clean Code* and of the
[Agentic Manifesto](https://www.agenticmanifesto.org/), described the
gauntlet. This repository builds that gauntlet as enforceable machinery
(the gates above: unit tests, gherkin scenario reds, QA procedures as
e2e scenarios, quality metrics, mutation testing, coverage, dependency
structure) and then does the part the tweet leaves open: it measures,
gate by gate against hidden test suites, which parts of the gauntlet
earn their keep. One deliberate divergence is documented in the
evidence section below: here the orchestrator still reads every diff,
because the measured value window of the gates alone turned out to be
narrow.

---

## Why the context window is the scarce resource

The strongest model in a subscription is usually also the one whose allowance you exhaust first.

A default agentic loop spends that resource inefficiently: one model searches, reads, implements, retries, runs tests, consumes test output, summarizes its own previous work, and carries all of that history into the next turn.

Consider a single feature:

* locating the relevant code,
* opening files that turn out not to matter,
* failed implementation attempts,
* repeated test output,
* repair iterations,
* and summaries whose only purpose is preserving state for the next turn.

That can consume tens of thousands of tokens to support a decision whose durable information may fit in a few hundred.

Worse, the accumulated context is re-sent on later requests.

The fix is not merely a shorter prompt.

**The fix is to put the volume somewhere else while keeping decisions and contracts in the orchestrator.**

---

## How the expensive-model tokens are reduced

### 1. Delegate implementation

Production code is written by an Opus subagent in its own fresh context.

Search runs, dead ends, file reads, implementation attempts and test output stay there rather than accumulating in the orchestrator window.

The orchestrator receives a compact structured return:

* changed files,
* criteria met,
* decisions,
* risks.

This is the largest measured mechanism.

### 2. Hand off contracts, not conversation history

Each delegation receives a small, self-contained commit contract.

The codebase does not need to be re-explained every round, and the orchestrator does not need to retain every implementation detail from earlier rounds in order to remain coherent.

### 3. Navigate by index instead of dumping files

A code-intelligence index answers questions such as:

* where is this defined?
* what calls this?
* which files are relevant?

That lets the workflow read targeted snippets and inspect complete files only when review requires them.

### 4. Persist evidence instead of reconstructing history

Each commit leaves a compact structured record containing things such as:

* contract hash,
* red proof,
* frozen-test hash,
* test results,
* content fingerprints.

Later review can navigate this ledger instead of reconstructing state from old agent transcripts.

### 5. Bound repair loops

A defect gets at most two repair attempts before the workflow returns to planning.

Unbounded patch loops are expensive because every failure adds context while the probability that another blind patch succeeds may be falling.

### 6. Audit in a fresh context

Final acceptance runs in a separate agent context.

That keeps audit volume out of the orchestrator window and reduces anchoring because the auditor never receives previous “all done” summaries.

### 7. Keep process state on disk

Phases, fingerprints and evidence live in files.

The orchestrator does not need to continuously hold or restate that state, and context compaction cannot silently erase it.

---

# Evidence

## Benchmark setup

The headline measurement comes from **16 paired runs**, not an estimate.

Two arms run the same task with:

* the same tools,
* the same effort level,
* the same turn cap.

The only experimental difference is whether implementation happens inline or is delegated to a subagent.

**Orchestrator:** Claude Fable 5
**Implementer:** Claude Opus 5
**Effort:** `medium`
**Runs:** 16 total, 4 per cell
**Success:** all 16 runs successful
**Cost-gate aborts:** none

Success means the test suite passes, so a cheap failed run cannot count as a saving.

Token and cost data are read from the `usage` field of every response rather than inferred from text length.

The two tasks have the same general shape but different sizes:

* **small (`duration`)**: one new module against 11 failing tests;
* **large (`feature`)**: three new modules against 27 failing tests.

They were chosen to fall on opposite sides of delegation's break-even point.

Everything in the headline tables is expressed in **tokens**, not dollars. Dollar figures are deliberately not used for the token comparison because model pairing, output weighting and cache pricing can make a cost ratio look like a token ratio when they are not the same thing.

---

## Large task

Mean of four runs per arm:

| Measure                      |     Inline |  Delegated |   Change |
| ---------------------------- | ---------: | ---------: | -------: |
| **Expensive model, total**   | **16,576** | **11,864** | **-28%** |
| Context re-sent              |     14,596 |     10,607 |     -27% |
| Output including thinking    |      1,981 |      1,258 |     -37% |
| Context peak, single request |      4,136 |      3,706 |     -10% |
| **Across both models**       | **16,576** | **22,632** | **+37%** |
| Success                      |        4/4 |        4/4 |    equal |

The ranges do not overlap on the headline measure, so the measured difference is not explained by overlap between the observed ranges.

The two bold token rows matter together:

**the expensive model did 28% less work, while the system as a whole did 37% more.**

The additional total consumption comes from moving implementation into a second context that starts cold and must first be briefed.

---

## Small task

Mean of four runs per arm:

| Measure                      |    Inline |  Delegated |    Change |
| ---------------------------- | --------: | ---------: | --------: |
| **Expensive model, total**   | **6,934** |  **7,407** |   **+7%** |
| Context re-sent              |     6,126 |      6,636 |       +8% |
| Context peak, single request |     2,016 |      2,202 |       +9% |
| **Across both models**       | **6,934** | **15,201** | **+119%** |
| Success                      |       4/4 |        4/4 |     equal |

Here delegation is simply worse.

The observed ranges are separated here too.

The orchestrator still has to understand the problem well enough to specify and verify it, but delegation adds an implementer cold start and a briefing round trip. For work that can already be completed in a handful of tool calls, those costs are pure overhead.

That is why the workflow begins with self-triage instead of requiring delegation universally.

---

## What these results do not say

### They do not say the workflow uses fewer tokens

It uses more total tokens:

* **+37%** on the large task;
* **+119%** on the small task.

What drops in the successful large-task case is the amount carried by the expensive model.

Read “saves” as:

> **saves scarce expensive-model allowance**

not:

> **reduces total token consumption**

### They do not establish scaling behavior

The measured mechanism should depend on the amount of implementation work that can be moved out of the orchestrator context.

In these benchmark tasks the implementer used three turns, placing the experiment near the low end of where such an effect can appear at all.

Whether the advantage increases on substantially longer implementations is untested.

**Only the measured 28% is evidence.**

---

## Reproduce the benchmark

```bash
pip install anthropic
export ANTHROPIC_API_KEY=...          # billed per token, no subscription credits
python3 bench/bench.py feature duration
```

The 16 recorded runs cost **$2.55 total**.

The harness hard-limits spend:

* `PER_RUN_CAP` aborts an individual runaway run;
* `GLOBAL_CAP` aborts the benchmark as a whole.

Raw per-run model usage, token counts and costs live in:

```text
bench/results.json
```

The experimental method and its limitations are documented in:

```text
bench/README.md
```

---

# Why delegation needs independent verification

Moving implementation out of the orchestrator context creates a trust problem.

If the strongest model no longer reads every line while it is being written, the workflow needs another way to establish whether the returned result is acceptable.

Agentic coding also has a structural failure mode: the same agent often writes the implementation and then decides whether the implementation is good enough.

That arrangement creates shortcuts to “done” that are cheaper than actually satisfying the requirement:

* a test can be weakened, skipped or rewritten;
* a red test may be caused by a broken import, the import gets fixed, and the intended behavior is never demonstrated;
* the full suite can pass, followed by two untested edits before commit;
* a repair loop can continue indefinitely because no one decides when to stop patching;
* a final report can claim “all requirements met” merely because the tests are green, even though the tests may not cover the complete requirement.

ICCA separates those incentives structurally.

---

## Roles

| Role               | Owns                                                                                                |
| ------------------ | --------------------------------------------------------------------------------------------------- |
| **Orchestrator**   | requirements, commit contracts, acceptance tests, red proof, review, verification, staging, commits |
| **Implementer**    | production code and repairs, nothing else                                                           |
| **Checker agents** | executing declared stage gates in independent fresh contexts; never repair                          |
| **Control agent**  | optional review of a finished cycle against its contract on larger plans                            |
| **Auditor**        | independent, requirement-first completeness acceptance in a fresh context                           |

Checker agents never see the implementer's transcript.

The Auditor never receives an “all done” summary.

---

# The cycle per commit

## 1. Commit contract

Every cycle begins with a contract small enough to remain:

* atomic,
* independently checkable,
* revertible.

Each acceptance criterion carries requirement provenance so a criterion cannot be quietly back-derived from implementation that already exists.

---

## 2. Red before implementation

The orchestrator writes the binding acceptance tests **before production implementation** and proves that they fail for the intended reason.

Three forms of red are valid.

### Behavior red

An interface already exists, but its behavior does not yet satisfy the new contract.

### Contract red

The contract deliberately introduces a new symbol.

In that case a `ModuleNotFoundError` can be the expected proof rather than evidence that test setup is broken.

### Scenario red

An acceptance criterion is represented by a Gherkin scenario.

A failing step or missing step definition can constitute the red proof. The `.feature` file and its step skeletons are frozen as specification rather than treated as production implementation.

The following never count as valid red:

* syntax errors,
* incorrect import paths,
* broken fixtures.

Because contract red exists, the orchestrator does not need to create a fake production stub merely to make a test importable.

---

## 3. Mechanical freeze

Acceptance tests are staged and frozen by patch fingerprint.

Only the orchestrator touches the Git index.

If a frozen test changes later, the harness detects the changed hash mechanically rather than relying on someone noticing it during review.

---

## 4. Delegated implementation

The Implementer receives:

* the commit contract,
* requirement provenance,
* the red proof,
* expected change surface,
* explicit non-goals.

It writes production code.

It does not stage, commit, edit frozen acceptance tests or decide whether its work passes.

---

## 5. Verification gate

The first verification step is the freeze check.

If the acceptance contract changed, later review is meaningless.

After the freeze check:

1. targeted tests run;
2. every changed hunk is read directly;
3. each acceptance criterion receives a concrete proof;
4. scope is checked for unintended changes.

A green test suite alone is not sufficient.

---

## 6. Bounded repair

A finding becomes a precise defect contract and returns to the Implementer.

The full suite does not have to run on every repair iteration unless the repair touches:

* shared core code,
* public interfaces,
* persistence,
* audit behavior,
* security boundaries,
* idempotency.

After **two failed repairs for the same defect**, the commit returns to planning rather than entering an unlimited patch loop.

---

## 7. Commit gate

Before commit:

* full suite passes;
* complete diff has been reviewed;
* contract is met;
* no scope creep remains;
* the change is atomic and revertible.

All evidence is then bound to the current content fingerprint.

One passed gate authorizes **exactly one commit**.

---

## 8. Requirement-first audit

The final Auditor starts in a fresh context.

It does not receive implementation justifications, repair history or prior completion summaries.

Instead it independently interprets the original requirements, runs tests and demos itself, creates its own probes, and grades every requirement as:

* met and proven;
* partially met;
* not met;
* not provable.

The final claim is therefore not:

> “the feature is correct”

but:

> **the feature demonstrably matches the specified requirements, to the extent covered by the recorded verification and audit.**

---

# The whole harness on one page

Everything below exists today. Whether each mechanism has measured value is separated explicitly from whether it is implemented.

## Decision layer

### Self-triage

Part 0 classifies the task as:

* `solo`
* `light`
* `full`

The agent makes the judgment itself, records it, and the user can override it explicitly.

---

## Specification layer

### Commit contracts

Every criterion carries requirement provenance.

### Red proof

Three supported forms:

* behavior red;
* contract red;
* scenario red.

The CLI refuses to record a red run whose command exited `0`.

### Frozen acceptance specification

Acceptance tests are patch-fingerprinted before implementation.

Gherkin `.feature` files and their step skeletons can participate in the frozen specification.

---

## Role-separation layer

### Implementer

A delegated fresh-context agent writes production code and repairs only.

It never:

* stages;
* commits;
* touches frozen tests;
* accepts itself.

### Checker

Each declared gate runs in its own fresh Checker context.

Checkers execute the check themselves, never repair, and never see Implementer transcripts.

### Control

Optional on larger plans.

Reviews the completed cycle against the contract before block-level audit.

### Auditor

Fresh, requirement-first context.

Never sees “all done” summaries.

---

## Stage-gate layer

Contracts can opt into:

* static analysis;
* quality ceilings;
* coverage;
* mutation testing;
* seed-pinned property testing;
* dependency-structure checks;
* end-to-end scenario checks.

Their evidence status differs; see **Evidence status** below.

---

## Mechanical-enforcement layer

Hooks deny:

* production edits before a cycle or logged exemption exists;
* commits without a passed commit gate;
* commits after verified content changes;
* reuse of one gate for multiple commits;
* modification of frozen acceptance tests.

A content fingerprint binds evidence to:

* `HEAD`;
* the contents of every modified file;
* the contents of every untracked file.

Staging reviewed production code does not alter that fingerprint.

Editing one byte of verified content does.

There is also:

* a worktree snapshot guard;
* bounded repair attempts;
* one evidence-ledger entry per commit.

---

## Science layer

The reported benchmark uses:

* paired runs;
* hidden test suites the agent never sees;
* reference and witness implementations proving fixtures distinguish correct from plausibly incorrect behavior;
* decision rules registered before the first run.

Benchmark verdicts are re-derived from raw data by a fresh context.

The workflow's own refinement process uses typed, judged and rollbackable proposals.

A proposal that weakens a gate cannot enter the refinement ledger without declaring a measurement obligation.

The first refinement round is on record, including a proposal rejected by its own judge.

---

# Install

Requires:

* Claude Code;
* Python 3.8 or newer;
* Git.

```bash
git clone https://github.com/BernhardJackiewicz/icca-harness.git
cd icca-harness
./install.sh
```

The installer:

* copies the skill into `~/.claude/skills/`;
* copies the gate CLI into `~/.claude/red-proof/`;
* merges two `PreToolUse` hooks into `~/.claude/settings.json`;
* creates a settings backup first.

It is idempotent.

Then add the contents of:

```text
examples/CLAUDE.md.snippet
```

to the global:

```text
~/.claude/CLAUDE.md
```

That makes the workflow load before the first production-code edit rather than after it.

Verify from a fresh terminal:

```text
/skills
/hooks
```

`/skills` should list the installed skill and `/hooks` should show both gates.

---

# Usage

## What happens when you simply ask for a change

You do not manually invoke the workflow for normal work.

State the task.

The registered skill loads and Part 0 performs self-triage.

### `solo`

For a genuinely small task, the agent records a logged exemption such as:

```text
triage: solo
```

and implements directly in the current session.

### `light`

Runs the core cycle:

```text
contract
-> red
-> freeze
-> delegated implementation
-> verification
-> suites
-> diff review
-> commit gate
```

No additional stage gates are required.

This is the default for substantial ordinary work.

### `full`

Uses the same core cycle but additionally declares `--require` gates when the contract justifies them.

The triage is a logged judgment, not a separate classifier program.

Every path leaves evidence:

* an exemption line; or
* an active contract.

Hooks refuse production-code changes before one exists.

A user can override the judgment with instructions such as:

```text
solo
full cycle
```

When classification is genuinely borderline, the workflow chooses the higher tier:

a too-careful classification costs tokens; a too-loose classification can ship unchecked code.

---

# Gate CLI

A typical cycle looks like this:

```bash
RP() { python3 ~/.claude/red-proof/red_proof.py "$@"; }

RP contract --file <contract.md>
RP red --test <name> --type contract|behavior --expected "<reason>" -- <testcmd>

git add <acceptance-tests>
RP freeze

# delegated implementation

RP check freeze
RP check targeted -- <testcmd>
RP check full-suite -- <suitecmd>

RP attest --diff-reviewed --contract-ok
RP commit-gate

git commit ...

RP status
RP exempt --reason "<why>"
```

`RP contract` creates `CONTRACT_CREATED` and resets the cycle.

`RP freeze` moves the acceptance specification into the frozen phase.

`RP commit-gate` binds all accumulated evidence to the current code state.

Exactly one commit can consume a gate.

### zsh note

Use a shell function as shown above.

A variable containing the command is not word-split by zsh in the same way.

---

# What is actually enforced

The distinction between instructions and mechanical guarantees matters.

## Instructed

These depend on model behavior and can in principle be violated:

* contract quality;
* review depth;
* requirement interpretation;
* audit rigor.

---

## Mechanically enforced

A hook denies the tool call when:

* production code is edited in a repository with neither an active cycle nor logged exemption;
* production code is edited before the acceptance tests are frozen;
* `git commit` is attempted without a passed commit gate;
* `git commit` is attempted after the verified code state changed;
* a second commit attempts to reuse the same passed gate;
* a frozen acceptance test was modified.

Frozen-test integrity is checked through its staged patch hash.

Commit evidence uses a broader content fingerprint covering `HEAD` plus every modified and untracked file.

That distinction lets `git add` stage already-reviewed production code without invalidating evidence while still causing an actual content edit to invalidate the gate.

---

## Produced by the tool, not merely claimed

The CLI itself produces:

* red-proof command result;
* targeted-test result;
* full-suite result;
* content fingerprints.

It refuses to record red proof when the red command exits successfully.

Two parts remain model-attested:

```text
--diff-reviewed
--contract-ok
```

A script can run a test or hash files.

It cannot determine whether a human-language requirement was interpreted correctly or whether a diff was reviewed intelligently.

---

# Stage gates

Beyond the base cycle, a contract can declare optional constraints through `--require`.

Each declared gate is executed by an independent Checker agent in a fresh context and recorded as fingerprint-bound evidence.

For this repository, the reference commands are:

```bash
RP check static -- sh -c \
  "ruff check bin/ bench/*.py && xenon --max-absolute C bin/"

RP check quality -- sh -c \
  "xenon --max-absolute C --max-modules B --max-average A bin/ && \
   python3 -c \"import pathlib, sys; big = [str(p) for p in pathlib.Path('bin').rglob('*.py') if len(p.read_text().splitlines()) > 1200]; sys.exit(1 if big else print('module sizes ok'))\""

RP check deps -- sh -c \
  "python3 tools/deps_check.py --policy deps-policy.json"

RP check e2e -- sh -c \
  "python3 tools/run_scenarios.py --config e2e-scenarios.json"

RP check coverage --min 40 -- sh -c \
  "python3 -m coverage run -m pytest -q tests/ && \
   python3 -m coverage report --include='bin/red_proof.py'"

RP check mutation --min 80 -- sh -c \
  "mutmut run && mutmut results"

RP check property -- \
  python3 -m pytest -q tests/ --hypothesis-seed=1234
```

---

## Failed-check snapshot guard

A failed check arms a worktree snapshot guard.

If the exact same command is rerun against an unchanged tree, the command does not execute again.

The attempt still counts against the contract's attempt budget:

```text
contract --max-attempts
```

Default:

```text
5
```

Exhausting that budget tells the cycle to stop repairing and return to planning.

A corrected command is allowed to execute against the same tree because repairing an incorrect check command should not require a code edit.

Its attempt count continues from the previous failure.

---

## Threshold semantics

`--min` only applies to gates whose executed result emits a meaningful measured value.

### Property gate

The property gate's recorded metric is the random seed supplied by the caller.

A threshold on that input would grade the input rather than the execution, so `--min` is rejected before execution.

### Quality gate

`quality` is a ceilings gate.

Limits such as complexity and module size belong inside the invoked command.

It therefore behaves as an exit-code gate and rejects `--min`.

### Static gate

`static` is separate from `quality` and carries the lint/static-analysis ruleset.

---

## Repository-specific thresholds

The example thresholds above describe this repository's current state, not universal recommendations.

The complexity ceiling is currently **C** because four long-standing blocks in the gate CLI rank C.

Moving them to B is a refactoring target, not a claim about today's code.

The module average ranks **A**.

The only module under `bin/` is currently **1,072 lines**, under the declared **1,200-line** ceiling.

The coverage floor is currently **40%**.

Measured line coverage for `bin/red_proof.py` is **43%**.

That apparently low number has a specific cause: `tests/` drives much of the CLI through subprocesses, while the line-coverage process does not observe execution inside the child process. The recorded line-coverage percentage therefore credits less execution than the test suite actually performs.

These numbers are project-specific.

Do not copy them blindly into another repository.

The mutation and property commands are examples of tool choices rather than gates this repository currently satisfies: neither `mutmut` nor the Hypothesis plugin is a dependency here.

---

## Dependency and end-to-end gates

`deps` and `e2e` are the two newest optional stages.

Both are:

* built;
* tested;
* unmeasured.

Neither currently carries a claim that it pays for itself.

### `deps`

Checks the import graph of first-party code against a declared dependency policy:

* no cycles;
* only permitted layering.

It is deliberately an exit-code gate.

A violation count has no useful floor semantics.

### `e2e`

Runs the wired artifact through its declared entry point rather than only exercising isolated units.

It is also an exit-code gate.

A partially passing scenario set is still a failed scenario run, so there is no meaningful `--min` threshold to grade.

The CLI executes the command supplied by the project; the actual dependency and scenario checks live in project-specific tools.

Thresholds are declared per contract rather than globally.

Cheap checks can run on every declaring commit.

Expensive checks belong on contracts whose risk justifies them, especially block-closing changes to critical code.

---

# Evidence status

Implemented does not mean validated.

This section separates what the development benchmark has actually measured from what merely exists as a mechanism.

The development benchmark uses paired runs against hidden suites that the agent never sees, with decision rules registered before the first run.

A fresh context re-derived every reported verdict from the raw data.

## Measured

### Delegation pays on implementation-heavy work, and only there

Large task:

* expensive-model tokens: **16,576 → 11,864**
* change: **-28%**
* success: identical
* total tokens across both models: **+37%**

Small task:

* expensive-model tokens: **+7%**
* total tokens: **+119%**

---

### Small, fully specified tasks do not need the harness

Direct implementation in the session lost no hidden-suite passes against delegation across **12 pairs**.

All runs were hidden-green.

Direct implementation used **0.45× the median cost**.

That is the measured basis for the `solo` tier in Part 0.

---

### The stage-1 gate has one narrow measured value window

The stage-1 gate is the visible suite plus coverage floor.

For a **weak implementer** working from an **example-specified task**, it converted plausible near-misses into hidden-suite passes:

* **net +4 over 25 pairs**
* **1.48× cost**

For a **frontier implementer**:

* net effect: **0**

For a **mid-tier implementer**:

* **net -1 over 12 pairs**

When the task states its rules explicitly:

* all comparisons tied.

So the gate has not demonstrated broad value across implementers and task specifications.

---

### Mutation and property stages did not earn their cost

Each gate caught an occasional blind spot that the cheaper stage-1 gate missed.

Neither met its registered value criterion.

Mutation:

* median cost: **3.08×**
* registered limit: **2.0×**

Property stage:

* evidence never exceeded **1.5**
* accept threshold: **20**
* measurement stopped at the registered budget stop.

---

### Fix-shaped tasks were solvable without the gate

The fix-shaped class had previously been difficult to measure because the default orchestrator refused when presented with bug code.

Under a recorded orchestrator choice, the class became measurable:

* **0 refusal aborts across 64 runs**
* **32 pairs**
* both arms hidden-green in all pairs
* **32 ties out of 32**

There was therefore no failure for the gate to convert.

---

## Development-extension summary

The private development extension registered **nine hypotheses**, of which **eight currently have verdicts**.

Its narrow conclusion is:

* stage 1 helps only in the measured weak-implementer/example-specified window;
* no effect was found for the frontier implementer;
* the mid-tier comparison was slightly negative;
* explicitly specified tasks produced ties;
* mutation and property checks found occasional additional defects but failed their cost/value rules;
* the measurable fix-shaped tasks stayed hidden-green in both arms;
* small direct tasks were cheaper without losing hidden passes.

The gates should therefore be treated as **mechanisms with a narrow demonstrated value window**, not as universally cost-effective defect reducers.

Their broader practical value may be the discipline they enforce, but that has not been established as a causal benchmark result.

---

## Built but not measured

### Quality-ceilings gate

Implemented and documented.

Its hypothesis is registered but unfunded.

Until measured, it is a mechanism rather than an evidence-backed claim.

### Dependency-structure gate

Built and tested.

The development benchmark contains:

* runners;
* arms;
* observing after-measures;
* preregistered start criteria;
* held-in fixtures;
* held-out fixtures;
* reference overlays;
* witness overlays.

No model has yet been run against it and no hypothesis is registered.

### End-to-end scenario gate

The same status as the dependency gate:

* built;
* tested;
* benchmark surface exists;
* not yet measured;
* no registered hypothesis.

### Real Claude Code loop

The reported numbers come from a benchmark harness that **imitates** the Claude Code loop.

The equivalent tasks have not yet been run through real Claude Code sessions billed to two separate API keys.

### Realistic repositories

The benchmark uses small synthetic packages.

A brownfield fixture exists: a working multi-module package with a feature request.

It has not yet been measured.

### Field causality

A field report could count:

* cycles;
* gate executions;
* findings.

But without a comparison arm it cannot establish whether the workflow reduces regressions.

A prospective design exists on paper; no causal number is claimed.

### Transfer to other model pairings

The measured numbers belong to the tested model pairs, task shapes and one developer's style.

Other orchestrators, implementers or local models inherit the mechanics.

They do **not** inherit the 28% result.

---

# Limits

The limits are intentionally explicit because a workflow about evidence should not overstate its own evidence.

### Narrow benchmark

The 28% reduction was measured on:

* one implementation-heavy task shape;
* 16 runs across two synthetic tasks;
* throwaway repositories;
* fixed `medium` effort;
* contexts below 5,000 tokens;
* a harness that imitates the Claude Code interaction loop.

It is a first narrow measurement, not a benchmark suite.

Nothing in the data supports a larger claimed number.

It also does not show a reduction in total token consumption.

---

### Harness versus real Claude Code

The experiment uses a harness that imitates the Claude Code loop.

Running equivalent tasks through actual Claude Code sessions using two separately billed API keys would reduce that external-validity gap.

That experiment has not been done.

---

### Hooks are process CI, not a security boundary

The hooks:

* fail open on internal errors;
* can be disabled locally by the machine owner.

They enforce workflow discipline, not adversarial security.

---

### Plain-terminal commits are outside the Claude Code gate

A commit performed from an ordinary terminal outside Claude Code is not intercepted by this workflow.

If the repository requires enforcement independent of the Claude Code session, add:

* a `pre-commit` hook;
* CI;
* or both.

---

### Repository resolution has parsing limits

The commit gate must determine which repository a shell command will commit into without implementing a full shell parser.

It understands:

```text
cd <dir> ...
```

when the `cd` is leading, and:

```text
git -C <dir> commit ...
```

when `-C` belongs to the commit invocation.

Other forms fall back to the working directory reported by the session.

Examples that are not fully interpreted include:

```text
ls && cd other && git commit
```

as well as:

* chained `cd` commands;
* subshells;
* path variables;
* escaped spaces in paths;
* aliases;
* environment-prefixed invocations.

In those shapes, a commit targeting a second repository can be judged against the session repository and can therefore allow an ungated commit.

Keep one repository per session, or add a repository-native `pre-commit` hook if you need a guarantee that does not depend on interpreting the shell command.

---

### Attestation remains model-attested

The harness can prove that commands ran and content hashes matched.

It cannot mechanically prove that:

```text
--diff-reviewed
--contract-ok
```

were judged correctly.

---

### Specification correctness is outside the proof

The method proves conformance with the specification that was checked.

It does not prove that the specification itself was correct.

A misunderstood requirement can be implemented perfectly and pass every gate.

The requirement-first Auditor mitigates that failure mode.

It does not eliminate it.

---

### State is repository-scoped

Workflow state is keyed by repository rather than Claude Code session.

That is intentional: a delegated Implementer and the Orchestrator must see the same gate state.

---

### Platform coverage

The harness has been tested on macOS.

Temporary-directory path handling is POSIX-oriented.

---

# Repository layout

| Path                              | Purpose                                                                 |
| --------------------------------- | ----------------------------------------------------------------------- |
| `skills/icca-harness/SKILL.md`    | installable Claude Code workflow, English default                       |
| `skills/icca-harness/SKILL.de.md` | synchronized German original                                            |
| `bin/red_proof.py`                | dependency-free gate CLI and hook entry point                           |
| `examples/settings-hooks.json`    | hook configuration for manual merging                                   |
| `examples/CLAUDE.md.snippet`      | global instruction that triggers the skill                              |
| `tests/`                          | 347 pytest tests covering state machine, checks, fingerprints and hooks |
| `test/smoke_test.sh`              | 21 checks covering deny paths, happy path and repository resolution     |
| `install.sh`                      | idempotent installer with settings backup                               |
| `bench/bench.py`                  | paired benchmark with hard spend limits                                 |
| `bench/results.json`              | raw data for the 16 headline runs                                       |
| `bench/README.md`                 | benchmark method and limitations                                        |

---

# Naming

The repository and installable skill are both called:

```text
icca-harness
```

ICCA refers to the four separated roles:

```text
Implementer
Checker
Control
Auditor
```

The name is deliberately model-neutral because the separation mechanics are model-neutral.

The verification mechanism inside the harness is called:

```text
red-proof
```

The unusual part is the requirement that red itself be established as valid evidence before implementation begins.

It is not enough for acceptance tests merely to exist.

---

# Language

English is the default install language.

```bash
./install.sh
./install.sh --lang de
SKILL_LANG=de ./install.sh
```

Both language versions live in:

```text
skills/icca-harness/
```

as:

```text
SKILL.md
SKILL.de.md
```

Both use the same English frontmatter description, so automatic invocation behaves the same way regardless of which body is installed.

The German file is the original language in which the method was written and is maintained in sync rather than archived.

Additional languages are welcome as pull requests:

```text
SKILL.<code>.md
```

plus the corresponding entry in the `case` statement in `install.sh`.

---

# License

MIT. See `LICENSE`.
