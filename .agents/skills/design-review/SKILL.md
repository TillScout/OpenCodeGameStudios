---
name: design-review
description: "Reviews a game design document for completeness, internal consistency, implementability, and adherence to project design standards. Run this before handing a design document to programmers."
argument-hint: "[path-to-design-doc] [--depth full|lean|solo]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, question
---

## Phase 0: Parse Arguments

Extract `--depth [full|lean|solo]` if present. Default is `full` when no flag is given.

**Note**: `--depth` controls the *analysis depth* of this skill (how many specialist agents are spawned). It is independent of the global review mode in `production/review-mode.txt`, which controls director gate spawning. These are two different concepts — `--depth` is about how thoroughly *this* skill analyses the document.

- **`full`**: Complete review — all phases + specialist agent delegation (Phase 3b)
- **`lean`**: All phases, no specialist agents — faster, single-session analysis
- **`solo`**: Phases 1-4 only, no delegation, no Phase 5 next-step prompt — use when called from within another skill

---

## Phase 1: Load Documents

Read the target design document in full. Read AGENTS.md to understand project context and standards. Read related design documents referenced or implied by the target doc (check `design/gdd/` for related systems).

**Dependency graph validation:** For every system listed in the Dependencies section, use Glob to check whether its GDD file exists in `design/gdd/`. Flag any that don't exist yet — these are broken references that downstream authors will hit.

**Lore/narrative alignment:** If `design/gdd/game-concept.md` or any file in `design/narrative/` exists, read it. Note any mechanical choices in this GDD that contradict established world rules, tone, or design pillars. Pass this context to `game-designer` in Phase 3b.

**Prior review check:** Check whether `design/gdd/reviews/[doc-name]-review-log.md` exists. If it does, read the most recent entry — note what verdict was given and what blocking items were listed. This session is a re-review; track whether prior items were addressed.

**Cycle ceiling (Review Stop Rule clause 5 — see `docs/framework/review-stop-rule.md`):**
- **No review log exists** → this is the FIRST review. Declare the cycle ceiling now: default **3 revision cycles after first review, plus 1 batched pin pass**. Record it in the review output and (with approval) in the review log entry. The ceiling cannot be raised mid-loop.
- **Review log exists** → count prior `NEEDS REVISION` / `MAJOR REVISION NEEDED` entries as cycles used. Report: "Cycle [N] of ceiling [M]."
- **Ceiling reached** → this review MUST end with the ACCEPTED (deferred items carried) verdict. Do not issue a revision bar. Route all new findings to the registers and close with the acceptance question (Phase 4).

**Register load:** Check the target document for `## Carried-Findings Register`, `## Pin Register`, and `## Errata` sections (written by prior reviews). If present, load them — pin-register items are due for their batched pass, and carried items must not be re-litigated as new findings.

---

## Phase 2: Completeness Check

Evaluate against the Design Document Standard checklist:

- [ ] Has Overview section (one-paragraph summary)
- [ ] Has Player Fantasy section (intended feeling)
- [ ] Has Detailed Rules section (unambiguous mechanics)
- [ ] Has Formulas section (all math defined with variables)
- [ ] Has Edge Cases section (unusual situations handled)
- [ ] Has Dependencies section (other systems listed)
- [ ] Has Tuning Knobs section (configurable values identified)
- [ ] Has Acceptance Criteria section (testable success conditions)

---

## Phase 3: Consistency and Implementability

**Internal consistency:**
- Do the formulas produce values that match the described behavior?
- Do edge cases contradict the main rules?
- Are dependencies bidirectional (does the other system know about this one)?

**Implementability:**
- Are the rules precise enough for a programmer to implement without guessing?
- Are there any "hand-wave" sections where details are missing?
- Are performance implications considered?

**Cross-system consistency:**
- Does this conflict with any existing mechanic?
- Does this create unintended interactions with other systems?
- Is this consistent with the game's established tone and pillars?

---

## Phase 3b: Adversarial Specialist Review (full mode only)

**Skip this phase in `lean` or `solo` mode.**

**This phase is MANDATORY in full mode.** Do not skip it.

**Before spawning any agents**, print this notice:
> "Full review: spawning specialist agents in parallel. This typically takes 8–15 minutes. Use `--review lean` for faster single-session analysis."

### Step 1 — Identify all domains the GDD touches

Read the GDD and identify every domain present. A GDD can touch multiple domains simultaneously — be thorough. Common signals:

