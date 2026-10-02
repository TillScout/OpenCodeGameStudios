---
name: art-generate
description: "Generates placeholder art from asset specs using the Aseprite MCP (2D) or Blender MCP (3D). Reads asset specs and art bible, creates sprites or 3D blockout meshes with correct dimensions/palette/materials, exports PNGs or glTF. Run after /asset-spec has produced specs and /art-bible exists."
argument-hint: "[system:<name> | level:<name> | character:<name> | path/to/spec.md]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Write, Edit, Task, question
---

If no argument is provided, read `design/assets/asset-manifest.md`:
- If it exists: find the first target with any asset at `Status: Needed` and use `question`:
  - Prompt: "The next unspecced target is **[target]**. Generate placeholder art for it?"
  - Options: `[A] Yes — generate for [target]` / `[B] Pick a different target` / `[C] Stop here`
- If no manifest: fail with:
  > "No asset manifest found. Run `/asset-spec [target]` first — I need asset specs to generate art from."

---

## Phase 0: Parse Target

Resolve the target:
1. If argument matches `system:<name>` → spec at `design/assets/specs/[name]-assets.md`
2. If argument matches `level:<name>` → spec at `design/assets/specs/[name]-assets.md`
3. If argument matches `character:<name>` → spec at `design/assets/specs/[name]-assets.md`
4. If argument is a path → read that file directly
5. If argument is a path to a .md file → treat as spec file

Fail if the spec file does not exist:
> "No asset spec found at `[path]`. Run `/asset-spec [target]` first."

---

## Phase 1: Gather Context

Read all source material before generating anything.

### Required reads:
- **Asset spec**: Read the resolved spec file. Extract all `ASSET-NNN` entries. For each, extract: Category, Dimensions, Format, Naming, Visual Description, and any 3D-specific fields (Polycount, Texture Maps, Rig, LOD Levels).
- **Art bible**: Read `design/art/art-bible.md` — fail if missing:
  > "No art bible found. Run `/art-bible` first — I need the palette and shape language to generate art."
  Extract: Color System (Section 4 — including the 4b palette export,
  `design/art/palette.json`, which is the machine-readable input this skill
  consumes), Shape Language (Section 3), Asset Standards (Section 8 — dimension
  tiers, polycount tiers, texture map standards, rig standards, LOD strategy).
- **Asset manifest**: Read `design/assets/asset-manifest.md` — note which assets already have placeholders. Filter to assets with `Status: Needed`.

### Determine pipeline dimension

Classify each asset as 2D or 3D based on its Category field:
- **3D**: `3D Mesh`, `Material`, `VFX` (3D particle systems), `UI` (3D billboard)
- **2D**: `2D Art`, `Sprite`, `VFX` (2D particles), `UI` (screen-space bitmap)
- **Audio**: skip generation — audio specs are descriptions only

If the spec does not have a Category field, infer from Format: `.glb`/`.gltf`/`.fbx`/`.blend` → 3D; `.png`/`.aseprite`/`.svg` → 2D.

Present context summary:
> **art-generate: [Target Type] — [Target Name]**
> - Spec: [path] — [N] assets identified
> - Art bible: found — [N] palette colors, shape language: [style]
> - Pipeline: [N] 3D assets (Blender MCP) / [N] 2D assets (Aseprite MCP) / [N] audio (skip)
> - Assets to generate: [N] (filtered from [N] total — [N] already have placeholders)
> - Output 3D: assets/source/[target]/ (.blend) and assets/models/[target]/ (.glb)
> - Output 2D: assets/source/[target]/ (.aseprite) and assets/sprites/[target]/ (.png)

---

## Phase 2: Per-Asset Generation

For each asset with `Status: Needed`, execute the pipeline matching its
dimension classification. **Process one asset at a time — do NOT batch MCP
calls.**

Route to the correct sub-pipeline:
- 3D assets → **Phase 2A: 3D Pipeline (Blender MCP)**
- 2D assets → **Phase 2B: 2D Pipeline (Aseprite MCP)**

---

## Phase 2A: 3D Pipeline (Blender MCP)

> **Reference file:** For detailed bpy Python patterns, read
> `bpy-patterns.md` in this skill directory. It contains tested, reusable
> patterns for materials, primitives, modifiers, armatures, particles, UV
> unwrapping, shape keys, texture baking, export, and more. When unsure about
> an API, use `search_api_docs` or `get_python_api_docs` to look up the
> correct function signature.

