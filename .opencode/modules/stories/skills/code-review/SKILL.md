---
name: code-review
description: "Performs an architectural and quality code review on a specified file or set of files. Checks for coding standard compliance, architectural pattern adherence, SOLID principles, testability, and performance concerns."
argument-hint: "[path-to-file-or-directory]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Task
agent: lead-programmer
---

## Phase 1: Load Target Files

Read the target file(s) in full. Read AGENTS.md for project coding standards.

---

## Phase 2: Identify Engine Specialists

Read `docs/framework/technical-preferences.md`, section `## Engine Specialists`. Note:

- The **Primary** specialist (used for architecture and broad engine concerns)
- The **Language/Code Specialist** (used when reviewing the project's primary language files)
- The **Shader Specialist** (used when reviewing shader files)
- The **UI Specialist** (used when reviewing UI code)

If the section reads `[TO BE CONFIGURED]`, no engine is pinned — skip engine specialist steps.

---

## Phase 3: ADR Compliance Check

Search for ADR references in the story file, commit messages, and header comments. Look for patterns like `ADR-NNN` or `docs/architecture/ADR-`.

If no ADR references found, note: "No ADR references found — skipping ADR compliance check."

For each referenced ADR: read the file, extract the **Decision** and **Consequences** sections, then classify any deviation:

- **ARCHITECTURAL VIOLATION** (BLOCKING): Uses a pattern explicitly rejected in the ADR
- **ADR DRIFT** (WARNING): Meaningfully diverges from the chosen approach without using a forbidden pattern
- **MINOR DEVIATION** (INFO): Small difference from ADR guidance that doesn't affect overall architecture

---

## Phase 4: Standards Compliance

Identify the system category (engine, gameplay, AI, networking, UI, tools) and evaluate:

- [ ] Public methods and classes have doc comments
- [ ] Cyclomatic complexity under 10 per method
- [ ] No method exceeds 40 lines (excluding data declarations)
- [ ] Dependencies are injected (no static singletons for game state)
- [ ] Configuration values loaded from data files
- [ ] Systems expose interfaces (not concrete class dependencies)

---

## Phase 5: Architecture and SOLID

**Architecture:**
- [ ] Correct dependency direction (engine <- gameplay, not reverse)
- [ ] No circular dependencies between modules
- [ ] Proper layer separation (UI does not own game state)
- [ ] Events/signals used for cross-system communication
- [ ] Consistent with established patterns in the codebase

**SOLID:**
- [ ] Single Responsibility: Each class has one reason to change
- [ ] Open/Closed: Extendable without modification
- [ ] Liskov Substitution: Subtypes substitutable for base types
- [ ] Interface Segregation: No fat interfaces
- [ ] Dependency Inversion: Depends on abstractions, not concretions

---

## Phase 6: Game-Specific Concerns

- [ ] Frame-rate independence (delta time usage)
- [ ] No allocations in hot paths (update loops)
- [ ] Proper null/empty state handling
- [ ] Thread safety where required
- [ ] Resource cleanup (no leaks)

---

## Phase 7: Specialist Reviews (Parallel)

Spawn all applicable specialists simultaneously via Task — do not wait for one before starting the next.

### Engine Specialists

If an engine is configured, determine which specialist applies to each file and spawn in parallel:

- Primary language files (`.gd`, `.cs`, `.cpp`) → Language/Code Specialist
- Shader files (`.gdshader`, `.hlsl`, shader graph) → Shader Specialist
- UI screen/widget code → UI Specialist
- Cross-cutting or unclear → Primary Specialist

Also spawn the **Primary Specialist** for any file touching engine architecture (scene structure, node hierarchy, lifecycle hooks).

### QA Testability Review

For Logic and Integration stories, also spawn `qa-tester` via Task in parallel with the engine specialists. Pass:
- The implementation files being reviewed
- The story's `## QA Test Cases` section (the pre-written test specs from qa-lead)
- The story's `## Acceptance Criteria`

Ask the qa-tester to evaluate:
- [ ] Are all test hooks and interfaces exposed (not hidden behind private/internal access)?
- [ ] Do the QA test cases from the story's `## QA Test Cases` section map to testable code paths?
- [ ] Are any acceptance criteria untestable as implemented (e.g., hardcoded values, no seam for injection)?
- [ ] Does the implementation introduce any new edge cases not covered by the existing QA test cases?
- [ ] Are there any observable side effects that should have a test but don't?

For Visual/Feel and UI stories: qa-tester reviews whether the manual verification steps in `## QA Test Cases` are achievable with the implementation as written — e.g., "is the state the manual checker needs to reach actually reachable?"

Collect all specialist findings before producing output.

---

## Phase 8: Output Review

**Review Stop Rule (as applicable — full text in `docs/framework/review-stop-rule.md`):**
- **Consumer test** — every item under "Required Changes" must carry an
  Observable Diff: "If unfixed: a player experiences X / an implementer builds
  Y. If fixed: Z" — differing at the runtime or interface level. A finding
  with no stateable observable diff goes under "Suggestions", not "Required
  Changes".
- **Regeneration guard** — findings about the review process's own artifacts
  (review report bookkeeping, counts in prior reviews) never trigger a
  re-review cycle.
- **Acceptance anchor** — end every review with one terminal question:
  "Would you hand this code to the next phase (merge) today — yes or no? If
  no, name the ONE finding that stops you." The loop ends at the first "yes";
  when findings remain, name the single worst remaining item.

```
## Code Review: [File/System Name]

### Engine Specialist Findings: [N/A — no engine configured / CLEAN / ISSUES FOUND]
[Findings from engine specialist(s), or "No engine configured." if skipped]

### Testability: [N/A — Visual/Feel or Config story / TESTABLE / GAPS / BLOCKING]
[qa-tester findings: test hooks, coverage gaps, untestable paths, new edge cases]
[If BLOCKING: implementation must expose [X] before tests in ## QA Test Cases can run]

### ADR Compliance: [NO ADRS FOUND / COMPLIANT / DRIFT / VIOLATION]
[List each ADR checked, result, and any deviations with severity]

### Standards Compliance: [X/6 passing]
[List failures with line references]

### Architecture: [CLEAN / MINOR ISSUES / VIOLATIONS FOUND]
[List specific architectural concerns]

### SOLID: [COMPLIANT / ISSUES FOUND]
[List specific violations]

### Game-Specific Concerns
[List game development specific issues]

### Positive Observations
[What is done well -- always include this section]

### Required Changes
[Must-fix items before approval — ARCHITECTURAL VIOLATIONs always appear here.
Each item carries an Observable Diff: "If unfixed: a player experiences X /
an implementer builds Y. If fixed: Z." Items with no observable diff go to
Suggestions instead.]

### Acceptance Answer
"Hand this code to the next phase (merge) today — [Yes / No]"
[If yes with findings remaining: worst remaining item: (the ONE finding).]

### Suggestions
[Nice-to-have improvements]

### Verdict: [APPROVED / APPROVED WITH SUGGESTIONS / CHANGES REQUIRED]
```

This skill is read-only — no files are written.

---

## Phase 9: Next Steps

- If verdict is APPROVED: run `/story-done [story-path]` to close the story.
- If verdict is CHANGES REQUIRED: fix the issues and re-run `/code-review`.
- If an ARCHITECTURAL VIOLATION is found: run `/architecture-decision` to record the correct approach.