| If the GDD contains... | Spawn these agents |
|------------------------|-------------------|
| Costs, prices, drops, rewards, economy | `economy-designer` |
| Combat stats, damage, health, DPS | `game-designer`, `systems-designer` |
| AI behaviour, pathfinding, targeting | `ai-programmer` |
| Level layout, spawning, wave structure | `level-designer` |
| Player progression, XP, unlocks | `economy-designer`, `game-designer` |
| UI, HUD, menus, player-facing displays | `ux-designer`, `ui-programmer` |
| Dialogue, quests, story, lore | `narrative-director` |
| Animation, feel, timing, juice | `gameplay-programmer` |
| Multiplayer, sync, replication | `network-programmer` |
| Audio cues, music triggers | `audio-director` |
| Performance, draw calls, memory | `performance-analyst` |
| Engine-specific patterns or APIs | Primary engine specialist (from `docs/framework/technical-preferences.md`) |
| Acceptance criteria, test coverage | `qa-lead` |
| Data schema, resource structure | `systems-designer` |
| Any gameplay system | `game-designer` (always) |

**Always spawn `game-designer` and `systems-designer` as a baseline minimum.** Every GDD touches their domain.

### Step 2 — Spawn all relevant specialists in parallel

**CRITICAL: Task in this skill spawns a SUBAGENT — a separate independent Claude session
with its own context window. It is NOT task tracking. Do NOT simulate specialist
perspectives internally. Do NOT reason through domain views yourself. You MUST issue
actual Task calls. A simulated review is not a specialist review.**

Issue all Task calls simultaneously. Do NOT spawn one at a time.

**Prompt each specialist adversarially:**
> "Here is the GDD for [system] and the main review's structural findings so far.
> Your job is NOT to validate this design — your job is to find problems.
> Challenge the design choices from your domain expertise. What is wrong,
> underspecified, likely to cause problems, or missing entirely?
> Be specific and critical. Disagreement with the main review is welcome."

Any fix or replacement text a specialist prescribes must satisfy Phase 4's prescription discipline (simulation, existence, coverage arithmetic, grader determinacy) — specialists self-check their own prescriptions before issuing them.

**Observable Diff requirement (Review Stop Rule clause 1).** Every finding a specialist submits as blocking must carry an Observable Diff, stated at issuance: "If unfixed: a player experiences X / an implementer builds Y. If fixed: Z" — where X/Y and Z differ at the runtime or interface level. Tell each specialist: findings without a stateable observable diff will be routed to the document's carried-findings register and cannot block, so don't phrase findings as opinions — state the diff or mark the item `[register]` yourself. Findings about the review process's own artifacts (dispositions, transcripts, figures and counts in reports, log bookkeeping) must be marked `[errata]` — they never open a revision cycle.

**Additional instructions per agent type:**

- **`game-designer`**: Anchor your review to the Player Fantasy stated in Section B of this GDD. Does this design actually deliver that fantasy? Would a player feel the intended experience? Flag any rules that serve implementability but undermine the stated feeling.

- **`systems-designer`**: For every formula in the GDD, plug in boundary values (minimum and maximum plausible inputs). Report whether any outputs go degenerate — negative values, division by zero, infinity, or nonsensical results at the extremes.

- **`qa-lead`**: Review every acceptance criterion. Flag any that are not independently testable — phrases like "feels balanced", "works correctly", "performs well" are not ACs. Suggest concrete rewrites for any that fail this test.

### Step 3 — Senior lead review

After all specialists respond, spawn `creative-director` as the **senior reviewer**:
- Provide: the GDD, all specialist findings, any disagreements between them, the cycle count vs the declared ceiling, and any existing registers on the document
- Ask: "Synthesise these findings. What are the most important issues? Do you agree with the specialists? What is your overall verdict on this design?"
- Ask also: any prescription, adjudication, or re-review bar the synthesis issues must satisfy Phase 4's prescription discipline — including the bar itself.
- **Acceptance anchor (Review Stop Rule clause 4) — the terminal question, always asked last:** "Would you hand this document to the next phase (architecture) today — yes or no? If no, name the ONE finding that stops you." The loop ends at the first "yes". The creative-director must answer this even when findings exist, and must name the single worst remaining item when answering "yes".
- The creative-director's synthesis and acceptance answer become the **final verdict** in Phase 4.

### Step 4 — Surface disagreements

If specialists disagree with each other or with the creative-director, do NOT silently pick one view. Present the disagreement explicitly in Phase 4 so the user can adjudicate.

Mark every finding with its source: `[game-designer]`, `[economy-designer]`, `[creative-director]` etc.

---

## Phase 4: Output Review

**Review Stop Rule (binding — full text in `docs/framework/review-stop-rule.md`).** This review is an acceptance decision, not an exhaustive defect search. Route every finding through this table before writing the output:

| Finding type | Route | Counts toward ceiling? |
|--------------|-------|------------------------|
| Passes the consumer test, design-level (stated Observable Diff) | Revision bar (`Required Before Implementation`) | Yes |
| Passes the consumer test, but one-clause (determinacy pin, wording disambiguation, single-value pin) | **Pin register** — one batched pass at the next phase boundary | No — the batched pass is the ceiling's +1 |
| No stateable Observable Diff | **Carried-findings register** — cannot block | No |
| About the review process's own artifacts (dispositions, verification transcripts, figures/counts in reports, log bookkeeping) | **Errata channel** — one correction pass per document, ever; never a revision cycle, never an escalation | No |