All Blender operations go through a single MCP tool:
`execute_blender_code` with `{ code: "<python>" }`. The Python code runs in
Blender's environment with full access to `bpy`. To return data, assign a
JSON-serialisable dict to a variable named `result`.

Each step below is one `execute_blender_code` call with a complete Python
script. Do not split a step into multiple calls — combining operations in a
single script reduces round-trips and state-tracking errors.

---

### Step 2a-3d: Create Collection

Construct the filename as `assets/source/[target]/[naming]` (replace `.glb` or
similar with `.blend`).

Create a Blender collection for the asset to keep work isolated. Use the
asset's naming convention as the collection name:

```python
import bpy

col = bpy.data.collections.new("[naming]")
bpy.context.scene.collection.children.link(col)
# Make the new collection the active one so every bpy.ops.mesh.primitive_*_add()
# call in the following steps links its object into THIS collection
# (not the scene collection). This keeps the asset isolated for export.
layer_col = bpy.context.view_layer.layer_collection.children.get(col.name)
if layer_col:
    bpy.context.view_layer.active_layer_collection = layer_col
result = {"collection": col.name}
```

Wait for success. If the call fails, stop this asset and report.

**Important:** new objects created by `bpy.ops` operators land in the
*active* collection. The step above makes the asset collection active —
do not change the active collection again until this asset is exported.

### Step 2b-3d: Apply Material System

Create PBR materials from the art bible's color system. For each named color
in the art bible's palette that this asset uses, create a Blender material
with a Principled BSDF node. Convert hex colors from the art bible to linear
RGB values (divide 0-255 sRGB by 255, then apply gamma correction).

```python
import bpy

def make_material(name, color_rgba, roughness=0.5, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color_rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

def hex_to_rgba(hex_str):
    h = hex_str.lstrip("#")
    # Blender's Base Color expects LINEAR values — convert sRGB 0-255
    # to linear (approximate gamma 2.2 decode)
    def srgb_to_linear(c):
        return pow(c, 2.2)
    r, g, b = (srgb_to_linear(int(h[i:i+2], 16) / 255.0) for i in (0, 2, 4))
    return (r, g, b, 1.0)

# Create materials from art bible palette
mats = {}
for name, hex_val, rough, metal in [
    ("[Environment_Base]", "#4A3B2A", 0.7, 0.0),
    ("[Environment_Accent]", "#6B5A3A", 0.6, 0.0),
    ("[Character_Skin]", "#8B6B4A", 0.8, 0.0),
    # ... add all colors this asset uses
]:
    m = make_material(name, hex_to_rgba(hex_val), rough, metal)
    mats[name] = m

result = {"materials": list(mats.keys())}
```

If the art bible specifies roughness or metallic values in its material
direction, use those. Otherwise use sensible defaults (roughness 0.5,
metallic 0.0 for non-metal surfaces). If the art bible specifies emission
colors (for VFX), use the emission pattern from `bpy-patterns.md` section 1.

### Step 2c-3d: Create 3D Structure

Create primitive objects matching the asset category template. Position and
scale them to match the spec's dimensions (interpret pixel dimensions as world
units divided by 100, or use the spec's stated dimensions if already in world
units).

Define helper functions and use them to build the asset in a single call.
This is more reliable than multiple separate calls.

**Blockout / Environment Prop:**
```python
import bpy
import math

def add_cube(name, location=(0,0,0), scale=(1,1,1), material=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    if material:
        o.data.materials.append(material)
    return o

base = add_cube("base", scale=(0.5, 0.5, 0.5), material=bpy.data.materials.get("[Environment_Base]"))
details_01 = add_cube("details_01", location=(0, 0, 0.55), scale=(0.3, 0.3, 0.1),
                      material=bpy.data.materials.get("[Environment_Accent]"))
details_02 = add_cube("details_02", location=(0.15, 0, 0.55), scale=(0.1, 0.1, 0.15),
                      material=bpy.data.materials.get("[Environment_Accent]"))

result = {"objects": [base.name, details_01.name, details_02.name]}
```

