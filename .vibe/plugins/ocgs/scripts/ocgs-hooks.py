#!/usr/bin/env python3
"""
ocgs-hooks.py — Vibe hook handler for OpenCode Game Studios.

Receives a Vibe hook event JSON on stdin, applies OCGS validation logic,
and responds via exit code + stdout JSON.

Dispatched by command-line argument:
  git-guard        pre_tool  (bash)     — block push to protected branches, validate commits
  file-validator   post_tool (write_file|edit) — validate assets, JSON, GDD sections
  agent-audit      post_tool (task)     — log subagent invocations
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROTECTED_BRANCHES = ["main", "master", "develop"]
DESIGN_SECTIONS = [
    "Overview", "Player Fantasy", "Detailed", "Formulas",
    "Edge Cases", "Dependencies", "Tuning Knobs", "Acceptance Criteria",
]
SOURCE_EXTENSIONS = [".gd", ".cs", ".cpp", ".c", ".h", ".hpp", ".rs", ".py", ".js", ".ts"]


def read_event():
    return json.load(sys.stdin)


def output_allow(message=None):
    if message:
        print(json.dumps({"decision": "allow", "system_message": message}))
    else:
        print(json.dumps({"decision": "allow"}))
    sys.exit(0)


def output_deny(reason):
    print(json.dumps({"decision": "deny", "reason": reason}))
    sys.exit(0)


def get_cwd(event):
    return event.get("cwd") or os.getcwd()


def git(cwd, *args):
    try:
        r = subprocess.run(
            ["git"] + list(args), cwd=cwd, capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return ""
        return r.stdout.strip()
    except Exception:
        return ""


def is_git_repo(cwd):
    return bool(git(cwd, "rev-parse", "--git-dir"))


def log_audit(cwd, message):
    try:
        log_dir = Path(cwd) / "production" / "session-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).isoformat()[:19]
        with open(log_dir / "agent-audit.log", "a") as f:
            f.write(f"{ts} | {message}\n")
    except Exception:
        pass


def timestamp():
    return datetime.now(timezone.utc).isoformat()[:19]


# ─── git-guard (pre_tool on bash) ──────────────────────────────────────────

def git_guard(event):
    tool_input = event.get("tool_input", {})
    cmd = tool_input.get("command", "")
    cwd = get_cwd(event)

    if not is_git_repo(cwd):
        output_allow()

    # Check for git push to protected branches
    if re.match(r"^git\s+push", cmd.strip()):
        branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
        for b in PROTECTED_BRANCHES:
            if branch == b or re.search(r"\s" + re.escape(b) + r"(\s|$)", cmd):
                log_audit(cwd, f"Push to protected branch '{b}' detected.")
                log_audit(cwd, "Reminder: Ensure build passes, tests pass, no S1/S2 bugs.")
                output_deny(
                    f"Push to protected branch '{b}' blocked by OCGS git-guard. "
                    "Ensure CI passes and no critical bugs before pushing."
                )
        output_allow()

    # Check for git commit — validate staged files
    if re.match(r"^git\s+commit", cmd.strip()):
        staged = git(cwd, "diff", "--cached", "--name-only")
        if not staged:
            output_allow()

        errors = []
        warnings = []
        for f in staged.split("\n"):
            if not f:
                continue
            fp = Path(cwd) / f
            if not fp.exists():
                continue

            # Design doc section check
            if f.startswith("design/gdd/") and f.endswith(".md"):
                content = fp.read_text(encoding="utf-8", errors="ignore")
                for section in DESIGN_SECTIONS:
                    if section.lower() not in content.lower():
                        warnings.append(f"DESIGN: {f} missing section: {section}")

            # JSON validity for data files
            if re.match(r"^assets/data/.*\.json$", f):
                try:
                    json.loads(fp.read_text(encoding="utf-8"))
                except Exception:
                    errors.append(f"BLOCKED: {f} is not valid JSON.")

            # Hardcoded gameplay values
            if f.startswith("src/gameplay/"):
                content = fp.read_text(encoding="utf-8", errors="ignore")
                if re.search(r"(damage|health|speed|rate|chance|cost|duration)\s*[:=]\s*\d+", content):
                    warnings.append(f"CODE: {f} may contain hardcoded gameplay values.")

            # TODO without owner tag
            if f.startswith("src/"):
                content = fp.read_text(encoding="utf-8", errors="ignore")
                if re.search(r"(TODO|FIXME|HACK)[^(]", content):
                    warnings.append(f"STYLE: {f} has TODO/FIXME without owner tag. Use TODO(name).")

        if errors:
            log_audit(cwd, "Commit blocked: " + "; ".join(errors))
            output_deny("\n".join(errors))

        for w in warnings:
            log_audit(cwd, w)

        if warnings:
            output_allow(f"OCGS commit warnings:\n" + "\n".join(warnings))

    output_allow()


# ─── file-validator (post_tool on write_file|edit) ─────────────────────────

def file_validator(event):
    tool_input = event.get("tool_input", {})
    tool_name = event.get("tool_name", "")
    cwd = get_cwd(event)

    file_path = tool_input.get("path") or tool_input.get("file_path") or ""
    if not file_path:
        output_allow()

    file_path = file_path.replace("\\", "/")
    fp = Path(cwd) / file_path if not os.path.isabs(file_path) else Path(file_path)

    warnings = []
    errors = []

    # Asset naming validation (match assets/ at start or after /)
    if re.search(r"(?:^|/)assets/", file_path):
        filename = os.path.basename(file_path)
        if re.search(r"[A-Z\s-]", filename) and not filename.endswith(".aseprite"):
            warnings.append(f"NAMING: {file_path} should be lowercase with underscores (got: {filename})")

        # JSON validity for asset data files
        if re.match(r".*/assets/data/.*\.json$", file_path) and fp.exists():
            try:
                json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                errors.append(f"FORMAT: {file_path} is not valid JSON")

    # GDD section validation (post-write advisory)
    if file_path.startswith("design/gdd/") and file_path.endswith(".md") and fp.exists():
        content = fp.read_text(encoding="utf-8", errors="ignore")
        missing = [s for s in DESIGN_SECTIONS if s.lower() not in content.lower()]
        if missing:
            warnings.append(f"DESIGN: {file_path} missing sections: {', '.join(missing)}")

    # Skill change detection
    skill_match = re.search(r"\.(?:opencode|agents)/(?:skills|commands)/([^/]+)", file_path)
    if skill_match:
        skill_name = skill_match.group(1)
        log_audit(cwd, f"Skill modified: {skill_name}")
        log_audit(cwd, f"Run /skill-test static {skill_name} to validate.")
        warnings.append(f"Skill '{skill_name}' modified — run /skill-test static {skill_name} to validate.")

    for w in warnings:
        log_audit(cwd, w)
    for e in errors:
        log_audit(cwd, e)

    if errors:
        output_deny("\n".join(errors))

    if warnings:
        output_allow(f"OCGS file validation:\n" + "\n".join(warnings))

    output_allow()


# ─── agent-audit (post_tool on task) ─────────────────────────────────────────

def agent_audit(event):
    tool_input = event.get("tool_input", {})
    tool_status = event.get("tool_status", "")
    cwd = get_cwd(event)

    agent_name = tool_input.get("agent", "unknown")
    if tool_status == "success":
        log_audit(cwd, f"Agent completed: {agent_name}")
    else:
        log_audit(cwd, f"Agent {tool_status}: {agent_name}")

    output_allow()


# ─── Main ───────────────────────────────────────────────────────────────────

DISPATCH = {
    "git-guard": git_guard,
    "file-validator": file_validator,
    "agent-audit": agent_audit,
}


def main():
    if len(sys.argv) < 2:
        sys.exit(0)

    hook_name = sys.argv[1]
    handler = DISPATCH.get(hook_name)
    if not handler:
        sys.exit(0)

    try:
        event = read_event()
        handler(event)
    except Exception as e:
        # Fail open — don't block on hook errors
        output_allow(f"OCGS hook '{hook_name}' error: {e}")


if __name__ == "__main__":
    main()