**Blocking findings must each carry an Observable Diff field:** "If unfixed: a player experiences X / an implementer builds Y. If fixed: Z." A finding with no observable diff cannot appear in `Required Before Implementation`.

**Verdict rules:**
- Zero blocking findings after routing → verdict is **ACCEPTED (deferred items carried)** or APPROVED, even if the registers are non-empty. Registers do not block.
- Ceiling reached → verdict is **ACCEPTED (deferred items carried)**, regardless of remaining findings.
- The review always ends with the acceptance question and, when the answer is "yes", the named ONE worst remaining item.

**Prescription discipline (binding on every fix this review issues).** A review's prescriptions — replacement text, pinned rules, named mechanisms, plant/pattern/cell counts, grader rubrics, and the re-review bar written into the review log — are implemented faithfully by the revision session. A defective prescription therefore enters the GDD with the review's own stamp of approval and is only found one or two cycles later, wasting a full review round. Before any prescription is issued into the output or the review log, it must pass these checks:

1. **Simulation** — every prescribed formula, predicate, driver, or rule containing arithmetic is walked against its boundary inputs (minimum and maximum plausible values, plus the exact input class the fix targets) before issuance.
2. **Existence** — every named engine mechanism, API member, or tool is verified against engine documentation or a registered probe gate. A mechanism the engine does not expose is never prescribed as if it existed.
3. **Coverage arithmetic** — any prescription that prescribes a COUNT of things (violation plants, scan patterns, test cells, fixtures, table rows, criteria) must enumerate the distinct families the target rule covers and show that every family is caught by at least one prescribed item (families × plants). A disjunction ("do X OR Y") is inadmissible unless each arm alone satisfies the coverage count.
4. **Grader determinacy** — any prescription containing a human-judgment rubric must pass: "would two independent facilitators reach the same ruling from this text as written?" If not, the rubric is rewritten to a determinate form before issuance.
5. **Self-application** — this discipline applies to the review's own output, including the re-review bar and any adjudication text the creative-director issues. A review that audits the GDD's fixes but exempts its own instructions has not learned the lesson.

```
## Design Review: [Document Title]
Specialists consulted: [list agents spawned]
Re-review: [Yes — prior verdict was X on YYYY-MM-DD / No — first review]

### Completeness: [X/8 sections present]
[List missing sections]

### Dependency Graph
[List each declared dependency and whether its GDD file exists on disk]
- ✓ enemy-definition-data.md — exists
- ✗ loot-system.md — NOT FOUND (file does not exist yet)

### Required Before Implementation
[Numbered list — blocking issues only. Each item tagged with source agent and
carrying an Observable Diff field:]
1. [Issue] — [source agent]
   Observable Diff: If unfixed: a player experiences [X] / an implementer builds [Y]. If fixed: [Z].

### Pin Register (one batched pass at the next phase boundary)
[One-clause findings that pass the consumer test: determinacy pins, wording
disambiguations, single-value pins. Each with its Observable Diff. Executed
together in ONE pass — never one review cycle each.]

### Carried-Findings Register (deferred, non-blocking)
[Findings with no stateable Observable Diff. Recorded on the document; cannot
block. If empty, write "None."]

### Errata (one correction pass per document, ever)
[Meta-artifact findings: figures and counts in review reports, disposition
bookkeeping, verification transcripts. Never open a revision cycle. If empty, write "None."]

### Recommended Revisions
[Numbered list — important but not blocking. Source-tagged.]

### Specialist Disagreements
[Any cases where agents disagreed with each other or with the main review.
Present both sides — do not silently resolve.]

### Nice-to-Have
[Minor improvements, low priority.]

### Senior Verdict [creative-director]
[Creative director's synthesis and overall assessment. MUST include the
acceptance answer: "Hand to the next phase (architecture) today — yes/no."
If yes with findings remaining, name the ONE worst remaining item.]

### Scope Signal
Estimate implementation scope based on: dependency count, formula count,
systems touched, and whether new ADRs are required.
- **S** — single system, no formulas, no new ADRs, <3 dependencies
- **M** — moderate complexity, 1-2 formulas, 3-6 dependencies
- **L** — multi-system integration, 3+ formulas, may require new ADR
- **XL** — cross-cutting concern, 5+ dependencies, multiple new ADRs likely
Label clearly: "Rough scope signal: M (producer should verify before sprint planning)"

### Verdict: [APPROVED / ACCEPTED (deferred items carried) / NEEDS REVISION / MAJOR REVISION NEEDED]
Cycle count: [N] of ceiling [M — declared at first review; default 3 revision
cycles + 1 batched pin pass. The ceiling cannot be raised mid-loop.]
[ACCEPTED (deferred items carried) = terminal: the senior answer to the
acceptance question was "yes" with register items carried, or the ceiling was
reached. ACCEPTED and APPROVED both close the loop — no further review cycles.]
```

