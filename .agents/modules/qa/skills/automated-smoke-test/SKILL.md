---
name: automated-smoke-test
description: "Run an automated smoke test using the Beckett MCP server. Launches the Godot project, captures logs, and checks for errors or crashes."
argument-hint: "[duration-seconds]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Bash, Task, question
---

# Automated Smoke Test

This skill runs a fully automated smoke test against the Godot project using
the Beckett MCP server. It launches the project, captures logs for a
configurable duration, and analyzes the output for errors, warnings, and
assertions — producing a structured pass/fail report.

No manual verification required. The entire check is automated through MCP.

---

## Phase 1: Verify Beckett MCP Availability

Call `get_godot_version` via the Beckett MCP server. If the call succeeds, note
the version string. If it fails, inform the user:

> "Beckett MCP server is not available. Install the Beckett plugin in your Godot
> project: copy `addons/beckett/` into your project, then enable it in
> Project → Project Settings → Plugins. See `/setup-engine` for full setup
> instructions."

Stop if the server is unavailable.

---

## Phase 2: Read Project Info

Call `get_project_statistics` via Beckett. Record:

- **Project size**, **script count**, **scene count** — context for duration scaling

Call `get_project_setting` for the key `application/run/main_scene`. Record:

- **Main scene** — the configured main scene path

If `get_project_statistics` or `get_project_setting` fails, retry up to 3 times
with a 2-second delay between attempts. If all retries fail: "Could not read
project info after 3 attempts. Is the Beckett plugin enabled and the correct
project open in the Godot editor?" Then stop.

---

## Phase 3: Run the Project

Parse the optional argument for duration. If no argument is provided, default
to 10 seconds. The argument is in seconds: `/automated-smoke-test 15` means
capture logs for 15 seconds.

Call `play_scene` via Beckett to launch the project.

After calling `play_scene`, poll `get_play_state` up to 15 times with a 2-second
interval (30 seconds total) to confirm the project is running:

1. Call `get_play_state`.
2. If it returns a playing/running state, proceed to Phase 4.
3. If it returns a stopped/error state, the project failed to start:
   - Report: "Project failed to start."
   - Verdict: **FAIL**
   - Skip to Phase 7 (Report)
4. If the call itself errors, retry. After 3 consecutive errors:
   - Report: "Could not confirm project is running after 3 attempts."
   - Verdict: **FAIL**
   - Skip to Phase 7

If no playing state is observed within 30 seconds:
- Report: "Project did not reach a running state within 30 seconds — the
  project may be hung or the engine may have frozen during launch."
- Verdict: **FAIL**
- Skip to Phase 6 (stop), then Phase 7

---

## Phase 4: Capture Logs

> **Duration scaling:** The capture duration should reflect project complexity.
> A minimal 2D project may produce output in 5 seconds; a large 3D project with
> many scenes may need 30+ seconds. Default to 10 seconds but scale up for
> complex titles (use script/scene counts from Phase 2 as a guide). For
> headless CI runs, prefer longer durations to account for slower hardware.

Do not use a fixed sleep. Instead, poll `logs_read` in a loop:

1. Every 2 seconds, call `logs_read`.
2. Accumulate the log output across polls — Beckett returns the current log
   buffer, so concatenate each poll's result to build the full capture.
3. If the accumulated output contains any ERROR, crash, or assertion pattern
   (see Phase 5), stop polling early — the test has already found failures.
4. If no errors appear, continue polling until the configured duration elapses
   (default: 10 seconds, configurable via argument).
5. If `logs_read` returns an error on any poll tick:
   - Report: "Could not capture logs on poll attempt [N]: [error message]"
   - Continue polling (do not abort) unless 3 consecutive polls fail.
   - After 3 consecutive failures: "Log capture failed after 3 consecutive
     poll errors."
   - Verdict: **FAIL**
   - Skip to Phase 6

Once polling ends (duration elapsed or early-stop triggered), use the
accumulated output for analysis. If all polls failed (3 consecutive errors),
there is no output to analyze — skip directly to the FAIL verdict.

If the final output is empty or trivially short, note: "Output appears minimal
— the project may not have rendered any frames."

**Optional visual check:** If `screenshot` is available, call it once during the
capture window to capture a frame. Note in the report whether a screenshot was
captured. This is advisory — a failed screenshot does not cause a FAIL verdict.

**Optional performance snapshot:** If `get_performance_monitors` is available,
call it once near the end of the capture window. Record fps, frame time, and
memory if returned. Include in the report as advisory data.

---

## Phase 5: Analyze Output

Scan the accumulated logs for:

| Pattern | Severity | Flags |
|---------|----------|-------|
| `ERROR` | Error | Catch-all for Godot error messages |
| `error:` | Error | Lower-case variant in scripts |
| `crash` | Critical | Game crashed during runtime |
| `NullReferenceException` | Error | Null access in C# script (.NET) |
| `segfault` | Critical | Memory access violation |
| `segmentation fault` | Critical | Full-form segfault message |
| `WARNING` | Warning | Non-fatal warnings |
| `warning:` | Warning | Lower-case variant |
| `Assertion failed` | Error | GDScript or C# assertion failure |

Count the occurrences of each pattern. Record the actual matching lines (up to
10 per pattern for the report).

---

## Phase 6: Stop the Project

Call `stop_scene` via Beckett to clean up. If it fails, note:
"Could not stop the project cleanly — you may need to stop it manually in the
Godot editor."

---

## Phase 7: Report Results

Format the report:

```markdown
## Automated Smoke Test Report

**Date**: [date]
**Project**: [project statistics summary]
**Main Scene**: [main scene path]
**Godot Version**: [version from Phase 1]
**Duration**: [X seconds]

---

### Results

| Check | Result |
|-------|--------|
| Project launched | PASS / FAIL |
| No runtime errors | PASS / FAIL (N errors found) |
| No critical crashes | PASS / FAIL (N crashes detected) |
| No warnings | PASS / WARN (N warnings) |
| No assertion failures | PASS / FAIL (N assertions failed) |

---

### Error Details

[If errors/crashes found, include the matching lines in a code block.
Otherwise: "No errors detected."]

---

### Warning Details

[If warnings found, include the matching lines in a code block.
Otherwise: "No warnings detected."]

---

### Performance Snapshot

[If get_performance_monitors was called, include fps, frame time, memory.
Otherwise: "Not captured."]

---

### Screenshot

[If screenshot was captured, note: "Screenshot captured during run."
Otherwise: "Not captured."]

---

### Verdict: [PASS | FAIL | SILENT-FAIL]

**FAIL** if ANY of:
- Project failed to start
- Runtime errors or crashes detected
- Assertion failures found
- Logs could not be captured after retries

**SILENT-FAIL** if:
- Project launched successfully AND no errors/crashes detected BUT
  log output was empty or trivially short (zero or near-zero lines).
  This means the project may have started but produced no frames or
  lifecycle output — a configuration problem or silent hang. The user
  should verify manually.

**PASS** if ALL of:
- Project launched successfully
- Log output contains substantive content (not SILENT-FAIL threshold)
- No runtime errors or crashes
- No assertion failures
- Warnings are acceptable (advisory only — do not cause FAIL)
```

Present the report to the user. Do not write it to a file unless asked.
