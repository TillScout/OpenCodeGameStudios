# bpy Patterns for Blender MCP

Reference Python patterns for driving Blender via the official Blender MCP
(`projects.blender.org/lab/blender_mcp`). All operations go through a single
MCP tool: `execute_blender_code` with `{ code: "<python>" }`.

Every code block is a self-contained script. Assign a dict to `result` to
return data to the caller.

When unsure about an API, use `search_api_docs` (full-text search over the
bundled Blender Python API reference) or `get_python_api_docs` (lookup a
fully-qualified identifier like `bpy.ops.export_scene.gltf`).

---

## 1. PBR Materials

### Standard PBR material (Principled BSDF)

```python
import bpy

def make_material(name, color_rgba, roughness=0.5, metallic=0.0):
    """Create a PBR material with a Principled BSDF node."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color_rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat

# Usage
mat = make_material("HeroSkin", (0.15, 0.35, 0.12, 1.0), roughness=0.8)
mat_metal = make_material("Armor", (0.12, 0.10, 0.08, 1.0), roughness=0.4, metallic=0.7)

result = {"created": [mat.name, mat_metal.name]}
```

### Emission material (VFX glow)

```python
import bpy

def make_emission_material(name, color_rgba, strength=5.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Emission Color"].default_value = color_rgba
    bsdf.inputs["Emission Strength"].default_value = strength
    # Set base color dark so emission dominates
    bsdf.inputs["Base Color"].default_value = (0, 0, 0, 1)
    return mat

mat = make_emission_material("VFX_Glow", (0.2, 0.8, 1.0, 1.0), strength=8.0)
result = {"created": mat.name}
```

### Node-based material (mix two shaders)

```python
import bpy

def make_mixed_material(name, color_a, color_b, mix_factor=0.5, roughness=0.5):
    """Mix two Principled BSDF shaders via a Mix node."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    # Clear default nodes
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bsdf_a = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf_a.inputs["Base Color"].default_value = color_a
    bsdf_b.inputs["Base Color"].default_value = color_b
    bsdf_a.inputs["Roughness"].default_value = roughness
    bsdf_b.inputs["Roughness"].default_value = roughness
    mix.inputs["Fac"].default_value = mix_factor
    nt.links.new(bsdf_a.outputs["BSDF"], mix.inputs[1])
    nt.links.new(bsdf_b.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat

mat = make_mixed_material("MixedMetal", (0.8, 0.6, 0.2, 1), (0.2, 0.2, 0.25, 1), 0.3)
result = {"created": mat.name}
```

### Procedural noise texture on a material

```python
import bpy

def make_noise_material(name, base_color, noise_scale=10.0, roughness=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = noise_scale
    cramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(noise.outputs["Fac"], cramp.inputs["Fac"])
    nt.links.new(cramp.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = roughness
    # Set color ramp to interpolate between base_color and a darker variant
    cramp.color_ramp.elements[0].color = (base_color[0]*0.3, base_color[1]*0.3, base_color[2]*0.3, 1)
    cramp.color_ramp.elements[1].color = base_color
    return mat

mat = make_noise_material("StoneWall", (0.5, 0.48, 0.42, 1.0), noise_scale=15.0)
result = {"created": mat.name}
```

### Assign material to object

```python
import bpy

def assign_material(obj_name, mat_name):
    obj = bpy.data.objects.get(obj_name)
    mat = bpy.data.materials.get(mat_name)
    if not obj or not mat:
        return False
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    return True

ok = assign_material("Body", "HeroSkin")
result = {"assigned": ok}
```

---

## 2. Primitives

### Primitive creation helpers

