# Art Module Refactor: Aseprite/2D → Blender/3D

## Goal

Refactor the OCGS art module (`.agents/modules/art/`) from a 2D pixel-art
pipeline built around the Aseprite MCP to a 3D pipeline built around a
Blender MCP. The framework's art pipeline should produce 3D assets — meshes,
materials, rigs, glTF exports — instead of 2D sprites, while keeping the
collaborative workflow, approval gates, and document-driven design
philosophy intact.

The art bible, asset spec, and audit skills are largely dimension-agnostic
already. The hard coupling to Aseprite and 2D is concentrated in the
`art-generate` skill. That skill needs a full rewrite. The other files need
targeted adjustments.

---

## Scope of Changes

### 1. Rewrite `art-generate/SKILL.md` (full rewrite)

**Current state:** 321 lines, every MCP tool call is an Aseprite primitive
(`create_canvas`, `set_palette`, `add_layer`, `draw_rectangle_at`,
`export_sprite`, etc.). Layer templates are 2D sprite structures
(body/details/outline). Animation is cel-style frame duplication. Output is
PNG sprites.

**Desired outcome:** A 3D placeholder art generation skill that drives a
Blender MCP server. The skill should follow the same 5-phase structure
(target resolution → context gathering → per-asset generation → manifest
update → summary) and the same collaborative protocol (one asset at a time,
user confirms target, manifest update after approval, error
retry/skip/stop). But every tool call, layer template, drawing step, and
export step changes.

#### Phase 0 and Phase 1 — unchanged structure

The target resolution logic (`system:<name>`, `level:<name>`,
`character:<name>`, path argument, manifest fallback) stays the same. The
context gathering (read asset spec, read art bible, read manifest) stays
the same. The context summary presentation stays the same.

#### Phase 2 — per-asset generation pipeline (rewrite entirely)

Replace the 7-step Aseprite pipeline with a 7-step Blender pipeline:

**Step 2a: Create scene/collection**

Instead of `create_canvas(width, height, filename)`, create a Blender
collection for the asset:

```
create_collection(name)
```

If the Blender MCP supports scene creation, create a new scene per asset
to keep work isolated. The collection name should match the asset naming
convention.

**Step 2b: Apply material system**

Instead of loading a flat color palette into Aseprite, create PBR
materials from the art bible's color system:

```
create_material(name, base_color_hex, roughness, metallic)
```

For each named color in the art bible's palette, create a Blender
material with:
- Base color from the palette hex
- Roughness and metallic values from the art bible's material direction
  (if specified) or sensible defaults (roughness 0.5, metallic 0.0)
- Named to match the semantic color role (e.g., "Danger_Red",
  "Primary_Blue")

If the art bible specifies a named palette resource, the materials should
still be derived from the hex values — Blender materials are PBR, not
indexed palette entries.

**Step 2c: Create 3D structure (replace layer templates)**

Replace the 2D layer templates with 3D object/collection structures per
category:

**Blockout / Environment Prop:**
```
create_primitive(type="cube", size=[w, h, d], name="base")
create_primitive(type="cube", size=[w2, h2, d2], name="details_01")
create_primitive(type="cube", size=[w3, h3, d3], name="details_02")
assign_material(object="base", material="Environment_Base")
assign_material(object="details_01", material="Environment_Accent")
```

**Character Mesh (blockout):**
```
create_primitive(type="cube", name="body", size=[0.5, 0.8, 0.3])
create_primitive(type="sphere", name="head", size=0.25)
create_primitive(type="cylinder", name="arm_l", size=[0.08, 0.4, 0.08])
create_primitive(type="cylinder", name="arm_r", size=[0.08, 0.4, 0.08])
create_primitive(type="cylinder", name="leg_l", size=[0.1, 0.5, 0.1])
create_primitive(type="cylinder", name="leg_r", size=[0.1, 0.5, 0.1])
parent_object(child="head", parent="body")
parent_object(child="arm_l", parent="body")
parent_object(child="arm_r", parent="body")
parent_object(child="leg_l", parent="body")
parent_object(child="leg_r", parent="body")
```

