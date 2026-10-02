# Review Stop Rule

A short, mechanical rule that terminates review-revision loops on documents.
The terminal condition of a review is **acceptance**, not the absence of findings.
"No findings" is unreachable; "yes, hand it over" is reachable.

Applies to every skill that runs a review loop over a document — `/design-review`,
`/ux-review`, `/architecture-review`, `/review-all-gdds`, `/code-review` (as
applicable) — and to the phase-gate questions in `/gate-check`. Review-participating
agents follow the same rule when issuing findings or synthesizing verdicts.

The rule is checkable without judgment: the Observable Diff requirement is the
forcing function. Either a finding states a runtime/interface-level diff, or it
cannot block.

---

## 1. Consumer Test

A finding may only block if it carries an **Observable Diff**, stated at
issuance time:

> "If unfixed: a player experiences X / an implementer builds Y. If fixed: Z."

X, Y, and Z must differ at the runtime or interface level. A finding with no
stateable observable diff cannot block; it is routed to the document's
**carried-findings register** (a deferred-items list on the document), not to a
revision bar.

## 2. Regeneration Guard

Findings about the review process's own artifacts — revision dispositions,
verification transcripts, figures and counts in reports, log bookkeeping —
NEVER open a revision cycle. They are routed to a single consolidated
**errata channel** with at most one correction pass per document, ever. No
escalation machinery (tripwires, watch lists, grace periods) may be built on
meta-artifact findings.

## 3. Proportionality

A revision cycle is the response to a design change, not a sentence edit.
Findings that pass the consumer test but are individually one-clause
(determinacy pins, wording disambiguations, single-value pins) go into a
**pin register** on the document and are executed in ONE batched pass at the
next natural phase boundary — not one full review cycle each. The revision
ceremony must scale to the size of the change.

## 4. Acceptance Anchor

Every review must end with one terminal question, put to the senior synthesizer:

> "Would you hand this document to the next phase today — yes or no? If no,
> name the ONE finding that stops you."

The loop ends at the first "yes." The verdict vocabulary includes
**ACCEPTED (deferred items carried)** as a terminal state, and reviews are
phrased as acceptance decisions, not exhaustive defect searches. Even when
findings exist, the verdict names the single worst remaining item.

## 5. Pre-Committed Ceiling

At a document's FIRST review, a cycle ceiling is declared and written down.
Default: **3 revision cycles after first review, plus 1 batched pin pass**.
Once the ceiling is reached, the document is accepted with its registers. The
ceiling cannot be raised mid-loop.

---

## Registers

| Register | Contents | Consumed by |
|----------|----------|-------------|
| **Carried-findings register** | Findings that failed or were not given the consumer test — deferred, non-blocking | Next-phase consumers (`/create-architecture`, `/consistency-check`) and any future re-review |
| **Pin register** | One-clause fixes (determinacy pins, wording disambiguations, single-value pins) pending one batched pass | The next natural phase boundary — executed by the next-phase consumer |
| **Errata channel** | Meta-artifact corrections (counts, figures, bookkeeping in review artifacts) | One consolidated correction pass per document, ever |

Registers live **on the document** (appended sections), written with the
document owner's approval at the review that produces them. Downstream
consumers read the registers and execute the batched fixes, so deferral has a
real home.
