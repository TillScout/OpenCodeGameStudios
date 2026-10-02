#!/usr/bin/env python3
"""
Copy OCGS framework files to a new project folder.
Preserves .agents/ structure, creates .vibe/config.toml with MCP servers,
and generates Vibe subagent profiles in .vibe/agents/.

Usage:
    python copy_ocgs.py /path/to/your/new/project
"""
import os
import shutil
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).parent.resolve()

# Files to copy (relative to SOURCE_ROOT)
FILES_TO_COPY = [
    ".agents/agents",
    ".agents/commands",
    ".agents/mcp",
    ".agents/modules",
    ".agents/skills",
    "docs/framework",
]

# Entries from FILES_TO_COPY that are copied file-by-file without ever
# overwriting: an existing destination file blocks only the file of the same
# name, not the whole directory.
NO_OVERWRITE = ["docs/framework"]


def copy_ocgs_framework(target_dir: Path):
    target_dir = target_dir.resolve()

    for rel_path in FILES_TO_COPY:
        src = SOURCE_ROOT / rel_path
        dst = target_dir / rel_path
        if not src.exists():
            print(f"Skipped (not found): {rel_path}")
            continue
        if rel_path in NO_OVERWRITE:
            copied = kept = 0
            for s in sorted(src.rglob("*")):
                if s.is_dir():
                    continue
                d = dst / s.relative_to(src)
                if d.exists():
                    kept += 1
                    continue
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
                copied += 1
            print(f"Copied {copied} new file(s) -> {dst} ({kept} existing file(s) kept)")
        elif dst.exists():
            shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"Copied: {rel_path} -> {dst}")
        else:
            shutil.copytree(src, dst)
            print(f"Copied: {rel_path} -> {dst}")

    # Create .vibe/config.toml
    vibe_dir = target_dir / ".vibe"
    vibe_dir.mkdir(exist_ok=True)

    config_path = vibe_dir / "config.toml"
    config_content = """[skills]
skill_paths = [".agents/skills", ".agents/modules/*/skills"]

[[mcp_servers]]
name = "beckett"
transport = "streamable-http"
url = "http://127.0.0.1:8770/mcp/c2cc10448ba30a863b6dae5772ed5748"

[[mcp_servers]]
name = "blender"
transport = "stdio"
command = "uvx"
args = [
    "--from",
    "git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp",
    "blender-mcp"
]

[mcp_servers.env]
BLENDER_MCP_HOST = "10.0.2.2"
BLENDER_MCP_PORT = "9876"
"""

    if not config_path.exists() or input(f"Overwrite {config_path}? [y/N]: ").lower() == "y":
        config_path.write_text(config_content)
        print(f"Created: .vibe/config.toml")
    else:
        print(f"Skipped: .vibe/config.toml (already exists)")

    # Generate Vibe subagent profiles from the OCGS agent definitions
    generate_vibe_agents(target_dir)


def generate_vibe_agents(target_dir: Path):
    """Generate .vibe/agents/<name>.toml subagent profiles for the target project.

    Vibe's subagent registry only discovers TOML profiles (in .vibe/agents/,
    ~/.vibe/agents/, or agent_paths); it never parses the Claude-Code-family
    .md definitions. OCGS skills spawn agents by bare name (e.g.
    "game-designer"), and the registry key is the TOML filename, so profiles
    are generated under the same names.

    Conversion logic is imported from tools/sync-vibe.py to keep a single
    source of truth for the .md -> TOML mapping.
    """
    import importlib.util

    sync_path = SOURCE_ROOT / "tools" / "sync-vibe.py"
    spec = importlib.util.spec_from_file_location("sync_vibe", sync_path)
    sync_vibe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync_vibe)

    src_agents = SOURCE_ROOT / ".agents" / "agents"
    dst = target_dir / ".vibe" / "agents"
    dst.mkdir(parents=True, exist_ok=True)

    count = 0
    for src_file in sorted(src_agents.glob("*.md")):
        slug = src_file.stem
        toml = sync_vibe.convert_agent(src_file, slug)
        (dst / f"{slug}.toml").write_text(toml, encoding="utf-8")
        count += 1
    print(f"Generated {count} Vibe agent profiles -> {dst}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python copy_ocgs.py /path/to/new/project")
        sys.exit(1)

    target = Path(sys.argv[1])
    copy_ocgs_framework(target)
    print("\nDone. Restart Vibe in the target directory.")