```python
import bpy
import math

def add_cube(name, location=(0,0,0), scale=(1,1,1), rotation=(0,0,0), size=1.0):
    bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.rotation_euler = rotation
    return o

def add_sphere(name, location=(0,0,0), radius=0.5, segments=12, ring_count=8):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments,
                                          ring_count=ring_count, location=location)
    o = bpy.context.active_object
    o.name = name
    return o

def add_cylinder(name, location=(0,0,0), radius=0.5, depth=1.0,
                 rotation=(0,0,0), vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                          vertices=vertices, location=location)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rotation
    return o

def add_cone(name, location=(0,0,0), radius1=0.5, radius2=0.0, depth=1.0,
             rotation=(0,0,0), vertices=12):
    bpy.ops.mesh.primitive_cone_add(radius1=radius1, radius2=radius2,
                                     depth=depth, vertices=vertices, location=location)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rotation
    return o

def add_plane(name, location=(0,0,0), scale=(1,1,1), size=1.0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=location)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    return o

def add_torus(name, location=(0,0,0), major_radius=1.0, minor_radius=0.25,
              major_segments=12, minor_segments=8):
    bpy.ops.mesh.primitive_torus_add(major_radius=major_radius,
                                      minor_radius=minor_radius,
                                      major_segments=major_segments,
                                      minor_segments=minor_segments, location=location)
    o = bpy.context.active_object
    o.name = name
    return o

def add_icosphere(name, location=(0,0,0), radius=0.5, subdivisions=2):
    bpy.ops.mesh.primitive_ico_sphere_add(radius=radius, subdivisions=subdivisions, location=location)
    o = bpy.context.active_object
    o.name = name
    return o

result = {"status": "helpers defined"}
```

### Low-poly variants (reduce vertex count)

```python
# Run in the SAME execute_blender_code call as the primitive helpers above —
# each call is a fresh Python scope, so helpers do not persist between calls.
import bpy
import math

def add_cube(name, location=(0,0,0), scale=(1,1,1)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    return o

def add_sphere(name, location=(0,0,0), radius=0.5, segments=12, ring_count=8):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments,
                                          ring_count=ring_count, location=location)
    o = bpy.context.active_object
    o.name = name
    return o

def add_cylinder(name, location=(0,0,0), radius=0.5, depth=1.0,
                 rotation=(0,0,0), vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                          vertices=vertices, location=location)
    o = bpy.context.active_object
    o.name = name
    o.rotation_euler = rotation
    return o

# For low-poly aesthetics, use fewer segments/rings:
body = add_cube("Body", location=(0,0,1), scale=(0.45, 0.28, 0.4))
head = add_sphere("Head", location=(0,0,1.85), radius=0.25, segments=6, ring_count=4)
arm_l = add_cylinder("ArmL", location=(-0.4,0,1.0), radius=0.08, depth=0.5,
                      rotation=(0, math.radians(90), 0), vertices=6)

result = {"objects": [body.name, head.name, arm_l.name]}
```

---

## 3. Modifiers

### Bevel

```python
import bpy

obj = bpy.data.objects.get("Body")
if obj:
    bev = obj.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.02
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bev.angle_limit = 0.523599  # 30 degrees

result = {"modifier": "Bevel" if obj else "not found"}
```

### Subdivision surface

```python
import bpy

obj = bpy.data.objects.get("Body")
if obj:
    subdiv = obj.modifiers.new("Subdivision", "SUBSURF")
    subdiv.levels = 2
    subdiv.render_levels = 3

result = {"modifier": "Subdivision" if obj else "not found"}
```

### Boolean (cut one shape from another)

```python
import bpy

def apply_boolean(target_name, cutter_name, operation="DIFFERENCE"):
    """Apply a boolean modifier and then remove the cutter object."""
    target = bpy.data.objects.get(target_name)
    cutter = bpy.data.objects.get(cutter_name)
    if not target or not cutter:
        return False
    mod = target.modifiers.new("Boolean", "BOOLEAN")
    mod.operation = operation
    mod.object = cutter
    # Apply the modifier
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    # Remove the cutter
    bpy.data.objects.remove(cutter, do_unlink=True)
    return True

ok = apply_boolean("Wall", "WindowCutout", "DIFFERENCE")
result = {"applied": ok}
```

### Decimate (for LOD generation)