This skill is read-only — no files are written during Phase 4.

---

## Phase 5: Next Steps

Use `question` for ALL closing interactions. Never plain text.

**First widget — what to do next:**

If APPROVED or ACCEPTED (deferred items carried) — no revision bar issued — proceed directly to the systems-index widget, review-log widget, then the final closing widget. Do not show a separate "what to do" widget — the final closing widget covers next steps.

If ACCEPTED with non-empty registers, first ask via `question`: "May I append the carried-findings register, pin register, and errata sections to [doc-path]? They are consumed by `/create-architecture` and `/consistency-check` at the next phase boundary." Options: `[A] Yes — append registers to the document` / `[B] No — registers live in the review log only`.

If NEEDS REVISION or MAJOR REVISION NEEDED, options:
- `[A] Revise the GDD now — address blocking items together`
- `[B] Stop here — revise in a separate session`
- `[C] Accept as-is and move on (only if all items are advisory)`
- `[D] Run the batched pin pass now — execute the pin register items in one pass (no full revision cycle)`

**If user selects [A] — Revise now:**

Work through all blocking items, asking for design decisions only where you cannot resolve the issue from the GDD and existing docs alone. Group all design-decision questions into a single multi-tab `question` before making any edits — do not interrupt mid-revision for each blocker individually.

After all revisions are complete, show a summary table (blocker → fix applied) and use `question` for a **post-revision closing widget**:

- Prompt: "Revisions complete — [N] blockers resolved. What next?"
- Note current context usage: if context is above ~50%, add: "(Recommended: /clear before re-review — this session has used X% context. A full re-review runs 5 agents and needs clean context.)"
- Options:
  - `[A] Re-review in a new session — run /design-review [doc-path] after /clear`
  - `[B] Accept revisions and mark Approved — update systems index, skip re-review`
  - `[C] Move to next system — /design-system [next-system] (#N in design order)`
  - `[D] Stop here`

Never end the revision flow with plain text. Always close with this widget.

**Second widget — systems index update (always show this separately):**

Use a second `question`:
- Prompt: "May I update `design/gdd/systems-index.md` to mark [system] as [In Review / Approved]?"
- Options: `[A] Yes — update it` / `[B] No — leave it as-is`

**Third widget — review log (always offer):**

Use a third `question`:
- Prompt: "May I append this review summary to `design/gdd/reviews/[doc-name]-review-log.md`? This creates a revision history so future re-reviews can track what changed."
- Options: `[A] Yes — append to review log` / `[B] No — skip`

If yes, append an entry in this format:
```
## Review — [YYYY-MM-DD] — Verdict: [APPROVED / ACCEPTED (deferred items carried) / NEEDS REVISION / MAJOR REVISION NEEDED]
Cycle ceiling: [M — declared at first review; default 3 revision cycles + 1 batched pin pass. Only present on the first review entry.]
Cycles used: [N of M]
Scope signal: [S/M/L/XL]
Specialists: [list]
Blocking items: [count — each with an Observable Diff] | Recommended: [count]
Pin register: [count] | Carried-findings register: [count] | Errata: [count]
Acceptance answer: [Yes — handed to next phase / No — blocked by: (the ONE finding)]
Summary: [2-3 sentence summary of key findings from creative-director verdict]
Prior verdict resolved: [Yes / No / First review]
```

---

**Final closing widget — always show after all file writes complete:**

Once the systems-index and review-log widgets are answered, check project state and show one final `question`:

Before building options, read:
- `design/gdd/systems-index.md` — find any system with Status: In Review or NEEDS REVISION (other than the one just reviewed)
- Count `.md` files in `design/gdd/` (excluding game-concept.md, systems-index.md) to determine if `/review-all-gdds` is worth offering (≥2 GDDs)
- Find the next system with Status: Not Started in design order

Build the option list dynamically — only include options that are genuinely next:
- `[_] Run /design-review [other-gdd-path] — [system name] is still [In Review / NEEDS REVISION]` (include if another GDD needs review)
- `[_] Run /consistency-check — verify this GDD's values don't conflict with existing GDDs` (always include if ≥1 other GDD exists)
- `[_] Run /review-all-gdds — holistic design-theory review across all designed systems` (include if ≥2 GDDs exist)
- `[_] Run /design-system [next-system] — next in design order` (always include, name the actual system)
- `[_] Stop here`

Assign letters A, B, C… only to included options. Mark the most pipeline-advancing option as `(recommended)`.

Never end the skill with plain text after file writes. Always close with this widget.
