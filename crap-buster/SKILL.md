---
name: crap-buster
description: Run a full code-hardening pass on a Java/Spring Boot project — measure coverage with JaCoCo, generate tests to close gaps, run PIT mutation testing to verify real coverage, write tests to kill surviving mutants, drive down cyclomatic complexity via refactors, and report CRAP-score deltas. Use this skill whenever the user is in a Java/Maven/Gradle project and asks for a "quality pass", "test hardening", "coverage sweep", "mutation testing", wants to run "crap-buster" or "bob-mode" explicitly, is preparing for a production release on a Spring Boot API, or mentions they want to systematically improve code quality before shipping. Also trigger on phrases like "harden this before we ship", "raise test coverage and actually verify it", "make the tests more rigorous", "drive down the CRAP score", or "refactor the complex methods and cover them". Assumes a green-test baseline, Java + Maven or Gradle, and JUnit 4/5 tests.
---

# crap-buster

An on-demand, autonomous code-hardening pass for Java/Spring Boot projects, following the workflow Uncle Bob Martin described in his 2026-04-20 "Morning Bathrobe Rant": stop writing code by hand, start directing AI with *hard quality gates* — coverage, mutation testing, CRAP score — and keep looping until the code is measurably cleaner.

## Philosophy

Coverage alone is a lie — it only proves code executed, not that it's verified. The fix is mutation testing: deliberately break the source, rerun tests, and for every mutation the tests fail to catch, write a test that does. Then attack complexity: decompose the methods that sit high on the CRAP curve (coverage × complexity) into small, individually covered units. Repeat until the CRAP distribution collapses.

The human doesn't write any of this. The human kicks off the skill, goes home, reviews the PR.

## When to run this

Good fits:
- "End of the week, run the quality sweep."
- "We ship Monday — harden the service layer."
- A new module just landed and you want to make sure it's covered *for real*.

Bad fits — refuse and explain:
- Working tree is dirty. Require a clean working tree before starting; the skill makes many commits and needs unambiguous attribution.
- Test suite is red at baseline. The skill can't tell regressions from pre-existing failures.
- Not a Java project, or no Maven `pom.xml` / Gradle `build.gradle*` found.

## Configuration

On first run in a project, copy `config/crap-buster.yml` (inside this skill) to `.crap-buster.yml` at the project root and commit it as a chore. On subsequent runs, read `.crap-buster.yml` for overrides. Key knobs:

- `crap.target` (default 10) — aim every method below this.
- `crap.hard_ceiling` (default 30) — methods above this are highest priority.
- `coverage.line_target` (default 0.85)
- `mutation.score_target` (default 0.75)
- `mutation.regression_tolerance` (default 2) — refactor reverts if class mutation score drops more than this many points.
- `mutation.scope` (default `full`) — `full` or `changed-since:<ref>`.
- `time_budget_minutes` (default 180) — hard stop; phases time-budget themselves proportionally.
- `exclude` — globs and packages to skip (DTOs, generated code, `*Application.java`, etc.)

## Phases

Run strictly in order. Each phase must finish successfully before the next starts. After every phase, commit and keep the branch pushable.

### Phase 0 — Preflight

Read `.crap-buster.yml` if present, else use defaults and offer to create one.

Run `scripts/detect_build.py` — it reports build tool (Maven vs. Gradle), Spring Boot version, presence of JaCoCo plugin, presence of PIT plugin, Java version, Lombok presence.

Verify the working tree is clean (`git status --porcelain` empty). Abort with a clear message if not.

Run the full test suite. Abort if anything fails.

If JaCoCo plugin is missing, add it. See `references/jacoco-setup.md` for the Maven and Gradle snippets. If Lombok is detected, ensure `lombok.config` has `lombok.addLombokGeneratedAnnotation = true` so JaCoCo skips Lombok boilerplate (add it if missing). Commit: `chore: add jacoco plugin for crap-buster`.

If PIT plugin is missing, add it. See `references/pit-setup.md`. Commit: `chore: add pitest plugin for crap-buster`.

Create a working branch: `quality/crap-buster-YYYYMMDD`. All further commits land on this branch.

### Phase 1 — Baseline

Run the coverage build: `mvn test jacoco:report` (Maven) or `./gradlew test jacocoTestReport` (Gradle).

Run `scripts/crap.py --input target/site/jacoco/jacoco.xml --out docs/quality/baseline-<DATE>.md --json docs/quality/baseline-<DATE>.json`. The script computes CRAP per method using `CRAP(m) = comp² + comp² × (1 − cov)³` and emits both a human-readable Markdown table and a machine-readable JSON snapshot.