```python
import bpy

def make_lod(source_name, lod_name, ratio=0.5):
    """Duplicate an object and decimate it to the given ratio."""
    source = bpy.data.objects.get(source_name)
    if not source:
        return None
    bpy.ops.object.select_all(action='DESELECT')
    source.select_set(True)
    bpy.context.view_layer.objects.active = source
    bpy.ops.object.duplicate()
    lod = bpy.context.active_object
    lod.name = lod_name
    decimate = lod.modifiers.new("Decimate", "DECIMATE")
    decimate.ratio = ratio
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    return lod.name

lod1 = make_lod("CharacterMesh", "CharacterMesh_LOD1", ratio=0.5)
lod2 = make_lod("CharacterMesh", "CharacterMesh_LOD2", ratio=0.25)
result = {"lods": [lod1, lod2]}
```

---

## 4. Parenting and Hierarchy

### Simple parenting

```python
import bpy

def parent_to(child_name, parent_name):
    child = bpy.data.objects.get(child_name)
    parent = bpy.data.objects.get(parent_name)
    if not child or not parent:
        return False
    child.parent = parent
    # Keep visual position by setting the parent inverse
    child.matrix_parent_inverse = parent.matrix_world.inverted()
    return True

parent_to("Head", "Body")
parent_to("ArmL", "Body")
result = {"parented": True}
```

### Parent to an empty (group root)

```python
import bpy

def create_group_root(name, child_names, location=(0,0,0)):
    bpy.ops.object.empty_add(location=location)
    root = bpy.context.active_object
    root.name = name
    for child_name in child_names:
        child = bpy.data.objects.get(child_name)
        if child and child.parent is None:
            child.parent = root
    return root

root = create_group_root("OrcSoldier", ["Body", "Head", "ArmL", "ArmR", "LegL", "LegR"])
result = {"root": root.name, "children": [c.name for c in root.children]}
```

---

## 5. Collections

### Create and link to a collection

```python
import bpy

def create_collection(name, object_names=None):
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    if object_names:
        for obj_name in object_names:
            obj = bpy.data.objects.get(obj_name)
            if obj:
                # Unlink from scene collection if linked there
                for c in obj.users_collection:
                    c.objects.unlink(obj)
                col.objects.link(obj)
    return col

col = create_collection("HeroAssets", ["Body", "Head"])
result = {"collection": col.name, "objects": [o.name for o in col.objects]}
```

### Move objects between collections

```python
import bpy

def move_to_collection(obj_name, col_name):
    obj = bpy.data.objects.get(obj_name)
    col = bpy.data.collections.get(col_name)
    if not obj or not col:
        return False
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)
    return True

ok = move_to_collection("Weapon", "HeroAssets")
result = {"moved": ok}
```

---

## 6. Armatures

### Create armature with named bones

```python
import bpy

def create_armature(name, bone_defs):
    """bone_defs: list of (name, head, tail, parent_name_or_None)"""
    bpy.ops.object.armature_add(enter_editmode=True)
    arm_obj = bpy.context.active_object
    arm_obj.name = name
    arm_obj.data.name = name + "_Data"
    # Remove the default bone
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

bone_defs = [
    ("Hips",     (0, 0, 0.8), (0, 0, 1.0), None),
    ("Spine",    (0, 0, 1.0), (0, 0, 1.3), "Hips"),
    ("Head",     (0, 0, 1.3), (0, 0, 1.6), "Spine"),
    ("ArmL_U",   (0, 0, 1.25), (-0.4, 0, 1.1), "Spine"),
    ("ArmL_L",   (-0.4, 0, 1.1), (-0.4, 0, 0.75), "ArmL_U"),
    ("ArmR_U",   (0, 0, 1.25), (0.4, 0, 1.1), "Spine"),
    ("ArmR_L",   (0.4, 0, 1.1), (0.4, 0, 0.75), "ArmR_U"),
    ("LegL_U",   (0, 0, 0.8), (-0.15, 0, 0.4), "Hips"),
    ("LegL_L",   (-0.15, 0, 0.4), (-0.15, 0, 0.0), "LegL_U"),
    ("LegR_U",   (0, 0, 0.8), (0.15, 0, 0.4), "Hips"),
    ("LegR_L",   (0.15, 0, 0.4), (0.15, 0, 0.0), "LegR_U"),
]

arm = create_armature("CharacterRig", bone_defs)
result = {"armature": arm.name, "bones": [b.name for b in arm.data.bones]}
```