**Character Mesh (blockout):**
```python
import bpy
import math

def add_cube(name, location=(0,0,0), scale=(1,1,1), material=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    if material:
        o.data.materials.append(material)
    return o

def add_cylinder(name, location=(0,0,0), radius=0.5, depth=1.0,
                 rotation=(0,0,0), material=None, vertices=8):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                          vertices=vertices, location=location)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rotation
    if material:
        o.data.materials.append(material)
    return o

def add_sphere(name, location=(0,0,0), radius=0.5, material=None, segments=8, ring_count=6):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments,
                                          ring_count=ring_count, location=location)
    o = bpy.context.active_object
    o.name = name
    if material:
        o.data.materials.append(material)
    return o

skin = bpy.data.materials.get("[Character_Skin]")
body = add_cube("body", location=(0, 0, 0.8), scale=(0.5, 0.8, 0.3), material=skin)
head = add_sphere("head", location=(0, 0, 1.25), radius=0.25, material=skin)
arm_l = add_cylinder("arm_l", location=(-0.35, 0, 0.8), radius=0.08, depth=0.4,
                     rotation=(0, math.radians(90), 0), material=skin)
arm_r = add_cylinder("arm_r", location=(0.35, 0, 0.8), radius=0.08, depth=0.4,
                     rotation=(0, math.radians(90), 0), material=skin)
leg_l = add_cylinder("leg_l", location=(-0.15, 0, 0.3), radius=0.1, depth=0.5, material=skin)
leg_r = add_cylinder("leg_r", location=(0.15, 0, 0.3), radius=0.1, depth=0.5, material=skin)

# Parent all parts to body
for child in [head, arm_l, arm_r, leg_l, leg_r]:
    child.parent = body

result = {"objects": [body.name, head.name, arm_l.name, arm_r.name, leg_l.name, leg_r.name]}
```

For VFX / Particle Systems, UI Elements (3D billboards), and other templates,
follow the Per-Category 3D Templates section below. Use the primitive helpers
from `bpy-patterns.md` section 2.

### Step 2d-3d: Add Placeholder Geometry Detail

Apply basic mesh operations to make the blockout read clearly. Match the art
bible's shape language. Both modifier types can be applied in the same
`execute_blender_code` call:

```python
import bpy

def add_modifier(obj_name, mod_type, **kwargs):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return False
    mod = obj.modifiers.new(mod_type, mod_type)
    for key, val in kwargs.items():
        setattr(mod, key, val)
    return True

# Organic/curved geometry → subdivision surface
add_modifier("body", "SUBSURF", levels=2)
add_modifier("head", "SUBSURF", levels=2)

# Angular/geometric geometry → bevel
add_modifier("arm_l", "BEVEL", width=0.02, segments=2)
add_modifier("arm_r", "BEVEL", width=0.02, segments=2)

result = {"modifiers_applied": True}
```

For boolean operations (cutting holes, combining shapes), see the boolean
pattern in `bpy-patterns.md` section 3.

### Step 2e-3d: Handle Rigging

If the spec indicates the asset is a character or animated object (Rig: Yes
in the spec), create a simple armature. For placeholder purposes, a simple
armature with the major bones is sufficient — the goal is a rig that can be
posed, not a production-ready deformation rig.

```python
import bpy

def create_armature(name, bone_defs):
    """bone_defs: list of (name, head, tail, parent_name_or_None)"""
    bpy.ops.object.armature_add(enter_editmode=True)
    arm_obj = bpy.context.active_object
    arm_obj.name = name
    # Remove default bone
    if arm_obj.data.edit_bones:
        default = arm_obj.data.edit_bones[0]
        arm_obj.data.edit_bones.remove(default)
    bones = {}
    for bone_name, head, tail, parent_name in bone_defs:
        bone = arm_obj.data.edit_bones.new(bone_name)
        bone.head = head
        bone.tail = tail
        if parent_name and parent_name in bones:
            bone.parent = bones[parent_name]
        bones[bone_name] = bone
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj

def parent_mesh_to_armature(mesh_name, armature_name):
    mesh = bpy.data.objects.get(mesh_name)
    arm = bpy.data.objects.get(armature_name)
    if not mesh or not arm:
        return False
    mesh.parent = arm
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return True

bone_defs = [
    ("Hips",      (0, 0, 0.8), (0, 0, 1.0), None),
    ("Spine",     (0, 0, 1.0), (0, 0, 1.3), "Hips"),
    ("Head",      (0, 0, 1.3), (0, 0, 1.6), "Spine"),
    ("ArmL_U",    (0, 0, 1.25), (-0.4, 0, 1.1), "Spine"),
    ("ArmL_L",    (-0.4, 0, 1.1), (-0.4, 0, 0.75), "ArmL_U"),
    ("ArmR_U",    (0, 0, 1.25), (0.4, 0, 1.1), "Spine"),
    ("ArmR_L",    (0.4, 0, 1.1), (0.4, 0, 0.75), "ArmR_U"),
    ("LegL_U",    (0, 0, 0.8), (-0.15, 0, 0.4), "Hips"),
    ("LegL_L",    (-0.15, 0, 0.4), (-0.15, 0, 0.0), "LegL_U"),
    ("LegR_U",    (0, 0, 0.8), (0.15, 0, 0.4), "Hips"),
    ("LegR_L",    (0.15, 0, 0.4), (0.15, 0, 0.0), "LegR_U"),
]

arm = create_armature("rig", bone_defs)
parent_mesh_to_armature("body", "rig")

result = {"armature": arm.name, "bone_count": len(arm.data.bones)}
```