Position child objects relative to the body (head above body, arms at
sides, legs below). This is a blockout — primitive shapes in the right
proportions, not a sculpted mesh.

**VFX / Particle System:**
```
create_particle_system(object="vfx_core", name="ambient_particles")
set_particle_count(object="vfx_core", system="ambient_particles", count=100)
set_particle_lifetime(object="vfx_core", system="ambient_particles", frames=60)
```

**UI Element (3D billboard):**
```
create_primitive(type="plane", name="ui_icon", size=[0.5, 0.5])
assign_material(object="ui_icon", material="UI_Primary")
set_shading_mode(object="ui_icon", mode="unshaded")
```

**Step 2d: Add placeholder geometry detail**

Instead of drawing pixel shapes, apply basic mesh operations to make the
blockout read clearly:

- Apply subdivision surface modifier for smoother shapes where the art
  bible specifies organic/curved geometry
- Apply bevel modifier for hard-surface edges where the art bible
  specifies angular/geometric geometry
- Scale and position objects to match the asset spec's dimensions
  (interpret "256x256" as a 2.56x2.56 unit footprint in Blender, or use
  the spec's stated dimensions if they are already in world units)

Use these Blender MCP tools as available:
```
add_modifier(object, modifier_type="subdivision", levels=2)
add_modifier(object, modifier_type="bevel", width=0.02)
set_position(object, [x, y, z])
set_scale(object, [sx, sy, sz])
```

**Step 2e: Handle rigging (replace cel animation)**

If the spec indicates the asset is a character or animated object:

```
create_armature(name="rig", bones=[...])
parent_object_with_armature(object="body", armature="rig")
```

For placeholder purposes, a simple armature with the major bones
(hips, spine, head, upper_arm_l/r, lower_arm_l/r, upper_leg_l/r,
lower_leg_l/r) is sufficient. The goal is a rig that can be posed, not
a production-ready deformation rig.

If the spec does not indicate animation, skip this step — a static
blockout mesh is enough.

Do NOT attempt to create walk cycles or keyframed animation in the
placeholder. The placeholder is a posed or T-posed mesh with optional
rig. Animation is a production step, not a placeholder step.

**Step 2f: Export**

Instead of `export_sprite(filename, output_path)`, export to glTF:

```
export_gltf(path="assets/models/[target]/[naming].glb")
```

Export as `.glb` (binary glTF) by default — it is the most widely
supported 3D format across Godot, Unity, Unreal, and Bevy. If the engine
specialist prefers `.gltf` with separate textures, or `.fbx`, use that
format instead.

Also save the source `.blend` file:

```
save_blend(path="assets/source/[target]/[naming].blend")
```

**Step 2g: Verify**

Instead of `validate_scene`, verify:

- The exported `.glb` file exists at the expected path
- The `.blend` source file exists
- The object count in the collection matches the expected structure
  (e.g., character blockout should have 6+ objects: body, head, arms,
  legs)
- If rigged, the armature has the expected bone count

#### Per-category templates (rewrite all)

Replace all 2D drawing templates in the "Per-Category Drawing Templates"
section with 3D blockout equivalents. Each template should specify:
- Object primitives to create and their dimensions
- Materials to assign
- Modifier stack (subdivision for organic, bevel for hard-surface)
- Rigging instructions (if applicable)
- Export format and path

Keep the template categories the same (Environment Prop, Character,
VFX, UI Element) but add a **Generic Prop / Blockout** category for
non-character, non-environment 3D assets.

#### Error handling

Keep the same error handling structure (retry/skip/stop per asset) but
replace Aseprite tool names with Blender tool names. Add handling for
Blender-specific failures: mesh creation failure, modifier stack error,
armature binding failure, export path permission error.

#### What to keep identical

- Phase 0 (target resolution) — unchanged
- Phase 1 (context gathering, required reads, context summary) — unchanged
- Phase 3 (manifest update: flip Status from "Needed" to "Placeholder
  Created", add Source column) — unchanged, but Source points to `.blend`
  file, not `.aseprite`
- Phase 4 (summary report) — unchanged structure, update output paths
  from `assets/sprites/` to `assets/models/` and `assets/source/` stays
  the same
- Phase 5 (next steps) — unchanged
- Collaborative protocol — unchanged
- The `question`-based interaction pattern — unchanged

---

### 2. Create `mcp/blender.json` (new file)

Create a new MCP server configuration file at
`.agents/modules/art/mcp/blender.json` analogous to `mcp/aseprite.json`.

The exact command, transport, and arguments depend on which Blender MCP
server is chosen. Two community options exist:

1. **blender-mcp** (ahujasid/blender-mcp) — stdio transport, requires
   the Blender MCP add-on installed in Blender and Blender running with
   the add-on enabled. The MCP server connects to Blender via a local
   socket.
2. **Blender's built-in MCP server** (Blender 4.2+, `blender --background
   --python-expr "..."` with MCP via the `bpy` module) — streamable HTTP.

The configuration should follow this pattern (using blender-mcp as
example):

```json
{
  "blender": {
    "type": "local",
    "command": ["uvx", "blender-mcp"],
    "enabled": true,
    "environment": {
      "BLENDER_PATH": "{env:BLENDER_PATH}"
    }
  }
}
```

Also add the Blender MCP server to `opencode.json` (under `"mcp"`) and
`.vibe/config.toml` (under `[[mcp_servers]]`), mirroring how Aseprite and
Beckett are already configured.

Remove or disable the Aseprite MCP entry in `opencode.json` and
`.vibe/config.toml` if the project is fully 3D. If the project may need
both 2D and 3D art, keep both entries but set Aseprite to `enabled: false`.

---

### 3. Update `modulefile.yaml`

**File:** `.agents/modules/art/modulefile.yaml`

Changes:
- `description`: Change from "Aseprite MCP, art generation, art bible,
  asset specs. Visual identity and production pipeline." to "Blender MCP,
  3D art generation, art bible, asset specs. Visual identity and
  production pipeline."
- `provides.mcp`: Change from `[aseprite]` to `[blender]` (or include
  both if keeping 2D support: `[aseprite, blender]`)
- `plugged-into.engines`: Change from `[godot]` to include 3D-capable
  engines: `[godot, unity, unreal, bevy]`. The art module is not
  engine-specific — the MCP generates assets that any engine can import.

---

### 4. Update `asset-spec/SKILL.md`

**File:** `.agents/modules/art/skills/asset-spec/SKILL.md`

#### 4a. Reorder asset categories (Phase 2)

The current category list leads with 2D categories:

```
- Sprite / 2D Art — character sprites, UI icons, tile sheets
- VFX / Particles — hit effects, ambient particles, screen effects
- Environment — props, tiles, backgrounds, skyboxes
- UI — HUD elements, menu art, fonts (if custom)
- Audio — SFX, music tracks, ambient loops
- 3D Assets — meshes, materials (if applicable per engine)
```

Change to lead with 3D categories:

```
- 3D Mesh — character meshes, environment props, blockout geometry
- Material / Texture — PBR materials, texture maps, material assignments
- VFX / Particles — particle systems, hit effects, ambient effects
- UI — HUD elements, menu art, icons (billboard or screen-space)
- Audio — SFX, music tracks, ambient loops
- 2D Art — sprites, tile sheets, UI bitmaps (if applicable per engine)
```

Move "2D Art" to last position with the "if applicable" guard, mirroring
how "3D Assets" currently sits with that guard.

#### 4b. Update the spec template (Phase 4)

The current spec template has these fields:

```
| Category | [Sprite / VFX / Environment / UI / Audio / 3D] |
| Dimensions | [e.g. 256×256px, 4-frame sprite sheet] |
| Format | [PNG / SVG / WAV / etc.] |
| Naming | [e.g. vfx_frost_hit_01.png] |
| Polycount | [if 3D — e.g. <800 tris] |
| Texture Res | [e.g. 512px — matches Art Bible §8 Tier 2] |
```

Change to:

```
| Category | [3D Mesh / Material / VFX / UI / Audio / 2D Art] |
| Dimensions | [e.g. 2.0×2.0×3.0 world units, or 256×256px if 2D] |
| Format | [GLB / FBX / blend / PNG / WAV / etc.] |
| Naming | [e.g. char_hero_idle.glb] |
| Polycount | [e.g. <2000 tris — matches Art Bible §8 Tier 1] |
| Texture Maps | [e.g. albedo 512px, normal 512px, roughness 256px] |
| Rig | [Yes/No — if Yes, skeleton type: humanoid/bipedal/custom] |
| LOD Levels | [e.g. 3 (LOD0 <2000, LOD1 <1000, LOD2 <500)] |
```

Remove the "if 3D" guard from Polycount — polycount is always relevant
for 3D assets. Add the three new fields (Texture Maps, Rig, LOD Levels)
unconditionally for 3D Mesh and Material categories.

#### 4c. Update asset identification (Phase 2)

The "For systems" and "For levels" identification instructions currently
look for "sprite references" and "tile sheets". Add: "mesh references,
material assignments, model imports, rig requirements". For characters,
add: "3D mesh (idle, walk, attack poses for rig reference), portrait/
avatar, VFX attached to abilities".

---

### 5. Update `art-bible/SKILL.md` Section 8

**File:** `.agents/modules/art/skills/art-bible/SKILL.md`

Section 8 (Asset Standards) currently spawns `art-director` and
`technical-artist` in parallel and asks them for file format
preferences, naming conventions, texture resolution tiers, LOD
expectations, and "poly count budgets per asset category". The
technical-artist is already asked for "poly count budgets" — but the
skill does not explicitly guide what 3D pipeline standards to cover.

Add to the `technical-artist` task in Section 8:

> "For 3D assets, also specify: mesh format (glTF/FBX), polycount tiers
> per asset category (hero prop, environment prop, character, background
> element), texture map types and resolution per map type (albedo,
> normal, roughness, metallic, AO, emission), rig standards (bone count
> limits, humanoid vs custom skeleton), LOD strategy (number of levels,
> polycount reduction per level), and material standards (PBR workflow:
> metallic-roughness vs specular, texture compression format)."

Add to the `art-director` task in Section 8:

> "For 3D assets, also specify: silhouette readability at game camera
> distance, material style (hand-painted textures vs PBR vs stylized
> PBR), and whether the game uses baked or real-time lighting (this
> affects texture map requirements)."

---

### 6. Update `asset-audit/SKILL.md`

**File:** `.agents/modules/art/skills/asset-audit/SKILL.md`

#### 6a. Add 3D file extensions to Glob patterns (Phase 2)

Current art glob:
```
Glob pattern="assets/art/**/*.{png,jpg,svg,psd,tres,tscn}"
```

Add:
```
Glob pattern="assets/models/**/*.{glb,gltf,fbx,blend}"
Glob pattern="assets/materials/**/*.{mat,mtl,tres}"
```

#### 6b. Add 3D texture map checks (Phase 3, new section 3f)

Add a new compliance check section:

```
### 3f: 3D Asset Completeness

For each .glb/.gltf/.fbx file, check for companion texture maps:
- Albedo/Base Color map
- Normal map
- Roughness map
- Metallic map (if metallic workflow)
- AO map (if specified in art bible)

Flag any 3D model that is missing required texture maps per the art bible
Section 8 standards.

Also check:
- Rig presence: if the spec says "Rig: Yes", verify the exported file
  contains an armature/skeleton
- LOD files: if the spec specifies LOD levels, verify LOD files exist
  or the glTF contains LOD meshes
```

#### 6c. Update the file size budget table (Phase 3, section 3b)

Add 3D-specific rows:

```
| 3D Models (character) | < 10 MB | < 200 MB |
| 3D Models (environment) | < 5 MB | < 100 MB |
| 3D Models (blockout) | < 1 MB | < 20 MB |
| Texture maps (per map) | < 4 MB | < 100 MB |
| Blend source files | < 50 MB | < 500 MB |
```

---

### 7. Update `art-bible` template

**File:** `docs/framework/templates/art-bible.md`

In the "Asset Production Standards" section, add a "3D Pipeline
Standards" subsection:

```markdown
### 3D Pipeline Standards

#### Mesh Format
[glTF/GLB / FBX / both — which format for which use case]

#### Polycount Tiers
| Category | LOD0 | LOD1 | LOD2 |
|----------|------|------|------|
| Characters | [N tris] | [N tris] | [N tris] |
| Environment Props | [N tris] | [N tris] | [N tris] |
| Background | [N tris] | [N tris] | [N tris] |

#### Texture Map Standards
| Map Type | Resolution | Format | Color Space |
|----------|-----------|--------|-------------|
| Albedo | [Size] | [Format] | sRGB |
| Normal | [Size] | [Format] | Linear |
| Roughness | [Size] | [Format] | Linear |
| Metallic | [Size] | [Format] | Linear |
| AO | [Size] | [Format] | Linear |

#### Rigging Standards
[Skeleton type, bone count limits, naming convention for bones]

#### LOD Strategy
[Number of levels, reduction ratio, distance thresholds]
```

Also update the "Rendering Style" line to lead with 3D options:

```
[Realistic / Stylized / Hand-painted / Cel-shaded / Low-poly / etc.]
```

And update "Environment Art Standards" to replace "Tilesets,
modularity" with "Modular props, environment kits, lighting setups,
scale reference".

---

## Files That Do NOT Need Changes

- **`art-director.md`** — already dimension-neutral. Mentions both
  "pixel/3D art" in the must-not section. Responsibilities
  (art bible, style enforcement, asset specs, color/lighting direction)
  are dimension-agnostic.
- **`technical-artist.md`** — already leans 3D. Responsibilities
  include "polygon counts, texture sizes, UV density, mesh optimization,
  LOD systems, occlusion, batching". No changes needed.
- **`art-bible/SKILL.md` Sections 1-7** — visual identity, color system,
  shape language, mood/atmosphere, character/environment/UI direction,
  reference direction are all dimension-agnostic. Only Section 8 needs
  the 3D additions described above.
- **`shader-code.md`** rule — already covers both `spatial_` and
  `canvas_` shader types. The naming convention
  (`[type]_[category]_[name].[ext]`) works for both 2D and 3D shaders.
- **All engine specialist agents** — they already handle both 2D and 3D.
  The Godot specialist mentions both, Unity/Unreal/Bevy specialists are
  3D-capable.

---

## Implementation Order

1. **Create `mcp/blender.json`** and add to `opencode.json` +
   `.vibe/config.toml` — so the MCP server is available before the skill
   that uses it.
2. **Rewrite `art-generate/SKILL.md`** — the largest change, depends on
   knowing which Blender MCP tools are available.
3. **Update `asset-spec/SKILL.md`** — reorder categories, update spec
   template fields.
4. **Update `art-bible/SKILL.md` Section 8** — add 3D pipeline standards
   to the technical-artist and art-director task prompts.
5. **Update `asset-audit/SKILL.md`** — add 3D extensions, texture map
   checks, 3D budget rows.
6. **Update `art-bible` template** — add 3D standards subsection.
7. **Update `modulefile.yaml`** — description, MCP list, engine list.
8. **Remove or disable Aseprite entries** in `opencode.json` and
   `.vibe/config.toml` if the project is fully 3D.

Steps 3-7 are independent of each other and can be done in any order after
step 1. Step 2 is the critical path.

---

## Open Decisions

Before starting implementation, the following must be decided:

1. **Which Blender MCP server to use.** The `art-generate` skill's tool
   calls depend on which MCP server is available. The two main options
   are `blender-mcp` (ahujasid, stdio, requires Blender running with
   add-on) and Blender 4.2+'s built-in MCP (streamable HTTP). The tool
   names and capabilities differ between them. This decision gates step 2.

2. **Whether to keep 2D/Aseprite support alongside 3D/Blender.** If the
   project may need both (e.g., 3D world with 2D UI elements), keep both
   MCP entries and make `art-generate` detect the asset category to route
   to the right pipeline. If the project is fully 3D, remove Aseprite
   entirely.

3. **Whether `art-generate` should be one skill or two.** If both 2D and
   3D are needed, the cleanest approach may be to split `art-generate`
   into `art-generate-2d` (Aseprite) and `art-generate-3d` (Blender), with
   the manifest or spec category determining which to invoke. The
   current single-skill approach would require branching on category
   type throughout Phase 2.