### Parent mesh to armature with deform

```python
import bpy

def parent_mesh_to_armature(mesh_name, armature_name):
    mesh = bpy.data.objects.get(mesh_name)
    arm = bpy.data.objects.get(armature_name)
    if not mesh or not arm:
        return False
    mesh.parent = arm
    mod = mesh.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return True

ok = parent_mesh_to_armature("Body", "CharacterRig")
result = {"parented": ok}
```

### Parent multiple meshes to armature with automatic weights

```python
import bpy

def parent_with_auto_weights(mesh_names, armature_name):
    arm = bpy.data.objects.get(armature_name)
    if not arm:
        return False
    bpy.ops.object.select_all(action='DESELECT')
    for name in mesh_names:
        m = bpy.data.objects.get(name)
        if m:
            m.select_set(True)
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
    return True

ok = parent_with_auto_weights(["Body", "Head", "ArmL", "ArmR"], "CharacterRig")
result = {"parented": ok}
```

---

## 7. Particle Systems

### Ambient particle system

```python
import bpy

def add_particle_system(obj_name, sys_name, count=100, lifetime=60):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return False
    mod = obj.modifiers.new(sys_name, "PARTICLE_SYSTEM")
    # The auto-created particle system does NOT inherit the modifier's name —
    # access it through the modifier's pointer, not by name lookup.
    psys = mod.particle_system
    settings = psys.settings
    settings.count = count
    settings.lifetime = lifetime
    settings.emit_from = 'VOLUME'
    settings.physics_type = 'NO'
    return True

ok = add_particle_system("VFX_Core", "AmbientParticles", count=200, lifetime=60)
result = {"added": ok}
```

### Hair particle system

```python
import bpy

def add_hair(obj_name, sys_name, count=1000, hair_length=0.5):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return False
    mod = obj.modifiers.new(sys_name, "PARTICLE_SYSTEM")
    # Access the psys via the modifier pointer — the auto-created
    # particle system has a default name, not the modifier's name.
    psys = mod.particle_system
    settings = psys.settings
    settings.type = 'HAIR'
    settings.count = count
    settings.hair_length = hair_length
    return True

ok = add_hair("Scalp", "HairStrands", count=500, hair_length=0.3)
result = {"added": ok}
```

---

## 8. UV Unwrapping

### Smart UV unwrap

```python
import bpy

def smart_unwrap(obj_name):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return False
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=66, island_margin=0.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    return True

ok = smart_unwrap("Body")
result = {"unwrapped": ok}
```

### Cylinder-based UV projection

```python
import bpy

def cylinder_unwrap(obj_name):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return False
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cylinder_project()
    bpy.ops.object.mode_set(mode='OBJECT')
    return True

ok = cylinder_unwrap("Pillar")
result = {"unwrapped": ok}
```

---

## 9. Shape Keys

### Create shape keys for facial expressions

```python
import bpy

def add_shape_key(obj_name, key_name):
    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != 'MESH':
        return False
    # Ensure a Basis shape key exists
    if not obj.data.shape_keys:
        obj.shape_key_add(name="Basis", from_mix=False)
    key = obj.shape_key_add(name=key_name, from_mix=False)
    return key.name

def set_shape_key_vertex(obj_name, key_name, vertex_index, new_co):
    obj = bpy.data.objects.get(obj_name)
    if not obj or not obj.data.shape_keys:
        return False
    key = obj.data.shape_keys.key_blocks.get(key_name)
    if not key:
        return False
    key.data[vertex_index].co = new_co
    return True

# Create a "MouthOpen" shape key and move some vertices
key = add_shape_key("Head", "MouthOpen")
# Move vertices 10-15 downward on Z (example)
for vi in range(10, 16):
    co = bpy.data.objects["Head"].data.vertices[vi].co
    set_shape_key_vertex("Head", "MouthOpen", vi, (co.x, co.y, co.z - 0.1))

result = {"shape_key": key, "vertices_moved": 6}
```