For automatic weight painting, use the `parent_with_auto_weights` pattern from
`bpy-patterns.md` section 6.

Do NOT attempt to create walk cycles or keyframed animation in the
placeholder. The placeholder is a T-posed mesh with optional rig. Animation
is a production step, not a placeholder step.

If the spec does not indicate animation, skip this step — a static blockout
mesh is enough.

### Step 2f-3d: Export

Export to glTF (binary glTF is the default and most widely supported format
across Godot, Unity, Unreal, and Bevy). Also save the source `.blend` file.
For `.gltf` (separate textures) or `.fbx`, use the patterns in
`bpy-patterns.md` section 13.

```python
import bpy
import os

# Use ABSOLUTE paths — Blender's working directory is NOT the project root.
# Resolve the repo root from the asset spec path you read in Phase 1.
project_root = "/absolute/path/to/repo"  # ← replace with the real repo root
out_dir = os.path.join(project_root, "assets/models/[target]")
src_dir = os.path.join(project_root, "assets/source/[target]")
os.makedirs(out_dir, exist_ok=True)
os.makedirs(src_dir, exist_ok=True)

# Select ONLY this asset's objects so the export contains nothing else
# (other assets in the scene, default Cube/Camera/Light).
col = bpy.data.collections.get("[naming]")
bpy.ops.object.select_all(action='DESELECT')
export_objects = list(col.objects) if col else []
for o in export_objects:
    o.select_set(True)

# Export .glb
bpy.ops.export_scene.gltf(
    filepath=os.path.join(out_dir, "[naming].glb"),
    use_selection=True,
    export_format='GLB',
    export_apply=True,
    export_yup=True,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_cameras=True,
    export_animations=True,
)

# Save .blend source
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(src_dir, "[naming].blend"))

result = {
    "glb_path": os.path.join(out_dir, "[naming].glb"),
    "blend_path": os.path.join(src_dir, "[naming].blend"),
    "exported_objects": [o.name for o in export_objects],
}
```

After exporting, if more assets remain in this run, optionally clean the
scene with the cleanup patterns from `bpy-patterns.md` section 14 so the
next asset starts from an empty scene (the per-asset `.blend` source was
already saved). Only remove objects this run created — never objects
that were already in the scene.

If the technical-artist prefers `.gltf` with separate textures, or `.fbx`,
use that format instead — consult `docs/framework/technical-preferences.md`.
Export patterns for all three formats are in `bpy-patterns.md` section 13.

### Step 2g-3d: Verify

Verify the output using two approaches:

**1. Structural verification** — Call `get_objects_summary({})` via the Blender
MCP. Confirm:
- All expected objects exist in the scene
- The parenting hierarchy is correct (e.g., body parts parented to the body)
- Objects are in the right collections

```python
# Inline structural check (alternative to get_objects_summary)
import bpy

expected = ["body", "head", "arm_l", "arm_r", "leg_l", "leg_r"]
missing = [n for n in expected if n not in bpy.data.objects]
result = {
    "missing": missing,
    "total_objects": len(bpy.data.objects),
    "all_present": len(missing) == 0,
}
```

