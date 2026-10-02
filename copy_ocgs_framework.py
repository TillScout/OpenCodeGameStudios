#!/usr/bin/env python3
"""
Copy minimal OCGS framework (skills, agents, MCP configs) from a source repo
and set up the Vibe config so skills are discovered.

Run from the TARGET project root.
Usage: python3 copy_ocgs_framework.py [SOURCE_PATH]

Default SOURCE_PATH: /home/till/projects/OpenCodeGameStudios
"""

import fnmatch
import os
import shutil
import sys

# --- CONFIG ---
SOURCE_ROOT = sys.argv[1] if len(sys.argv) > 1 else "/home/till/projects/OpenCodeGameStudios"

# Files/dirs to copy (relative to SOURCE_ROOT)
COPY_SPEC = [
    (".agents/skills",        ["*.md"]),           # SKILL.md + support files (recursive)
    (".agents/agents",        ["*.md"]),           # Agent definitions
    (".agents/mcp",           ["*.json"]),          # MCP server definitions
    (".agents/commands",      ["*.md"]),           # Command definitions
    ("docs/framework",        ["*.md", "*.yaml"]),  # Framework reference docs (recursive)
    # Module files for art (Blender pipeline)
    (".agents/modules/art/skills/art-generate", ["*.md"]),
    (".agents/modules/art/agents",             ["*.md"]),
    (".agents/modules/art/commands",           ["*.md"]),
    (".agents/modules/art/mcp",               ["*.json"]),
]

# COPY_SPEC entries whose files are never overwritten: an existing
# destination file blocks only the file of the same name, not the whole
# directory. All other entries overwrite as before.
NO_OVERWRITE_DIRS = {"docs/framework"}

# Vibe config template with skill_paths and MCP servers
VIBE_CONFIG = """# Vibe configuration for OCGS projects with Blender + Beckett MCP

[tools.skill]
skill_paths = [".agents/skills", ".agents/modules/*/skills"]

[[mcp_servers]]
name = "beckett"
transport = "streamable-http"
url = "http://127.0.0.1:8770/mcp/c2cc10448ba30a863b6dae5772ed5748"

[[mcp_servers]]
name = "blender"
transport = "stdio"
command = "uvx"
args = ["--from", "git+https://projects.blender.org/lab/blender_mcp.git#subdirectory=mcp", "blender-mcp"]

[mcp_servers.env]
BLENDER_MCP_HOST = "127.0.0.1"
BLENDER_MCP_PORT = "9876"
"""


def generate_vibe_agents(src, dst):
    """Generate .vibe/agents/<name>.toml subagent profiles from the OCGS agent
    .md definitions in the source repo.

    Vibe's subagent registry only discovers TOML profiles (in .vibe/agents/,
    ~/.vibe/agents/, or agent_paths); the Claude-Code-family .md files are
    never parsed. OCGS skills spawn agents by bare name (e.g. "game-designer"),
    and the registry key is the TOML filename, so profiles are generated under
    the same names. Conversion logic is imported from the source repo's
    tools/sync-vibe.py to keep a single source of truth.
    """
    import importlib.util
    from pathlib import Path

    sync_path = Path(src) / "tools" / "sync-vibe.py"
    if not sync_path.is_file():
        print(f"  skipped .vibe/agents generation ({sync_path} not found)")
        return
    spec = importlib.util.spec_from_file_location("sync_vibe", sync_path)
    sync_vibe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync_vibe)

    agents_dst = Path(dst) / ".vibe" / "agents"
    agents_dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for src_file in sorted((Path(src) / ".agents" / "agents").glob("*.md")):
        slug = src_file.stem
        toml = sync_vibe.convert_agent(src_file, slug)
        (agents_dst / f"{slug}.toml").write_text(toml, encoding="utf-8")
        count += 1
    print(f"  generated {count} Vibe agent profiles -> {agents_dst}")


def main():
    src = os.path.abspath(SOURCE_ROOT)
    dst = os.getcwd()
    if not os.path.isdir(src):
        print(f"Error: Source not found: {src}")
        sys.exit(1)

    # ---- Copy framework files ----
    copied = []
    for rel_dir, patterns in COPY_SPEC:
        src_dir = os.path.join(src, rel_dir)
        dst_dir = os.path.join(dst, rel_dir)
        if not os.path.isdir(src_dir):
            print(f"  skipped {rel_dir} (not found in source)")
            continue
        # Walk the tree recursively so nested content (skill directories,
        # framework subdirectories like templates/) is picked up too.
        for root, _dirs, files in os.walk(src_dir):
            rel_root = os.path.relpath(root, src_dir)
            target_dir = dst_dir if rel_root == "." else os.path.join(dst_dir, rel_root)
            os.makedirs(target_dir, exist_ok=True)
            for f in sorted(files):
                if any(fnmatch.fnmatch(f, pat) for pat in patterns):
                    rel = f"{rel_dir}/{f}" if rel_root == "." else f"{rel_dir}/{rel_root}/{f}"
                    dst_file = os.path.join(target_dir, f)
                    if rel_dir in NO_OVERWRITE_DIRS and os.path.exists(dst_file):
                        print(f"  kept existing {rel}")
                        continue
                    shutil.copy2(
                        os.path.join(root, f),
                        dst_file
                    )
                    copied.append(rel)
                    print(f"  copied  {rel}")

    # ---- Create .vibe/config.toml ----
    vibe_dir = os.path.join(dst, ".vibe")
    os.makedirs(vibe_dir, exist_ok=True)
    config_path = os.path.join(vibe_dir, "config.toml")
    with open(config_path, "w") as fh:
        fh.write(VIBE_CONFIG)
    print(f"  created {config_path}")

    # ---- Generate Vibe subagent profiles ----
    generate_vibe_agents(src, dst)

    # ---- Create marker file ----
    marker_dir = os.path.join(dst, "agents")
    os.makedirs(marker_dir, exist_ok=True)
    with open(os.path.join(marker_dir, ".ocgs-minimal"), "w") as fh:
        fh.write(f"# Minimal OCGS framework copy\n# Source: {src}\n# Date: {os.popen('date').read().strip()}\n")
    print(f"  created agents/.ocgs-minimal")

    if copied:
        print(f"\nDone. {len(copied)} framework files + Vibe config copied to: {dst}")
    else:
        print(f"\nWarning: NO framework files were copied. Check SOURCE_ROOT={src}")
    print("\nNext: Run 'vibe' in this directory. Skills should now be detected.")

if __name__ == "__main__":
    main()
