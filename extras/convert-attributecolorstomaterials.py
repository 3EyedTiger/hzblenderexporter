"""
Advanced Vertex Colour Fix - Horizon Worlds FBX Export
=======================================================

PROVIDED BY 3 EYED TIGER — FREE FOR THE HORIZON WORLDS COMMUNITY
-----------------------------------------------------------------
This script is provided free of charge by 3 Eyed Tiger to the Horizon Worlds
community. You are welcome to use, modify, and share it, but it must NOT be
sold or bundled into any paid product or service.

The latest version of this script can always be found at:
  https://tinyurl.com/horizonexport
  
Instructional video can be found here:
  https://www.youtube.com/watch?v=3Mj9b_6DxBY

MIT License
-----------
Copyright (c) 2026 3 Eyed Tiger

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice, this permission notice, and the non-commercial
restriction notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

=======================================================
This script:

1. Reads the dominant vertex colour of every mesh
2. Groups meshes that share the same colour (within tolerance)
3. Creates ONE shared material per unique colour
4. Assigns that material to all objects sharing that colour
5. Names materials descriptively (e.g. "VCol_Red_255_000_000")

This makes the scene Unity-ready:
- Each unique colour = one material asset
- Objects sharing a colour share the same material
- No duplicate materials
- Clean material names you can map to Unity shaders

HOW TO USE:
-----------
1. Open Blender
2. Import your FBX (File > Import > FBX)
3. Open the Scripting workspace
4. Paste this script and click Run Script (Alt+P)
5. Switch viewport to Material Preview (Z key) to see results

UNITY EXPORT:
-------------
File > Export > FBX, then in Unity assign a Vertex Color shader.
URP: Shader Graph > Vertex Color node > Base Color
"""

import bpy
from collections import defaultdict

# ─── SETTINGS ────────────────────────────────────────────────────────────────

# How close two colours need to be to be considered "the same"
# 0.05 = within ~5% on each channel. Raise for more aggressive merging.
COLOUR_TOLERANCE = 0.05

# Fix near-zero alpha on all vertex colour loops
FIX_ALPHA = True

# Material name prefix
MAT_PREFIX = "VCol"


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def get_dominant_colour(obj):
    """
    Returns the most common quantised (r, g, b) vertex colour for a mesh.
    Returns None if no vertex colours found.
    """
    mesh = obj.data
    if not mesh.vertex_colors:
        return None
    vcol_layer = mesh.vertex_colors.active
    if not vcol_layer:
        return None

    colour_counts = defaultdict(int)
    for loop_col in vcol_layer.data:
        r, g, b, a = loop_col.color
        rq = round(round(r / COLOUR_TOLERANCE) * COLOUR_TOLERANCE, 4)
        gq = round(round(g / COLOUR_TOLERANCE) * COLOUR_TOLERANCE, 4)
        bq = round(round(b / COLOUR_TOLERANCE) * COLOUR_TOLERANCE, 4)
        colour_counts[(rq, gq, bq)] += 1

    if not colour_counts:
        return None

    return max(colour_counts, key=colour_counts.get)


def fix_alpha_on_object(obj):
    """Set all vertex colour alphas to 1.0 so colours display correctly."""
    mesh = obj.data
    if not mesh.vertex_colors:
        return
    for vcol_layer in mesh.vertex_colors:
        for loop_col in vcol_layer.data:
            r, g, b, a = loop_col.color
            if a < 0.99:
                loop_col.color = (r, g, b, 1.0)


def colour_to_label(r, g, b):
    """Return a human-readable colour label for material naming."""
    ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)

    if ri > 180 and gi < 80  and bi < 80:  return "Red"
    if gi > 150 and ri < 80  and bi < 80:  return "Green"
    if bi > 180 and ri < 80  and gi < 80:  return "Blue"
    if ri > 180 and gi > 150 and bi < 80:  return "Yellow"
    if ri > 180 and bi > 150 and gi < 80:  return "Magenta"
    if gi > 150 and bi > 150 and ri < 80:  return "Cyan"
    if ri > 200 and gi > 200 and bi > 200: return "White"
    if ri < 50  and gi < 50  and bi < 50:  return "Black"
    if abs(ri-gi) < 30 and abs(gi-bi) < 30: return "Grey"
    if ri > gi  and ri > bi  and ri > 120: return "RedTone"
    if gi > ri  and gi > bi  and gi > 100: return "GreenTone"
    if bi > ri  and bi > gi  and bi > 120: return "BlueTone"
    if ri > 150 and gi > 100 and bi < 80:  return "Orange"
    if ri > 100 and bi > 150 and gi < 100: return "Purple"
    return "Mixed"