**2. Visual verification** — Call
`render_viewport_to_path({ output_path: "/tmp/[naming]_preview.png" })` via
the Blender MCP. This renders the current viewport. Use it to visually confirm
the asset matches the spec — correct proportions, materials applied, shape
language matches the art bible.

Also verify:
- The exported `.glb` file exists at the expected path
- The `.blend` source file exists
- If rigged, the armature has the expected bone count (use
  `get_object_detail_summary({ name: "rig" })` to inspect the armature)

For detailed object inspection — checking materials, modifiers, and
transforms on a specific object — call
`get_object_detail_summary({ name: "[object_name]" })`.

---

## Phase 2B: 2D Pipeline (Aseprite MCP)

### Step 2a-2d: Create Canvas

Construct the filename as `assets/source/[target]/[naming]` (replace `.png` or
similar with `.aseprite`).

Use the `create_canvas` MCP tool:
```
create_canvas(width, height, filename)
```

Wait for success. If it fails, stop this asset and report.

### Step 2b-2d: Apply Palette

Load the art bible palette. If the art bible specifies a named palette
resource (e.g., "DB16", "RPG"), use:

```
load_palette_from_resource(filename, resource_name)
```

Otherwise extract hex colors from the art bible's Color System section and
apply:

```
set_palette(filename, [hex_colors_array])
```

### Step 2c-2d: Create Layer Structure

Create layers matching the asset category template:

**Sprite / 2D Art:**
```
add_layer(filename, "body")
set_layer(filename, "body")
set_layer_label_color(filename, "body", color_hex)
add_layer(filename, "details")
add_layer(filename, "outline")
```

**UI Icon:**
```
add_layer(filename, "icon")
```

**VFX (2D):**
```
add_layer(filename, "core")
set_layer_blend_mode(filename, "core", "normal")
add_layer(filename, "glow")
set_layer_blend_mode(filename, "glow", "add")
add_layer(filename, "sparks")
```

**Environment (2D):**
```
add_layer(filename, "base")
add_layer(filename, "shading")
add_layer(filename, "details")
```

**Character Sprite:**
```
add_layer(filename, "body")
add_layer(filename, "head")
add_layer(filename, "arms")
add_layer(filename, "legs")
add_layer(filename, "outline")
```

### Step 2d-2d: Draw Placeholder Content

Draw shapes on each layer following the art bible's shape language. Use the
semantic color from the art bible for the asset's role.

General approach per layer:
1. `set_layer(filename, layer_name)` — activate the layer
2. `set_frame(filename, 1)` — draw on frame 1
3. Draw shapes:
   - **Body/base**: Fill a rectangle/circle/polygon covering ~80% of the canvas at the body center position
   - **Details**: Smaller shapes offset from center, using secondary/accent colors from the palette
   - **Outline**: Thin rectangle around the body bounds using a dark color

Use these drawing tools as appropriate:
- `draw_rectangle_at(filename, layer, frame, x, y, w, h, color, fill=true)` for blocky shapes
- `draw_circle_at(filename, layer, frame, cx, cy, r, color, fill=true)` for round shapes
- `draw_polygon(filename, layer, frame, points, color, fill=true)` for angular shapes (character limbs)
- `fill_area_at(filename, layer, frame, cx, cy, color)` for filled regions
- `apply_gradient_rect(filename, layer, frame, x, y, w, h, start, end, horizontal)` for gradient fills

### Step 2e-2d: Handle Animation

If the spec indicates multiple frames (e.g., "4-frame sprite sheet"):

```
add_frames(filename, count=3, duration_ms=200)  # frame 1 already exists
set_frame_duration(filename, 1, 200)
```

For each additional frame, duplicate frame 1 and add minor position offsets for limbs:
```
copy_frame(filename, source_frame=1, target_frame=N)
```

Then tag the animation:
```
set_tag(filename, name="default", from_frame=1, to_frame=N, direction="forward")
```

If not animated, skip this step.

### Step 2f-2d: Export

```
export_sprite(filename, output_path="assets/sprites/[target]/[naming]")
```

### Step 2g-2d: Verify

Use the quality tools to check the output:

```
validate_scene(filename, required_layers=[list from step 2c-2d])
```

Expected: JSON confirming all layers and frames exist.

Also verify the exported file exists:
```
ls "assets/sprites/[target]/[naming]"
```

Expected: `True`

---

## Error Handling (Both Pipelines)