Commit: `docs(quality): baseline snapshot`.

### Phase 2 — Cover

Goal: raise line coverage and kill the easy CRAP wins (methods with high complexity but near-zero coverage).

Load the JSON from Phase 1. Filter methods where `coverage < 1.0` AND `crap > config.crap.target`. Sort descending by CRAP. Skip anything matching `config.exclude`.

For each method, read `prompts/generate-test-for-method.md` and follow it. That prompt knows about Spring test slices (`@WebMvcTest`, `@DataJpaTest`, `@SpringBootTest` sparingly) and about Mockito idioms. Write the new tests into the existing test class if present, or create a mirror class in `src/test/java`.

After writing each test class, run *only that class* first (`mvn -Dtest=ClassNameTest test`), then run the full suite. If the full suite is red, fix or revert. Only commit green.

Commit granularity: one commit per class exercised: `test: cover ClassName`. Include in the body which methods were targeted and the coverage delta.

Stopping condition for this phase: every non-excluded method has coverage ≥ `config.coverage.line_target`, or the phase's time budget (30% of total) is exhausted, whichever first.

### Phase 3 — Mutate

Goal: prove the coverage is real. Coverage that can't detect deliberate source bugs is theater.

Run PIT scoped according to `config.mutation.scope`. For Maven with full scope: `mvn org.pitest:pitest-maven:mutationCoverage -DoutputFormats=HTML,XML`. For `changed-since` scope, pass `-DtargetClasses=...` with the class globs derived from `git diff --name-only <ref>`.

Run `scripts/mutant_gaps.py --input target/pit-reports/<latest>/mutations.xml --out docs/quality/surviving-mutants-<DATE>.md --json docs/quality/surviving-mutants-<DATE>.json`. This lists every surviving mutant grouped by class and method, with the mutation description (e.g., "negate conditional at line 42") and the source excerpt.

For each surviving mutant, read `prompts/kill-mutant.md` and follow it. The prompt's core idea: write a test that asserts a specific observable output for a specific input that *would differ* under the mutation. Run the test against the current (un-mutated) source — it should pass. Run PIT scoped to that class — the mutant should now be killed.

Commit per class: `test(mutation): kill <N> surviving mutants in ClassName`.

Stopping condition: class mutation score ≥ `config.mutation.score_target` for every non-excluded class, or the phase's time budget (40% of total) is exhausted.

### Phase 4 — Decompose

Goal: reduce complexity where CRAP is still high because of cyclomatic complexity, not coverage.

Re-run `scripts/crap.py` against the latest JaCoCo XML to get the current CRAP map. Filter methods where `crap > config.crap.target` AND `coverage ≥ 0.9`. These are the "well-tested but too complex" methods.

For each, read `prompts/refactor-for-complexity.md`. The prompt describes safe refactors — extract method, replace conditional with polymorphism, early-return guard clauses, replace magic numbers with named constants — and requires that the refactor be *behavior-preserving*.

**Non-negotiable gates after every refactor:**
1. Full test suite green.
2. Class mutation score after refactor ≥ class mutation score before refactor minus `config.mutation.regression_tolerance`.

If either gate fails, revert the refactor with `git reset --hard HEAD` and skip to the next method. Note the skip in the report.

Commit per method: `refactor: decompose ClassName.methodName (CRAP <before> → <after>)`.

Stopping condition: every non-excluded method has `crap ≤ config.crap.target`, or the phase's time budget (20% of total) is exhausted.

### Phase 5 — Report and open PR

Run `mvn test jacoco:report` and PIT one final time (scoped to changed classes — full is redundant).

Run `scripts/crap.py --input target/site/jacoco/jacoco.xml --out docs/quality/report-<DATE>.md --json docs/quality/report-<DATE>.json --compare docs/quality/baseline-<DATE>.json`. The compare flag produces a diff: CRAP histogram before vs. after, methods moved above/below threshold, coverage delta, any methods excluded or skipped and why.

Append mutation-score deltas from `scripts/mutant_gaps.py --compare`.

Commit: `docs(quality): final report for crap-buster-<DATE>`.

Push the branch: `git push -u origin quality/crap-buster-<DATE>`.

If `gh` CLI is available: `gh pr create --title "Quality pass <DATE> — crap-buster" --body-file docs/quality/report-<DATE>.md`. Otherwise print the compare URL for the user.

End with a one-screen summary in the chat: coverage before/after, mutation score before/after, CRAP distribution shift, PR link.

## Safety invariants

These hold across every phase. If any is violated, stop the run and print a postmortem — don't try to recover.