def colour_to_name(r, g, b):
    ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
    label = colour_to_label(r, g, b)
    return f"{MAT_PREFIX}_{label}_{ri:03d}_{gi:03d}_{bi:03d}"


def create_vertex_colour_material(name, r, g, b):
    """
    Create a flat-colour material with the RGB value baked directly
    into the Base Color input of a Principled BSDF.

    No Attribute node, no vertex colour lookup — just a plain colour.
    This exports cleanly to Unity as a Standard/URP material with
    the correct Albedo already set.
    """
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Output node
    output = nodes.new('ShaderNodeOutputMaterial')
    output.location = (400, 0)

    # Principled BSDF with flat colour baked in
    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 0)
    bsdf.inputs['Specular IOR Level'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = 1.0

    # Set the Base Color directly — no Attribute node needed
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)

    # Wire BSDF -> Output
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # Viewport display colour (Solid mode)
    mat.diffuse_color = (r, g, b, 1.0)

    return mat


# ─── MAIN ────────────────────────────────────────────────────────────────────

print("\n" + "="*65)
print("  Advanced Vertex Colour Fix + Material Grouping  (v2 - fixed)")
print("="*65)

# ── Step 1: Analyse all meshes ───────────────────────────────────────────────
print("\n[1/4] Analysing mesh colours...")

mesh_colour_map = {}  # obj -> (r, g, b)
skipped = []

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    if FIX_ALPHA:
        fix_alpha_on_object(obj)
    dominant = get_dominant_colour(obj)
    if dominant is None:
        skipped.append(obj.name)
        continue
    mesh_colour_map[obj] = dominant

print(f"  Meshes with vertex colours : {len(mesh_colour_map)}")
print(f"  Meshes skipped (no vcols)  : {len(skipped)}")

# ── Step 2: Group by colour ──────────────────────────────────────────────────
print("\n[2/4] Grouping by colour...")

colour_groups = defaultdict(list)
for obj, colour in mesh_colour_map.items():
    colour_groups[colour].append(obj)

print(f"  Unique colour groups : {len(colour_groups)}")

# ── Step 3: Create materials ─────────────────────────────────────────────────
print("\n[3/4] Creating materials...")

colour_material_map = {}
sorted_colours = sorted(colour_groups.keys(), key=lambda c: (-c[0], -c[1], -c[2]))

for colour in sorted_colours:
    r, g, b = colour
    mat_name = colour_to_name(r, g, b)

    if mat_name in bpy.data.materials:
        mat = bpy.data.materials[mat_name]
        print(f"  ~ Reusing : {mat_name}")
    else:
        mat = create_vertex_colour_material(mat_name, r, g, b)
        count = len(colour_groups[colour])
        print(f"  + Created : {mat_name:<50s}  [{count} objects]")

    colour_material_map[colour] = mat

# ── Step 4: Assign materials ─────────────────────────────────────────────────
print("\n[4/4] Assigning materials...")

assigned = 0
for obj, colour in mesh_colour_map.items():
    mat = colour_material_map[colour]
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    assigned += 1

# ── Report ────────────────────────────────────────────────────────────────────
print("\n" + "="*65)
print("  COMPLETE")
print("="*65)
print(f"  Objects processed    : {len(mesh_colour_map)}")
print(f"  Objects skipped      : {len(skipped)}")
print(f"  Unique materials     : {len(colour_groups)}")
print(f"  Assignments made     : {assigned}")
print()
print("  Materials created:")
for colour in sorted_colours:
    r, g, b   = colour
    mat       = colour_material_map[colour]
    obj_count = len(colour_groups[colour])
    print(f"    {mat.name:<50s}  -> {obj_count:>4} object(s)")

print()
print("  ─── TO VIEW CORRECTLY ──────────────────────────────")
print("  Press Z -> choose 'Material Preview'")
print("  (Solid mode won't show vertex colours properly)")
print()
print("  ─── IF COLOURS STILL LOOK WRONG ───────────────────")
print("  The vertex colour layer might not be named 'Col'.")
print("  Check: Properties > Object Data > Color Attributes")
print("  Update attr.attribute_name in each material if needed.")
print()
print("  ─── UNITY EXPORT ───────────────────────────────────")
print("  File > Export > FBX")
print("  In Unity: assign a Vertex Color shader per material")
print("  URP Shader Graph: Vertex Color node -> Base Color")
print("="*65 + "\n")