If any MCP tool call fails:
```
Question: "Tool [tool_name] failed for ASSET-[NNN] ([asset name]): [error]. Options:"
A) Retry this asset
B) Skip this asset, continue with next
C) Stop generation entirely
```

Blender-specific failures to handle:
- `execute_blender_code` returns a Python traceback — read the error line and fix the specific `bpy` call. Common causes: wrong operator name, missing context override, object not found by name.
- Mesh creation failure — check Blender is running with the MCP add-on enabled and connected (the `blender-mcp` subprocess must reach Blender via `BLENDER_MCP_HOST`/`BLENDER_MCP_PORT`)
- Modifier stack error — simplify modifier parameters and retry. Use `get_object_detail_summary` to inspect the current modifier stack.
- Armature binding failure — verify bone names match the hierarchy. Use `get_object_detail_summary({ name: "rig" })` to inspect the armature.
- Export path permission error — ensure output directories exist before exporting (use `os.makedirs` in the Python script) and use absolute paths. If Blender runs on a different machine than the agent (e.g. via an MCP bridge), the path must be valid and writable from Blender's machine.
- API uncertainty — use `search_api_docs` to look up the correct function name or `get_python_api_docs` for a specific identifier before guessing.

Aseprite-specific failures to handle:
- Canvas creation failure — check Aseprite is installed and ASEPRITE_PATH is set
- Palette resource unknown — fall back to `set_palette` with hex colors from art bible
- Export fails — check file path permissions, suggest manual export

---

## Phase 3: Update Manifest

After all assets are generated (or after partial completion), update
`design/assets/asset-manifest.md`.

For each generated asset, change its status from `Needed` to
`Placeholder Created`. Add a `Source` column if it doesn't exist:

```
| ASSET-001 | hero-mesh | 3D Mesh | Placeholder Created | design/assets/specs/hero-assets.md | assets/source/hero/ASSET-001-hero-mesh.blend |
| ASSET-002 | hero-portrait | 2D Art | Placeholder Created | design/assets/specs/hero-assets.md | assets/source/hero/ASSET-002-hero-portrait.aseprite |
```

If the manifest doesn't have a `Source` column yet, rewrite the header to
include it.

---

## Phase 4: Summary Report

Present a completion summary:

> **art-generate complete for [target]:**
> - [N]/[M] assets generated successfully
> - [N] 3D assets (Blender) — output: assets/source/[target]/ (.blend), assets/models/[target]/ (.glb)
> - [N] 2D assets (Aseprite) — output: assets/source/[target]/ (.aseprite), assets/sprites/[target]/ (.png)
> - [N] failed (skipped)
> - Manifest updated: design/assets/asset-manifest.md

---

## Phase 5: Next Steps

Use `question`:
- Prompt: "Placeholder art generated for **[target]**. What's next?"
- Options:
  - `[A] Generate another target — /art-generate [next-target]`
  - `[B] Run /asset-audit — validate generated assets against specs`
  - `[C] Review generated art manually`
  - `[D] Stop here`

---

## Per-Category 3D Templates

### Blockout / Environment Prop (3D)

```
Collection: [naming]
Objects: base (cube), details_01 (cube), details_02 (cube)
Materials: [Environment_Base] on base, [Environment_Accent] on details
Modifiers: subdivision on base (if organic), bevel on details (if angular)
Rig: None
Export: assets/models/[target]/[naming].glb
```

### Character Mesh (3D)

```
Collection: [naming]
Objects: body (cube), head (sphere), arm_l/arm_r (cylinders), leg_l/leg_r (cylinders)
Parenting: head, arms, legs parented to body
Materials: [Character_Body] on body, [Character_Skin] on head and arms, [Character_Legs] on legs
Modifiers: subdivision on body and head (organic), bevel on limbs (angular)
Rig: Simple armature (hips, spine, head, upper/lower arm_l/r, upper/lower leg_l/r)
Export: assets/models/[target]/[naming].glb
```

### VFX / Particle System (3D)

```
Collection: [naming]
Objects: vfx_core (icosphere)
Materials: [VFX_Glow] (emission, high roughness)
Particle system: ambient_particles, 100 particles, 60-frame lifetime
Rig: None
Export: assets/models/[target]/[naming].glb
```

### UI Element (3D Billboard)

```
Collection: [naming]
Objects: ui_icon (plane)
Materials: [UI_Primary] (unshaded)
Rig: None
Export: assets/models/[target]/[naming].glb
```