1. **Never on `main`.** All work is on `quality/crap-buster-<DATE>`.
2. **Never commit red.** Every commit must have `mvn test` (or `./gradlew test`) passing. For Phase 2–3 test-only commits this is trivial; for Phase 4 refactor commits it's the non-negotiable gate.
3. **Mutation score never regresses** beyond `config.mutation.regression_tolerance` on any class touched during Phase 4. This is what prevents "refactored it, tests still pass, but the tests got weaker."
4. **Only one build-file `chore:` commit in Phase 0.** The skill touches `pom.xml` / `build.gradle` exactly once per run (plugin additions if missing) and never again.
5. **Respect `.crap-buster.yml` `exclude`.** Never write tests for, or refactor, anything on the exclusion list — even if the CRAP score says to.
6. **Time budgets are hard stops.** When a phase's budget is exhausted, commit whatever work is done, record the stop in the phase notes, and move to the next phase. Don't silently over-run.

## What the skill ships

```
crap-buster/
├── SKILL.md                             — this file
├── config/
│   └── crap-buster.yml                  — config template copied into projects as .crap-buster.yml
├── scripts/
│   ├── detect_build.py                  — Maven vs. Gradle + plugin/Spring/Lombok detection
│   ├── crap.py                          — JaCoCo XML → CRAP per-method table (Markdown + JSON)
│   └── mutant_gaps.py                   — PIT mutations.xml → surviving-mutant table
├── prompts/
│   ├── generate-test-for-method.md      — load in Phase 2 for each uncovered method
│   ├── kill-mutant.md                   — load in Phase 3 for each surviving mutant
│   └── refactor-for-complexity.md       — load in Phase 4 for each over-complex method
└── references/
    ├── jacoco-setup.md                  — Maven + Gradle plugin snippets, Lombok config
    ├── pit-setup.md                     — Maven + Gradle plugin snippets, exclusion rules
    └── spring-test-types.md             — @WebMvcTest vs. @DataJpaTest vs. @SpringBootTest decisions
```

## Why this design is worth following

A few of the choices are load-bearing and worth understanding before you edit the skill:

*CRAP threshold is 10, not 5.* Uncle Bob said < 5 in the video. CRAP = 5 requires complexity 2 at 100% coverage — one conditional per method. That's not realistic for a Spring service with any real business logic. 10 is aggressive but achievable; 5 as a stretch goal is fine, but using it as a gate will either stall the run or produce a pile of absurd micro-methods.

*Existing mutation testers, not a hand-rolled one.* Uncle Bob said "have the AI build the mutation tester in five minutes." PIT has been the Java mutation-testing gold standard for over a decade and handles Java bytecode mutation corner cases a new implementation won't get right. The skill uses PIT. Being pragmatic here doesn't weaken the workflow — it strengthens it.

*Refactor must not drop mutation score.* This is the single most important safety gate. A passing test suite after a refactor is necessary but not sufficient — the suite must still be *as good at detecting bugs* as before. Without this gate, a refactor that accidentally turns pure functions into untested wrappers will look green while silently weakening verification.

*Default mutation scope is `full`.* The user specified this. PIT on full codebases is slow; honor the `time_budget_minutes` hard stop and prioritize scope-wide mutation score over phase-level perfectionism if budget runs out.

*Skip Lombok-generated methods* via `lombok.addLombokGeneratedAnnotation = true`. Otherwise JaCoCo reports spurious low coverage on getters/setters and the skill will waste cycles writing tests for `return this.name;`.

## If the skill finds itself stuck

These are known failure modes and the right response for each.

- **Flaky tests.** A test passes locally, fails under PIT, or passes on first run and fails on rerun. Don't fight it — quarantine the test with `@Disabled("flaky: crap-buster YYYY-MM-DD")`, log the class in the report, and move on. The user's next move is to fix the flake manually.
- **Spring context load failures.** Usually a misconfigured slice test. Downgrade the offending test to a plain JUnit + Mockito test if possible; if not, skip and log.
- **PIT out-of-memory.** Add `-DjvmArgs=-Xmx4g` (or higher) to the PIT invocation and retry once. If it still OOMs, narrow scope and continue.
- **Coverage report missing classes.** Usually means the test suite didn't run against those classes at all (compile failure, module config). Don't try to fix the module — stop Phase 2, print the missing classes, move on.
- **CRAP stuck above threshold for a specific method no matter what.** Some methods are irreducibly complex (parsers, state machines). After two refactor attempts with no CRAP improvement, add the method to `exclude` in `.crap-buster.yml` with a comment explaining why, commit, and move on.