---

## 10. Custom Properties and Drivers

### Add custom property to an object

```python
import bpy

def add_custom_property(obj_name, prop_name, default=0.0, min_val=0.0, max_val=1.0):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return False
    obj[prop_name] = default
    obj.property_overridable_library_set(f'["{prop_name}"]', True)
    # Set property UI metadata
    ui = obj.id_properties_ui(prop_name)
    ui.update(min=min_val, max=max_val, description=prop_name)
    return True

ok = add_custom_property("CharacterMesh", "health_pct", 1.0, 0.0, 1.0)
result = {"added": ok}
```

### Driver: link shape key to custom property

```python
import bpy

def add_shape_key_driver(obj_name, key_name, prop_name):
    """Drive a shape key's value from a custom property on the object."""
    obj = bpy.data.objects.get(obj_name)
    if not obj or not obj.data.shape_keys:
        return False
    key = obj.data.shape_keys.key_blocks.get(key_name)
    if not key:
        return False
    fcurve = key.driver_add("value")
    driver = fcurve.driver
    driver.type = 'SCRIPTED'
    driver.expression = prop_name
    var = driver.variables.new()
    var.name = prop_name
    var.targets[0].id_type = 'OBJECT'
    var.targets[0].id = obj
    var.targets[0].data_path = f'["{prop_name}"]'
    return True

ok = add_shape_key_driver("Head", "MouthOpen", "mouth_open")
result = {"driver_added": ok}
```

---

## 11. Texture Baking

### Bake ambient occlusion to texture

```python
import bpy

def bake_ao(obj_name, image_size=512, output_path="/tmp/baked_ao.png"):
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return False
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Create a texture image
    img = bpy.data.images.new(f"{obj_name}_AO", width=image_size, height=image_size)

    # Create or find a UV-mapped material with an image node
    mat = obj.data.materials[0] if obj.data.materials else None
    if not mat:
        return False

    # Add an image texture node for baking target
    nt = mat.node_tree
    img_node = nt.nodes.new("ShaderNodeTexImage")
    img_node.image = img
    nt.nodes.active = img_node

    # Configure bake settings
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.bake_type = 'AO'
    bpy.context.scene.render.bake.margin = 16
    bpy.ops.object.bake(type='AO')

    # Save the baked image
    img.filepath_raw = output_path
    img.file_format = 'PNG'
    img.save()

    return True

ok = bake_ao("Body", image_size=512, output_path="/tmp/baked_ao.png")
result = {"baked": ok}
```

---

## 12. Animation Keyframing

### Insert keyframes for object location

```python
import bpy

def keyframe_location(obj_name, frames_and_positions):
    """frames_and_positions: list of (frame, (x, y, z))"""
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return False
    for frame, pos in frames_and_positions:
        bpy.context.scene.frame_set(frame)
        obj.location = pos
        obj.keyframe_insert(data_path="location")
    return True

keyframe_location("Camera", [
    (1, (7, -5, 4)),
    (30, (3, -3, 3)),
    (60, (0, -2, 2)),
])
result = {"keyframed": True}
```

### Insert keyframes for shape key values

```python
import bpy

def keyframe_shape_key(obj_name, key_name, frames_and_values):
    """frames_and_values: list of (frame, value 0.0-1.0)"""
    obj = bpy.data.objects.get(obj_name)
    if not obj or not obj.data.shape_keys:
        return False
    key = obj.data.shape_keys.key_blocks.get(key_name)
    if not key:
        return False
    for frame, value in frames_and_values:
        bpy.context.scene.frame_set(frame)
        key.value = value
        key.keyframe_insert(data_path="value")
    return True

keyframe_shape_key("Head", "MouthOpen", [
    (1, 0.0),
    (15, 1.0),
    (30, 0.0),
])
result = {"keyframed": True}
```

---

## 13. Export

### Export to .glb (binary glTF, default)