### Generic Prop / Blockout (3D)

```
Collection: [naming]
Objects: base (cube or cylinder), top (cube or sphere)
Materials: [Prop_Base] on base, [Prop_Accent] on top
Modifiers: subdivision or bevel per art bible shape language
Rig: None
Export: assets/models/[target]/[naming].glb
```

---

## Per-Category 2D Templates

### Sprite / 2D Asset (Default)

```
Canvas: spec dimensions (e.g. 256x256)
Layers: body, details, outline

Frame 1:
  layer=body:   fill_rect(32, 32, 192, 192, body_color)
  layer=details: draw_rect(48, 48, 160, 160, accent_color, fill=false)
  layer=outline: draw_rect(30, 30, 196, 196, outline_color, fill=false)
```

### UI Icon

```
Canvas: 32x32 or 64x64
Layers: icon

Frame 1:
  layer=icon: fill_rect(4, 4, 24, 24, palette[0])
```

### VFX (2D)

```
Canvas: matching target sprite dimensions
Layers: core, glow, sparks

Frame 1:
  layer=core: circle(center, radius*0.3, core_color, fill=true)
  layer=glow: circle(center, radius, glow_color, fill=true, set opacity=128)
```

### Environment Prop (2D)

```
Canvas: tile dimensions
Layers: base, shading, details

Frame 1:
  layer=base: fill_rect(0, 0, w, h, base_color)
  layer=shading: gradient_rect(0, 0, w, h, shade_top, shade_bottom)
```

### Character Sprite (2D)

```
Canvas: sprite sheet width, frame height
Layers: body, head, arms, legs, outline

Frame 1 (idle pose):
  layer=body:   fill_rect(24, 40, 16, 24, body_color)
  layer=head:   fill_rect(28, 24, 8, 12, skin_color)
  layer=arms:   fill_rect(16, 44, 8, 8, skin_color)
               draw_rect(40, 44, 8, 8, skin_color)
  layer=legs:   fill_rect(24, 64, 6, 12, leg_color)
               fill_rect(34, 64, 6, 12, leg_color)
  layer=outline: draw_rect(22, 22, 20, 54, outline)

Frame 2 (walk frame 1): copy_frame(1, 2)
  layer=legs: offset legs by +2 on x to show stride
```

---

## Error Recovery

| Error | Pipeline | Recovery |
|-------|----------|----------|
| Spec file not found | Both | Fail with clear message pointing to /asset-spec |
| Art bible not found | Both | Fail — generation without palette produces wrong colors |
| Blender MCP not connected | 3D | Check Blender is running with the MCP add-on enabled. Verify the `blender-mcp` subprocess can reach Blender via `BLENDER_MCP_HOST`/`BLENDER_MCP_PORT` (see `.vibe/config.toml` or `opencode.json` for the configured host/port) |
| `execute_blender_code` Python traceback | 3D | Read the error line, fix the specific `bpy` call. Use `search_api_docs` to look up correct function names |
| Blender mesh creation failure | 3D | Check Blender is running and MCP server is connected. Use `get_objects_summary` to inspect scene state |
| Blender modifier error | 3D | Use `get_object_detail_summary` to inspect the modifier stack, simplify parameters and retry |
| Blender armature binding failure | 3D | Use `get_object_detail_summary({ name: "rig" })` to verify bone names and hierarchy |
| Blender export fails | 3D | Ensure output directories exist (`os.makedirs`). Check file path permissions, try alternative format (.gltf or .fbx) |
| Blender API uncertainty | 3D | Use `search_api_docs` or `get_python_api_docs` to look up the correct API before guessing |
| Aseprite MCP not connected | 2D | Check Aseprite is installed and ASEPRITE_PATH is set |
| MCP tool timeout | Both | Report tool + args that failed, offer retry/skip/stop |
| Palette resource unknown | 2D | Fall back to `set_palette` with hex colors from art bible |
| Aseprite export fails | 2D | Check file path permissions, suggest manual export |
| `validate_scene` fails | 2D | Report which layers/frames are missing, offer to fix |

## Collaborative Protocol

- Never generate without user confirming the target
- Report each asset's success/failure immediately after processing it
- Write the manifest update only after explicit approval
- If the art bible's palette has changed since the spec was written, ask which to use