```python
import bpy

def export_glb(path):
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLB',
        export_apply=True,          # Apply modifiers before exporting
        export_yup=True,            # Y-up for most engines
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
        export_cameras=True,
        export_animations=True,
    )
    return True

ok = export_glb("assets/models/hero/hero_mesh.glb")
result = {"exported": ok}
```

### Export to .gltf (separate textures)

```python
import bpy

def export_gltf(path):
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format='GLTF_SEPARATE',  # .gltf + .bin + textures
        export_apply=True,
        export_yup=True,
        export_texcoords=True,
        export_normals=True,
        export_materials='EXPORT',
        export_cameras=True,
        export_animations=True,
    )
    return True

ok = export_gltf("assets/models/hero/hero_mesh.gltf")
result = {"exported": ok}
```

### Export to .fbx

```python
import bpy

def export_fbx(path):
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=False,
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        bake_anim=True,
        use_mesh_modifiers=True,
        mesh_smooth_type='OFF',    # No auto-smooth for low-poly
        use_custom_props=True,
    )
    return True

ok = export_fbx("assets/models/hero/hero_mesh.fbx")
result = {"exported": ok}
```

### Save .blend source file

```python
import bpy
import os

def save_blend(path):
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    return True

ok = save_blend("assets/source/hero/hero_mesh.blend")
result = {"saved": ok}
```

---

## 14. Scene Cleanup

### Remove objects, materials, and collections

```python
import bpy

def remove_object(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)
        return True
    return False

def remove_material(name):
    mat = bpy.data.materials.get(name)
    if mat:
        bpy.data.materials.remove(mat)
        return True
    return False

def remove_collection(name):
    col = bpy.data.collections.get(name)
    if col:
        bpy.data.collections.remove(col)
        return True
    return False

# Usage
remove_object("TestCube")
remove_material("TestPBR_Mat")
remove_collection("TestCollection")

result = {"cleaned": True}
```

### Clear scene (remove all mesh objects)

```python
import bpy

def clear_all_meshes():
    removed = []
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH':
            # Capture the name BEFORE removal — accessing obj.name after
            # bpy.data.objects.remove() is a use-after-free.
            name = obj.name
            bpy.data.objects.remove(obj, do_unlink=True)
            removed.append(name)
    return removed

removed = clear_all_meshes()
result = {"removed": removed}
```

---

## 15. Verification Patterns

### Structural verification via execute_blender_code

```python
import bpy

def verify_scene(expected_objects):
    missing = []
    for name in expected_objects:
        if name not in bpy.data.objects:
            missing.append(name)
    counts = {}
    for obj in bpy.data.objects:
        t = obj.type
        counts[t] = counts.get(t, 0) + 1
    return {
        "missing": missing,
        "counts": counts,
        "total_objects": len(bpy.data.objects),
    }

result = verify_scene(["Body", "Head", "ArmL"])
```

### Structural verification via get_objects_summary

Call `get_objects_summary({})` via the Blender MCP. This returns the full
collection hierarchy with object names, types, parents, and visibility. Use
it to confirm:
- All expected objects exist
- Parenting hierarchy is correct
- Objects are in the right collections

### Visual verification via render_viewport_to_path

Call `render_viewport_to_path({ output_path: "/tmp/preview.png" })` via the
Blender MCP. This renders the current viewport. Use it after creating an
asset to visually confirm the result matches the spec.

### Detailed object check via get_object_detail_summary

Call `get_object_detail_summary({ name: "Body" })` to check a specific
object's transforms, materials, modifiers, and parent. Use it to verify that
materials and modifiers were applied correctly.

---

## 16. API Lookup (when unsure)

### Search the Blender API docs

Call `search_api_docs({ query: "export_scene gltf", max_results: 5 })` to find
the correct API for an operation.

### Get specific API documentation

Call `get_python_api_docs({ identifier: "bpy.ops.export_scene.gltf" })` to
read the full API documentation for a specific function.

### Search the Blender manual

Call `search_manual_docs({ query: "UV unwrap smart project" })` for
conceptual explanations and workflow guidance.
