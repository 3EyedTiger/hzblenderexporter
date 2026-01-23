bl_info = {
    "name": "Horizon Worlds Texture Packer",
    "author": "3 Eyed Tiger",
    "version": (1, 11, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Horizon Tools",
    "description": "Bake and Pack Materials into Horizon Compatible Imports",
    "category": "Material",
}

import bpy
import os
import re
from pathlib import Path


def validate_material_name(name):
    """
    Validate material name against Horizon Worlds rules.
    Returns (is_valid, reason) tuple.

    Rules:
    - Only uppercase, lowercase letters and numbers
    - Must not start with a number
    - No spaces or underscores (except for specific suffixes)
    - Allowed suffixes: _Transparent, _Masked, _MaskedVXM, _VXC, _VXM, _Blend, _Unlit, _UIO, _Metal
    """
    ALLOWED_SUFFIXES = ['_Transparent', '_Masked', '_MaskedVXM', '_VXC', '_VXM', '_Blend', '_Unlit', '_UIO', '_Metal']

    # Check if name has an allowed suffix
    base_name = name
    suffix = ''
    for allowed_suffix in ALLOWED_SUFFIXES:
        if name.endswith(allowed_suffix):
            base_name = name[:-len(allowed_suffix)]
            suffix = allowed_suffix
            break

    # Base name must not be empty
    if not base_name:
        return False, "Material name cannot be only a suffix"

    # Base name must start with a letter
    if base_name[0].isdigit():
        return False, f"Name cannot start with a number: '{base_name[0]}'"

    # Base name must only contain alphanumeric characters (no spaces, underscores, special chars)
    if not base_name.isalnum():
        invalid_chars = [c for c in base_name if not c.isalnum()]
        return False, f"Name contains invalid characters: {', '.join(repr(c) for c in set(invalid_chars))}"

    return True, ""


def generate_compliant_name(name, existing_names):
    """
    Generate a compliant material name from an invalid one.
    Preserves allowed suffixes and adds incremental numbers if needed.
    """
    ALLOWED_SUFFIXES = ['_Transparent', '_Masked', '_MaskedVXM', '_VXC', '_VXM', '_Blend', '_Unlit', '_UIO', '_Metal']

    # Extract suffix if present
    base_name = name
    suffix = ''
    for allowed_suffix in ALLOWED_SUFFIXES:
        if name.endswith(allowed_suffix):
            base_name = name[:-len(allowed_suffix)]
            suffix = allowed_suffix
            break

    # Clean the base name: remove invalid characters
    # Keep only alphanumeric characters
    cleaned = ''.join(c for c in base_name if c.isalnum())

    # If name starts with a number, prepend 'Mat'
    if cleaned and cleaned[0].isdigit():
        cleaned = 'Mat' + cleaned

    # If completely empty after cleaning, use a default
    if not cleaned:
        cleaned = 'Material'

    # Try the cleaned name first
    candidate = cleaned + suffix
    if candidate not in existing_names:
        return candidate

    # If taken, add incremental number before suffix
    counter = 1
    while True:
        if suffix:
            candidate = f"{cleaned}{counter}{suffix}"
        else:
            candidate = f"{cleaned}{counter}"

        if candidate not in existing_names:
            return candidate
        counter += 1


class HZ_OT_ValidateMaterialNames(bpy.types.Operator):
    """Validate and optionally rename materials to be Horizon Worlds compliant"""
    bl_idname = "hz.validate_material_names"
    bl_label = "Validate Material Names"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout

        layout.label(text="Invalid Material Names Found:", icon='ERROR')
        layout.separator()

        box = layout.box()
        for item in context.scene.hz_invalid_materials:
            row = box.row()
            col = row.column()
            col.label(text=f"• {item.material_name}")
            col.label(text=f"  Reason: {item.reason}", icon='BLANK1')
            box.separator()

        layout.separator()
        layout.label(text="Click OK to auto-rename these materials to be compliant.", icon='INFO')

    def invoke(self, context, event):
        # Get all materials from the blend file
        materials = set()
        for mat in bpy.data.materials:
            if mat:
                materials.add(mat)

        if not materials:
            self.report({'WARNING'}, "No materials found in scene")
            return {'CANCELLED'}

        # Check for invalid names
        invalid_materials = []
        for mat in materials:
            is_valid, reason = validate_material_name(mat.name)
            if not is_valid:
                invalid_materials.append((mat, reason))

        if not invalid_materials:
            self.report({'INFO'}, "All material names are valid!")
            return {'FINISHED'}

        # Store invalid materials for the dialog
        context.scene.hz_invalid_materials.clear()
        for mat, reason in invalid_materials:
            item = context.scene.hz_invalid_materials.add()
            item.material_name = mat.name
            item.reason = reason
            item.material_ptr = mat

        # Show the rename dialog
        return context.window_manager.invoke_props_dialog(self, width=500)

    def execute(self, context):
        # This is called when user clicks OK in the dialog
        # Get existing material names to avoid duplicates
        existing_names = {mat.name for mat in bpy.data.materials}

        renamed_count = 0
        for item in context.scene.hz_invalid_materials:
            mat = item.material_ptr
            if mat:
                old_name = mat.name
                # Generate new compliant name
                new_name = generate_compliant_name(old_name, existing_names)

                # Rename the material
                mat.name = new_name
                existing_names.add(new_name)
                existing_names.discard(old_name)

                print(f"Renamed: '{old_name}' → '{new_name}'")
                renamed_count += 1

        self.report({'INFO'}, f"Renamed {renamed_count} materials to be compliant")
        context.scene.hz_invalid_materials.clear()
        return {'FINISHED'}


class HZ_OT_PackTextures(bpy.types.Operator):
    """Bake & Pack Textures and Meshes into importable assets for Meta Horizon Worlds"""
    bl_idname = "hz.pack_textures"
    bl_label = "Pack Selected"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.hz_texture_packer
        output_dir = bpy.path.abspath(props.output_path)

        if not output_dir:
            self.report({'ERROR'}, "Please set an output directory")
            return {'CANCELLED'}

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Get all materials from selected objects
        materials = set()
        for obj in context.selected_objects:
            if obj.type == 'MESH' and obj.data.materials:
                for mat in obj.data.materials:
                    if mat and mat.use_nodes:
                        materials.add(mat)

        if not materials:
            self.report({'WARNING'}, "No materials found on selected meshes")
            return {'CANCELLED'}

        # Check for invalid material names
        invalid_materials = []
        for mat in materials:
            is_valid, reason = validate_material_name(mat.name)
            if not is_valid:
                invalid_materials.append((mat.name, reason))

        if invalid_materials:
            # Show warning but allow them to proceed
            warning_msg = f"Warning: {len(invalid_materials)} material(s) have invalid names:\n"
            for mat_name, reason in invalid_materials[:3]:  # Show first 3
                warning_msg += f"  • {mat_name}: {reason}\n"
            if len(invalid_materials) > 3:
                warning_msg += f"  ... and {len(invalid_materials) - 3} more\n"
            warning_msg += "Run 'Validate Material Names' to fix these issues."
            self.report({'WARNING'}, warning_msg)
            print("\n" + "="*60)
            print("MATERIAL NAME VALIDATION WARNING")
            print("="*60)
            for mat_name, reason in invalid_materials:
                print(f"  ✗ {mat_name}")
                print(f"    Reason: {reason}")
            print("="*60)
            print("TIP: Use 'Validate Material Names' button to auto-fix these issues")
            print("="*60 + "\n")

        # Initialize progress bar
        wm = context.window_manager
        wm.progress_begin(0, len(materials))

        print("\n" + "="*60)
        print(f"STARTING TEXTURE PACKING FOR {len(materials)} MATERIAL(S)")
        print("="*60)

        processed_count = 0
        for idx, mat in enumerate(materials):
            # Update progress bar with current material
            wm.progress_update(idx)
            print(f"\n[{idx + 1}/{len(materials)}] Processing: {mat.name}")

            success = self.process_material(mat, output_dir, context)
            if success:
                processed_count += 1

        # End progress bar
        wm.progress_end()

        # Print summary
        print("\n" + "="*60)
        print(f"TEXTURE PACKING COMPLETE")
        print(f"  Materials processed: {processed_count}/{len(materials)}")
        if processed_count < len(materials):
            print(f"  Materials skipped: {len(materials) - processed_count}")
        print("="*60)

        # Export selected meshes to FBX
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        if selected_meshes:
            # Create a name for the FBX based on selected objects
            if len(selected_meshes) == 1:
                fbx_name = self.sanitize_filename(selected_meshes[0].name) + ".fbx"
            else:
                # Use the first object's name or a generic name
                fbx_name = "exported_meshes.fbx"

            fbx_path = os.path.join(output_dir, fbx_name)

            # Export FBX with selected objects only
            try:
                print(f"\nExporting {len(selected_meshes)} mesh(es) to FBX...")
                bpy.ops.export_scene.fbx(
                    filepath=fbx_path,
                    use_selection=True,
                    object_types={'MESH'},
                    use_mesh_modifiers=True,
                    add_leaf_bones=False,
                    bake_anim=False
                )
                print(f"✓ Exported FBX to: {fbx_path}")
                self.report({'INFO'}, f"Processed {processed_count} materials and exported {len(selected_meshes)} mesh(es)")
            except Exception as e:
                print(f"✗ Error exporting FBX: {e}")
                self.report({'WARNING'}, f"Processed {processed_count} materials but FBX export failed: {e}")
        else:
            self.report({'INFO'}, f"Processed {processed_count} materials")

        return {'FINISHED'}
    
    def process_material(self, mat, output_dir, context):
        """Process a single material and pack its textures"""
        props = context.scene.hz_texture_packer

        # Check for special material suffixes (special export behaviors)
        is_metal_material = mat.name.endswith('_Metal')
        is_blend_material = mat.name.endswith('_Blend')
        is_transparent_material = mat.name.endswith('_Transparent')
        is_maskedvxm_material = mat.name.endswith('_MaskedVXM')
        is_masked_material = mat.name.endswith('_Masked') and not is_maskedvxm_material  # Exclude _MaskedVXM
        is_vxc_material = mat.name.endswith('_VXC')
        is_vxm_material = mat.name.endswith('_VXM')
        is_uio_material = mat.name.endswith('_UIO')

        # Find Principled BSDF node
        principled = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break

        # Initialize textures dictionary
        textures = {
            'base_color': None,
            'roughness': None,
            'metallic': None,
            'emission': None,
            'specular': None,
            'ao': None
        }

        if not principled:
            # Material uses custom shader - try to bake it
            print(f"  ⚠ No Principled BSDF found - will bake custom shader to texture")

            # Bake the material's appearance
            baked_texture = self.bake_material_combined(context, mat, props.default_resolution)

            if not baked_texture:
                print(f"  ✗ Skipped: Could not bake custom shader")
                self.report({'WARNING'}, f"Material '{mat.name}' has no Principled BSDF and baking failed")
                return False

            # Use the baked texture as base color for export
            textures['base_color'] = baked_texture
            print(f"  ✓ Custom shader baked successfully")

            # For custom shaders, we'll export a simple BR texture with white roughness
            # since we don't have access to proper PBR channels
            resolution = (baked_texture.size[0], baked_texture.size[1])
            safe_name = self.sanitize_filename(mat.name)

            # Create BR texture with baked base color and white roughness
            br_image = self.create_br_texture(textures, resolution)
            br_path = os.path.join(output_dir, f"{safe_name}_BR.png")

            br_image.filepath_raw = br_path
            br_image.file_format = 'PNG'
            br_image.save()

            bpy.data.images.remove(br_image)
            # Clean up baked image
            bpy.data.images.remove(baked_texture)

            print(f"  ✓ Saved: {safe_name}_BR.png (baked from custom shader)")
            return True

        # Extract texture paths from Principled BSDF
        textures['base_color'] = self.get_texture_from_socket(principled.inputs['Base Color'])
        textures['roughness'] = self.get_texture_from_socket(principled.inputs['Roughness'])
        textures['metallic'] = self.get_texture_from_socket(principled.inputs['Metallic'])
        textures['emission'] = self.get_texture_from_socket(principled.inputs['Emission Color'])
        textures['specular'] = self.get_texture_from_socket(principled.inputs.get('Specular', principled.inputs.get('Specular IOR Level')))
        # textures['ao'] remains None - AO is typically not directly connected to Principled BSDF

        # Debug output
        print(f"  Material Type: ", end="")
        if is_vxc_material:
            print(f"_VXC (vertex color only - no texture export needed)")
            return True  # Successfully processed, but no export needed
        elif is_metal_material:
            print(f"_Metal → will export BR (RGB=BaseColor, A=Metallic)")
        elif is_blend_material:
            print(f"_Blend → will export BA (RGB=BaseColor, A=Alpha)")
        elif is_transparent_material:
            print(f"_Transparent → will export BR + MESA")
        elif is_vxm_material:
            print(f"_VXM (vertex multiplied) → will export BR + MEO*")
        elif is_maskedvxm_material:
            print(f"_MaskedVXM → will export BA (RGB=BaseColor, A=Alpha)")
        elif is_masked_material:
            print(f"_Masked → will export BA (RGB=BaseColor, A=Alpha)")
        elif is_uio_material:
            print(f"_UIO (UI optimized) → will export BA")
        else:
            print(f"Standard → will export BR + MEO*")

        print(f"  Textures found:")
        for key, tex in textures.items():
            if tex:
                print(f"    ✓ {key}: {tex.name} ({tex.size[0]}x{tex.size[1]})")
            else:
                print(f"    ✗ {key}: None")

        # Try to find AO texture from other nodes (common setup)
        # _Transparent, _Masked, _MaskedVXM, and _UIO materials don't need AO (not in their output formats)
        # _VXM materials CAN use AO if present (outputs MEO alongside BR)
        if not is_metal_material and not is_blend_material and not is_transparent_material and not is_masked_material and not is_maskedvxm_material and not is_uio_material:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    img_name = node.image.name.lower()
                    if 'ao' in img_name or 'occlusion' in img_name or 'ambient' in img_name:
                        textures['ao'] = node.image
                        print(f"    ✓ Found AO by name: {node.image.name}")
                        break

            # Auto-bake if enabled
            if props.auto_bake_ao and not textures['ao']:
                print(f"  ⏳ Auto-baking AO (this may take a moment)...")
                textures['ao'] = self.bake_ao(context, mat, props.bake_resolution)
                if textures['ao']:
                    print(f"  ✓ AO bake complete")

            if props.auto_bake_emission and not textures['emission']:
                print(f"  ⏳ Auto-baking Emission (this may take a moment)...")
                textures['emission'] = self.bake_emission(context, mat, props.bake_resolution)
                if textures['emission']:
                    print(f"  ✓ Emission bake complete")

        # Determine resolution
        resolution = self.get_resolution(textures, props.default_resolution)

        # Generate output filename (remove special suffixes from filename)
        if is_metal_material:
            # Remove _Metal suffix from output filename
            base_name = mat.name[:-6]  # Remove "_Metal"
            safe_name = self.sanitize_filename(base_name)
        elif is_blend_material:
            # Remove _Blend suffix from output filename
            base_name = mat.name[:-6]  # Remove "_Blend"
            safe_name = self.sanitize_filename(base_name)
        elif is_transparent_material:
            # Remove _Transparent suffix from output filename
            base_name = mat.name[:-12]  # Remove "_Transparent"
            safe_name = self.sanitize_filename(base_name)
        elif is_vxm_material:
            # Remove _VXM suffix from output filename
            base_name = mat.name[:-4]  # Remove "_VXM"
            safe_name = self.sanitize_filename(base_name)
        elif is_maskedvxm_material:
            # Remove _MaskedVXM suffix from output filename
            base_name = mat.name[:-10]  # Remove "_MaskedVXM"
            safe_name = self.sanitize_filename(base_name)
        elif is_masked_material:
            # Remove _Masked suffix from output filename
            base_name = mat.name[:-7]  # Remove "_Masked"
            safe_name = self.sanitize_filename(base_name)
        elif is_uio_material:
            # Remove _UIO suffix from output filename
            base_name = mat.name[:-4]  # Remove "_UIO"
            safe_name = self.sanitize_filename(base_name)
        else:
            safe_name = self.sanitize_filename(mat.name)

        # Handle _Metal material: BR with RGB=BaseColor, A=Metallic
        if is_metal_material:
            br_image = self.create_metal_br_texture(textures, resolution)
            br_path = os.path.join(output_dir, f"{safe_name}_BR.png")

            br_image.filepath_raw = br_path
            br_image.file_format = 'PNG'
            br_image.save()

            bpy.data.images.remove(br_image)
            print(f"  ✓ Saved: {safe_name}_BR.png (Metal material)")
        # Handle _Blend material: BA with RGB=BaseColor, A=Alpha
        elif is_blend_material:
            ba_image = self.create_blend_ba_texture(textures, resolution)
            ba_path = os.path.join(output_dir, f"{safe_name}_BA.png")

            ba_image.filepath_raw = ba_path
            ba_image.file_format = 'PNG'
            ba_image.save()

            bpy.data.images.remove(ba_image)
            print(f"  ✓ Saved: {safe_name}_BA.png (Blend material)")
        # Handle _Transparent material: BR (RGB=BaseColor, A=Roughness) and MESA (R=Metallic, G=Specular, B=Emission, A=Alpha)
        elif is_transparent_material:
            # Create BR texture (standard base color + roughness)
            br_image = self.create_br_texture(textures, resolution)
            br_path = os.path.join(output_dir, f"{safe_name}_BR.png")

            br_image.filepath_raw = br_path
            br_image.file_format = 'PNG'
            br_image.save()

            bpy.data.images.remove(br_image)

            # Create MESA texture (R=Metallic, G=Specular, B=Emission, A=Alpha)
            mesa_image = self.create_transparent_mesa_texture(textures, resolution)
            mesa_path = os.path.join(output_dir, f"{safe_name}_MESA.png")

            mesa_image.filepath_raw = mesa_path
            mesa_image.file_format = 'PNG'
            mesa_image.save()

            bpy.data.images.remove(mesa_image)
            print(f"  ✓ Saved: {safe_name}_BR.png and {safe_name}_MESA.png (Transparent material)")
        # Handle _VXM material: BR with RGB=BaseColor, A=Roughness (vertex color multiplied in Horizon)
        # Optionally also export MEO if metallic, emission, or AO data is present
        elif is_vxm_material:
            # Always create BR texture
            br_image = self.create_br_texture(textures, resolution)
            br_path = os.path.join(output_dir, f"{safe_name}_BR.png")

            br_image.filepath_raw = br_path
            br_image.file_format = 'PNG'
            br_image.save()

            bpy.data.images.remove(br_image)

            # Check if we have metallic, emission, or AO data to create MEO
            has_meo_data = textures['metallic'] or textures['emission'] or textures['ao']

            if has_meo_data:
                # Create MEO texture (R=Metallic, G=Emission, B=AO)
                meo_image = self.create_meo_texture(textures, resolution)
                meo_path = os.path.join(output_dir, f"{safe_name}_MEO.png")

                meo_image.filepath_raw = meo_path
                meo_image.file_format = 'PNG'
                meo_image.save()

                bpy.data.images.remove(meo_image)

                # Clean up baked images (AO and Emission)
                for key in ['ao', 'emission']:
                    if textures[key] and textures[key].name.endswith('_baked'):
                        print(f"  Cleaning up baked image: {textures[key].name}")
                        bpy.data.images.remove(textures[key])

                print(f"  ✓ Saved: {safe_name}_BR.png and {safe_name}_MEO.png (VXM material)")
            else:
                print(f"  ✓ Saved: {safe_name}_BR.png (VXM material)")
        # Handle _MaskedVXM material: BA with RGB=BaseColor, A=Alpha (same as _Blend, vertex color multiplied in Horizon)
        elif is_maskedvxm_material:
            ba_image = self.create_blend_ba_texture(textures, resolution)
            ba_path = os.path.join(output_dir, f"{safe_name}_BA.png")

            ba_image.filepath_raw = ba_path
            ba_image.file_format = 'PNG'
            ba_image.save()

            bpy.data.images.remove(ba_image)
            print(f"  ✓ Saved: {safe_name}_BA.png (MaskedVXM material)")
        # Handle _Masked material: BA with RGB=BaseColor, A=Alpha (same as _Blend)
        elif is_masked_material:
            ba_image = self.create_blend_ba_texture(textures, resolution)
            ba_path = os.path.join(output_dir, f"{safe_name}_BA.png")

            ba_image.filepath_raw = ba_path
            ba_image.file_format = 'PNG'
            ba_image.save()

            bpy.data.images.remove(ba_image)
            print(f"  ✓ Saved: {safe_name}_BA.png (Masked material)")
        # Handle _UIO material: BA with RGB=BaseColor, A=Alpha (high-quality UI texture)
        elif is_uio_material:
            ba_image = self.create_blend_ba_texture(textures, resolution)
            ba_path = os.path.join(output_dir, f"{safe_name}_BA.png")

            ba_image.filepath_raw = ba_path
            ba_image.file_format = 'PNG'
            ba_image.save()

            bpy.data.images.remove(ba_image)
            print(f"  ✓ Saved: {safe_name}_BA.png (UIO material)")
        else:
            # Standard material: Always create BR, optionally create MEO if metallic/emission/AO present
            br_image = self.create_br_texture(textures, resolution)
            br_path = os.path.join(output_dir, f"{safe_name}_BR.png")

            # Save BR texture
            br_image.filepath_raw = br_path
            br_image.file_format = 'PNG'
            br_image.save()

            bpy.data.images.remove(br_image)

            # Check if we have metallic, emission, or AO data to create MEO
            has_meo_data = textures['metallic'] or textures['emission'] or textures['ao']

            if has_meo_data:
                # Create MEO texture (R=Metallic, G=Emission, B=AO)
                meo_image = self.create_meo_texture(textures, resolution)
                meo_path = os.path.join(output_dir, f"{safe_name}_MEO.png")

                meo_image.filepath_raw = meo_path
                meo_image.file_format = 'PNG'
                meo_image.save()

                bpy.data.images.remove(meo_image)

                # Clean up baked images (AO and Emission)
                for key in ['ao', 'emission']:
                    if textures[key] and textures[key].name.endswith('_baked'):
                        print(f"  Cleaning up baked image: {textures[key].name}")
                        bpy.data.images.remove(textures[key])

                print(f"  ✓ Saved: {safe_name}_BR.png and {safe_name}_MEO.png")
            else:
                print(f"  ✓ Saved: {safe_name}_BR.png")

        return True
    
    def get_texture_from_socket(self, socket):
        """Get the image texture connected to a socket, tracing through intermediate nodes"""
        if not socket.is_linked:
            return None

        # Trace back through the node chain to find an Image Texture
        nodes_to_check = [socket.links[0].from_node]
        visited = set()

        while nodes_to_check:
            node = nodes_to_check.pop(0)

            if node in visited:
                continue
            visited.add(node)

            # Found an image texture node
            if node.type == 'TEX_IMAGE' and node.image:
                return node.image

            # For other node types, check their inputs
            if hasattr(node, 'inputs'):
                for input_socket in node.inputs:
                    if input_socket.is_linked:
                        nodes_to_check.append(input_socket.links[0].from_node)

        return None
    
    def get_resolution(self, textures, default_res):
        """Determine resolution from existing textures or use default"""
        for tex in textures.values():
            if tex:
                return (tex.size[0], tex.size[1])
        return (default_res, default_res)
    
    def get_pixel_data(self, image, resolution):
        """Get pixel data from Blender image and resize if needed"""
        if not image:
            return None

        # If image needs resizing, create a temporary resized copy
        width, height = image.size[0], image.size[1]
        if (width, height) != resolution:
            # Create a temporary image at target resolution
            temp_img = bpy.data.images.new(
                name="temp_resize",
                width=resolution[0],
                height=resolution[1],
                alpha=True
            )

            # Scale the source image to temp image using Blender's scale
            temp_img.scale(resolution[0], resolution[1])

            # Copy pixels from source with scaling
            src_pixels = list(image.pixels)
            temp_pixels = [0.0] * (resolution[0] * resolution[1] * 4)

            # Simple bilinear interpolation for resizing
            for y in range(resolution[1]):
                for x in range(resolution[0]):
                    # Map to source coordinates
                    src_x = (x / resolution[0]) * width
                    src_y = (y / resolution[1]) * height

                    # Get integer coordinates
                    x0 = int(src_x)
                    y0 = int(src_y)
                    x1 = min(x0 + 1, width - 1)
                    y1 = min(y0 + 1, height - 1)

                    # Get fractional parts
                    fx = src_x - x0
                    fy = src_y - y0

                    # Sample 4 pixels for bilinear interpolation
                    for c in range(min(image.channels, 4)):
                        p00 = src_pixels[(y0 * width + x0) * image.channels + c] if c < image.channels else 1.0
                        p10 = src_pixels[(y0 * width + x1) * image.channels + c] if c < image.channels else 1.0
                        p01 = src_pixels[(y1 * width + x0) * image.channels + c] if c < image.channels else 1.0
                        p11 = src_pixels[(y1 * width + x1) * image.channels + c] if c < image.channels else 1.0

                        # Bilinear interpolation
                        p0 = p00 * (1 - fx) + p10 * fx
                        p1 = p01 * (1 - fx) + p11 * fx
                        value = p0 * (1 - fy) + p1 * fy

                        temp_pixels[(y * resolution[0] + x) * 4 + c] = value

                    # Fill alpha if source doesn't have it
                    if image.channels < 4:
                        temp_pixels[(y * resolution[0] + x) * 4 + 3] = 1.0

            return temp_pixels, 4
        else:
            return list(image.pixels), image.channels
    
    def create_br_texture(self, textures, resolution):
        """Create BR texture: RGB = Base Color, A = Roughness"""
        width, height = resolution

        # Create a new Blender image for the BR texture
        br_image = bpy.data.images.new(
            name="BR_temp",
            width=width,
            height=height,
            alpha=True
        )

        # Initialize pixel array (RGBA format)
        pixels = [1.0] * (width * height * 4)  # Default to white

        # Load base color
        base_color_data = None
        if textures['base_color']:
            base_color_data, channels = self.get_pixel_data(textures['base_color'], resolution)

        # Load roughness
        roughness_data = None
        if textures['roughness']:
            roughness_data, channels = self.get_pixel_data(textures['roughness'], resolution)

        # Fill pixel data
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4

                # Set RGB from base color
                if base_color_data:
                    pixels[idx] = base_color_data[idx]      # R
                    pixels[idx + 1] = base_color_data[idx + 1]  # G
                    pixels[idx + 2] = base_color_data[idx + 2]  # B
                else:
                    pixels[idx] = 1.0
                    pixels[idx + 1] = 1.0
                    pixels[idx + 2] = 1.0

                # Set A from roughness (use first channel)
                if roughness_data:
                    pixels[idx + 3] = roughness_data[idx]  # Use R channel for roughness
                else:
                    pixels[idx + 3] = 1.0

        # Apply pixels to image using foreach_set for better performance and reliability
        br_image.pixels.foreach_set(pixels)

        # Update the image to ensure changes are applied
        br_image.update()

        # BR texture should use sRGB for base color (default is fine)
        # Alpha channel (roughness) will be saved correctly as linear data

        return br_image

    def create_metal_br_texture(self, textures, resolution):
        """Create Metal BR texture: RGB = Base Color, A = Metallic"""
        width, height = resolution

        # Create a new Blender image for the Metal BR texture
        br_image = bpy.data.images.new(
            name="Metal_BR_temp",
            width=width,
            height=height,
            alpha=True
        )

        # Initialize pixel array (RGBA format)
        pixels = [1.0] * (width * height * 4)  # Default to white

        # Load base color
        base_color_data = None
        if textures['base_color']:
            base_color_data, channels = self.get_pixel_data(textures['base_color'], resolution)

        # Load metallic
        metallic_data = None
        if textures['metallic']:
            metallic_data, channels = self.get_pixel_data(textures['metallic'], resolution)

        # Fill pixel data
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4

                # Set RGB from base color
                if base_color_data:
                    pixels[idx] = base_color_data[idx]          # R
                    pixels[idx + 1] = base_color_data[idx + 1]  # G
                    pixels[idx + 2] = base_color_data[idx + 2]  # B
                else:
                    pixels[idx] = 1.0
                    pixels[idx + 1] = 1.0
                    pixels[idx + 2] = 1.0

                # Set A from metallic (use first channel)
                if metallic_data:
                    pixels[idx + 3] = metallic_data[idx]  # Use R channel for metallic
                else:
                    pixels[idx + 3] = 1.0  # Full metallic by default

        # Apply pixels to image using foreach_set
        br_image.pixels.foreach_set(pixels)

        # Update the image to ensure changes are applied
        br_image.update()

        return br_image

    def create_blend_ba_texture(self, textures, resolution):
        """Create Blend BA texture: RGB = Base Color, A = Alpha"""
        width, height = resolution

        # Create a new Blender image for the Blend BA texture
        ba_image = bpy.data.images.new(
            name="Blend_BA_temp",
            width=width,
            height=height,
            alpha=True
        )

        # Initialize pixel array (RGBA format)
        pixels = [1.0] * (width * height * 4)  # Default to white with full alpha

        # Load base color (which should contain the alpha channel)
        base_color_data = None
        base_color_channels = 0
        if textures['base_color']:
            base_color_data, base_color_channels = self.get_pixel_data(textures['base_color'], resolution)

        # Fill pixel data
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4

                # Set RGB from base color
                if base_color_data:
                    pixels[idx] = base_color_data[idx]          # R
                    pixels[idx + 1] = base_color_data[idx + 1]  # G
                    pixels[idx + 2] = base_color_data[idx + 2]  # B

                    # Set A from base color's alpha channel if it exists
                    if base_color_channels >= 4:
                        pixels[idx + 3] = base_color_data[idx + 3]  # Alpha from texture
                    else:
                        pixels[idx + 3] = 1.0  # Full opacity if no alpha channel
                else:
                    pixels[idx] = 1.0
                    pixels[idx + 1] = 1.0
                    pixels[idx + 2] = 1.0
                    pixels[idx + 3] = 1.0

        # Apply pixels to image using foreach_set
        ba_image.pixels.foreach_set(pixels)

        # Update the image to ensure changes are applied
        ba_image.update()

        return ba_image

    def create_transparent_mesa_texture(self, textures, resolution):
        """Create Transparent MESA texture: R = Metallic, G = Specular, B = Emission, A = Alpha"""
        width, height = resolution

        # Create a new Blender image for the MESA texture
        mesa_image = bpy.data.images.new(
            name="Transparent_MESA_temp",
            width=width,
            height=height,
            alpha=True
        )

        # Initialize pixel array (RGBA format)
        pixels = [0.0] * (width * height * 4)  # Default to black

        # Load metallic
        metallic_data = None
        if textures['metallic']:
            metallic_data, _ = self.get_pixel_data(textures['metallic'], resolution)

        # Load specular
        specular_data = None
        if textures['specular']:
            specular_data, _ = self.get_pixel_data(textures['specular'], resolution)

        # Load emission
        emission_data = None
        if textures['emission']:
            emission_data, _ = self.get_pixel_data(textures['emission'], resolution)

        # Load base color for alpha channel
        base_color_data = None
        base_color_channels = 0
        if textures['base_color']:
            base_color_data, base_color_channels = self.get_pixel_data(textures['base_color'], resolution)

        # Debug: Check what data we have
        print(f"  Debug - metallic_data: {metallic_data is not None}, specular_data: {specular_data is not None}, emission_data: {emission_data is not None}, base_color_channels: {base_color_channels}")

        # Fill pixel data
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4

                # R channel = Metallic (use first channel)
                if metallic_data:
                    pixels[idx] = metallic_data[idx]
                else:
                    pixels[idx] = 0.0

                # G channel = Specular (use first channel)
                if specular_data:
                    pixels[idx + 1] = specular_data[idx]
                else:
                    pixels[idx + 1] = 0.5  # Default specular value

                # B channel = Emission (convert RGB to grayscale if needed)
                if emission_data:
                    r = emission_data[idx]
                    g = emission_data[idx + 1]
                    b = emission_data[idx + 2]
                    pixels[idx + 2] = (r + g + b) / 3.0
                else:
                    pixels[idx + 2] = 0.0

                # A channel = Alpha from base color texture
                if base_color_data and base_color_channels >= 4:
                    pixels[idx + 3] = base_color_data[idx + 3]
                else:
                    pixels[idx + 3] = 1.0  # Full opacity by default

        # Set colorspace to Non-Color for data textures
        mesa_image.colorspace_settings.name = 'Non-Color'

        # Apply pixels to image using foreach_set
        try:
            mesa_image.pixels.foreach_set(pixels)
        except Exception as e:
            print(f"  Error in foreach_set: {e}")
            mesa_image.pixels[:] = pixels

        # Update the image to ensure changes are applied
        mesa_image.update()

        return mesa_image

    def create_meo_texture(self, textures, resolution):
        """Create MEO texture: R = Metallic, G = Emission, B = AO"""
        width, height = resolution

        # Create a new Blender image for the MEO texture
        meo_image = bpy.data.images.new(
            name="MEO_temp",
            width=width,
            height=height,
            alpha=True
        )

        # Initialize pixel array (RGBA format, but we'll only use RGB)
        pixels = [0.0] * (width * height * 4)  # Default to black

        # Load metallic
        metallic_data = None
        if textures['metallic']:
            metallic_data, _ = self.get_pixel_data(textures['metallic'], resolution)

        # Load emission
        emission_data = None
        if textures['emission']:
            emission_data, _ = self.get_pixel_data(textures['emission'], resolution)

        # Load AO
        ao_data = None
        if textures['ao']:
            ao_data, _ = self.get_pixel_data(textures['ao'], resolution)

        # Debug: Check what data we have
        print(f"  Debug - metallic_data: {metallic_data is not None}, emission_data: {emission_data is not None}, ao_data: {ao_data is not None}")

        # Fill pixel data
        for y in range(height):
            for x in range(width):
                idx = (y * width + x) * 4

                # R channel = Metallic (use first channel)
                if metallic_data:
                    pixels[idx] = metallic_data[idx]  # Use R channel
                else:
                    pixels[idx] = 0.0

                # G channel = Emission (convert RGB to grayscale if needed)
                if emission_data:
                    # Average RGB channels for grayscale emission
                    r = emission_data[idx]
                    g = emission_data[idx + 1]
                    b = emission_data[idx + 2]
                    pixels[idx + 1] = (r + g + b) / 3.0
                else:
                    pixels[idx + 1] = 0.0

                # B channel = AO (use first channel)
                if ao_data:
                    pixels[idx + 2] = ao_data[idx]  # Use R channel
                else:
                    pixels[idx + 2] = 1.0  # White = full ambient

                # Alpha channel
                pixels[idx + 3] = 1.0

        # Debug: Check what we're about to write
        sample_idx = (height // 2 * width + width // 2) * 4  # Middle pixel
        print(f"  MEO Debug BEFORE write - Center pixel will be: R={pixels[sample_idx]:.3f}, "
              f"G={pixels[sample_idx+1]:.3f}, B={pixels[sample_idx+2]:.3f}")

        # Set colorspace BEFORE setting pixels (important for Blender 5.0)
        meo_image.colorspace_settings.name = 'Non-Color'

        # Apply pixels to image using foreach_set for better performance and reliability
        try:
            meo_image.pixels.foreach_set(pixels)
        except Exception as e:
            print(f"  Error in foreach_set: {e}")
            # Fallback to direct assignment
            meo_image.pixels[:] = pixels

        # Update the image to ensure changes are applied
        meo_image.update()

        # Debug: Check pixel values after write
        check_pixels = list(meo_image.pixels)
        if check_pixels:
            print(f"  MEO Debug AFTER write - Center pixel: R={check_pixels[sample_idx]:.3f}, "
                  f"G={check_pixels[sample_idx+1]:.3f}, B={check_pixels[sample_idx+2]:.3f}")

        return meo_image
    
    def bake_ao(self, context, material, resolution):
        """Bake ambient occlusion for a material"""
        # Find objects using this material
        objects = [obj for obj in context.selected_objects
                   if obj.type == 'MESH' and material in [slot.material for slot in obj.material_slots]]

        if not objects:
            print(f"  Warning: No objects found with material {material.name}")
            return None

        # Use the first object with this material
        target_obj = objects[0]

        # Check for UV map
        if not target_obj.data.uv_layers:
            print(f"  Warning: Object '{target_obj.name}' has no UV map, cannot bake AO")
            return None

        print(f"  Baking AO on object: {target_obj.name}")

        # Convert resolution string to int
        res = int(resolution)

        # Create a new image for baking
        bake_image = bpy.data.images.new(
            name=f"{material.name}_AO_baked",
            width=res,
            height=res,
            alpha=False
        )

        # Create a temporary image texture node for baking
        nodes = material.node_tree.nodes
        temp_node = nodes.new('ShaderNodeTexImage')
        temp_node.image = bake_image
        temp_node.select = True
        nodes.active = temp_node

        # Store original settings
        original_engine = context.scene.render.engine
        original_active = context.view_layer.objects.active
        original_samples = context.scene.cycles.samples

        # Configure for baking
        context.scene.render.engine = 'CYCLES'
        context.view_layer.objects.active = target_obj
        context.scene.cycles.samples = 32  # Reasonable quality for AO

        # Note: AO distance (how far rays travel) uses Blender's default settings
        # In Blender 5.0, this is controlled by Cycles render settings

        try:
            # Bake AO
            print(f"    Baking with {context.scene.cycles.samples} samples at {res}x{res}...")
            bpy.ops.object.bake(type='AO')

            # Debug: Check if image has any variation
            pixels = list(bake_image.pixels)
            if pixels:
                min_val = min(pixels)
                max_val = max(pixels)
                avg_val = sum(pixels) / len(pixels)
                print(f"    Range: {min_val:.2f} - {max_val:.2f}, Avg: {avg_val:.2f}")

        except Exception as e:
            print(f"  Error baking AO: {e}")
            bpy.data.images.remove(bake_image)
            context.scene.render.engine = original_engine
            context.view_layer.objects.active = original_active
            context.scene.cycles.samples = original_samples
            # Remove temp node
            try:
                nodes.remove(temp_node)
            except:
                pass  # Node may already be removed
            return None
        finally:
            # Restore settings
            context.scene.render.engine = original_engine
            context.view_layer.objects.active = original_active
            context.scene.cycles.samples = original_samples

            # Remove temp node if it still exists
            try:
                nodes.remove(temp_node)
            except:
                pass  # Node may already be removed or invalid

        return bake_image

    def bake_emission(self, context, material, resolution):
        """Bake emission for a material"""
        # Find objects using this material
        objects = [obj for obj in context.selected_objects
                   if obj.type == 'MESH' and material in [slot.material for slot in obj.material_slots]]

        if not objects:
            print(f"  Warning: No objects found with material {material.name}")
            return None

        # Convert resolution string to int
        res = int(resolution)

        # Create a new image for baking
        bake_image = bpy.data.images.new(
            name=f"{material.name}_Emission_baked",
            width=res,
            height=res,
            alpha=False
        )

        # Create a temporary image texture node for baking
        nodes = material.node_tree.nodes
        temp_node = nodes.new('ShaderNodeTexImage')
        temp_node.image = bake_image
        temp_node.select = True
        nodes.active = temp_node

        # Store original render engine and switch to Cycles
        original_engine = context.scene.render.engine
        context.scene.render.engine = 'CYCLES'

        try:
            # Bake
            print(f"    Baking at {res}x{res}...")
            bpy.ops.object.bake(type='EMIT')
        except Exception as e:
            print(f"  Error baking Emission: {e}")
            bpy.data.images.remove(bake_image)
            context.scene.render.engine = original_engine
            # Remove temp node
            try:
                nodes.remove(temp_node)
            except:
                pass  # Node may already be removed
            return None
        finally:
            # Restore settings
            context.scene.render.engine = original_engine

            # Remove temp node if it still exists
            try:
                nodes.remove(temp_node)
            except:
                pass  # Node may already be removed or invalid

        return bake_image

    def bake_material_combined(self, context, material, resolution):
        """Bake the entire material appearance (for custom shaders without Principled BSDF)"""
        # Find objects using this material
        objects = [obj for obj in context.selected_objects
                   if obj.type == 'MESH' and material in [slot.material for slot in obj.material_slots]]

        if not objects:
            print(f"  Warning: No objects found with material {material.name}")
            return None

        # Use the first object with this material
        target_obj = objects[0]

        # Check for UV map
        if not target_obj.data.uv_layers:
            print(f"  Warning: Object '{target_obj.name}' has no UV map, cannot bake")
            return None

        print(f"  ⏳ Baking custom shader appearance (this may take a moment)...")
        print(f"    Using object: {target_obj.name}")

        # Convert resolution to int if it's a string or use directly if it's an int
        if isinstance(resolution, str):
            res = int(resolution)
        else:
            res = resolution

        # Create a new image for baking
        bake_image = bpy.data.images.new(
            name=f"{material.name}_Combined_baked",
            width=res,
            height=res,
            alpha=True
        )

        # Create a temporary image texture node for baking
        # For materials without a node tree, we need to handle differently
        if not material.use_nodes or not material.node_tree:
            print(f"  Warning: Material has no node tree, cannot bake")
            bpy.data.images.remove(bake_image)
            return None

        nodes = material.node_tree.nodes
        temp_node = nodes.new('ShaderNodeTexImage')
        temp_node.image = bake_image
        temp_node.select = True
        nodes.active = temp_node

        # Store original settings
        original_engine = context.scene.render.engine
        original_active = context.view_layer.objects.active
        original_samples = context.scene.cycles.samples if hasattr(context.scene, 'cycles') else 32

        # Configure for baking
        context.scene.render.engine = 'CYCLES'
        context.view_layer.objects.active = target_obj
        if hasattr(context.scene, 'cycles'):
            context.scene.cycles.samples = 32  # Reasonable quality

        try:
            # Bake Combined (full material appearance)
            print(f"    Baking with {context.scene.cycles.samples if hasattr(context.scene, 'cycles') else 32} samples at {res}x{res}...")
            bpy.ops.object.bake(type='COMBINED')

            # Debug: Check if image has data
            pixels = list(bake_image.pixels)
            if pixels:
                avg_val = sum(pixels) / len(pixels)
                print(f"    Average pixel value: {avg_val:.2f}")

        except Exception as e:
            print(f"  Error baking combined: {e}")
            bpy.data.images.remove(bake_image)
            context.scene.render.engine = original_engine
            context.view_layer.objects.active = original_active
            if hasattr(context.scene, 'cycles'):
                context.scene.cycles.samples = original_samples
            # Remove temp node
            try:
                nodes.remove(temp_node)
            except:
                pass
            return None
        finally:
            # Restore settings
            context.scene.render.engine = original_engine
            context.view_layer.objects.active = original_active
            if hasattr(context.scene, 'cycles'):
                context.scene.cycles.samples = original_samples

            # Remove temp node if it still exists
            try:
                nodes.remove(temp_node)
            except:
                pass

        return bake_image

    def sanitize_filename(self, name):
        """Remove invalid characters from filename"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name


class HZ_PT_TexturePackerPanel(bpy.types.Panel):
    """UI Panel for Horizon Worlds Texture Packer"""
    bl_label = "Horizon Worlds Texture Packer"
    bl_idname = "HZ_PT_texture_packer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Horizon Tools'
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.hz_texture_packer

        layout.label(text="Pack PBR to BR/MEO Format")

        # Material name validation
        box = layout.box()
        box.label(text="Material Validation:", icon='CHECKMARK')
        box.operator("hz.validate_material_names", text="Validate Material Names", icon='SORTALPHA')

        layout.separator()

        layout.prop(props, "output_path")
        layout.prop(props, "default_resolution")

        layout.separator()

        # Baking options
        box = layout.box()
        box.label(text="Auto-Bake Options:", icon='RENDER_STILL')
        box.prop(props, "auto_bake_ao")
        box.prop(props, "auto_bake_emission")
        box.prop(props, "bake_resolution")

        layout.separator()

        row = layout.row()
        row.scale_y = 2.0
        row.operator("hz.pack_textures", icon='IMAGE_DATA')

        layout.separator()

        # Material suffix reference table (collapsible)
        box = layout.box()
        col = box.column(align=True)

        # Header with expand/collapse icon
        row = col.row()
        icon = 'TRIA_DOWN' if props.show_suffix_table else 'TRIA_RIGHT'
        row.prop(props, 'show_suffix_table',
                 text="Material Suffix Reference",
                 icon=icon,
                 emboss=False)

        # Show table content when expanded
        if props.show_suffix_table:
            col.separator()

            # Table header
            row = col.row()
            row.label(text="Material Suffix")
            row.label(text="Output Files")

            col.separator()

            # Standard materials
            row = col.row()
            row.label(text="(none)")
            row.label(text="Name_BR.png (+ Name_MEO.png)*")

            # _Metal
            row = col.row()
            row.label(text="_Metal")
            row.label(text="Name_BR.png")

            # _Blend
            row = col.row()
            row.label(text="_Blend")
            row.label(text="Name_BA.png")

            # _Transparent
            row = col.row()
            row.label(text="_Transparent")
            row.label(text="Name_BR.png + Name_MESA.png")

            # _VXM
            row = col.row()
            row.label(text="_VXM")
            row.label(text="Name_BR.png (+ Name_MEO.png)*")

            # _MaskedVXM
            row = col.row()
            row.label(text="_MaskedVXM")
            row.label(text="Name_BA.png")

            # _Masked
            row = col.row()
            row.label(text="_Masked")
            row.label(text="Name_BA.png")

            # _VXC
            row = col.row()
            row.label(text="_VXC")
            row.label(text="(no files - vertex color only)")

            # _UIO
            row = col.row()
            row.label(text="_UIO")
            row.label(text="Name_BA.png")

            col.separator()

            # Note about conditional exports
            note_box = col.box()
            note_box.scale_y = 0.7
            note_box.label(text="* MEO exported if metallic/emission/AO present", icon='INFO')

        layout.separator()

        # Footer logo
        icon_img = None
        if 'icon.png' in bpy.data.images:
            icon_img = bpy.data.images['icon.png']
        else:
            # Try to load icon.png from the addon directory
            addon_dir = os.path.dirname(os.path.realpath(__file__))
            icon_path = os.path.join(addon_dir, 'icon.png')
            if os.path.exists(icon_path):
                try:
                    icon_img = bpy.data.images.load(icon_path, check_existing=True)
                except:
                    pass

        if icon_img:
            # Display the image using template_preview
            box = layout.box()
            box.template_preview(icon_img, show_buttons=False)


class HZ_InvalidMaterialItem(bpy.types.PropertyGroup):
    """Property group to store invalid material info"""
    material_name: bpy.props.StringProperty(name="Material Name")
    reason: bpy.props.StringProperty(name="Reason")
    material_ptr: bpy.props.PointerProperty(type=bpy.types.Material)


class HZ_TexturePackerProperties(bpy.types.PropertyGroup):
    """Properties for Horizon Texture Packer"""
    output_path: bpy.props.StringProperty(
        name="Output Directory",
        description="Directory to save packed textures",
        default="//textures_packed/",
        subtype='DIR_PATH'
    )

    default_resolution: bpy.props.IntProperty(
        name="Default Resolution",
        description="Resolution to use when no source textures are found",
        default=2048,
        min=256,
        max=8192
    )

    auto_bake_ao: bpy.props.BoolProperty(
        name="Auto-bake AO",
        description="Automatically bake Ambient Occlusion if not found",
        default=False
    )

    auto_bake_emission: bpy.props.BoolProperty(
        name="Auto-bake Emission",
        description="Automatically bake Emission if not found",
        default=False
    )

    bake_resolution: bpy.props.EnumProperty(
        name="Bake Resolution",
        description="Resolution for baked textures",
        items=[
            ('512', '512', 'Fast bake, lower quality'),
            ('1024', '1024', 'Balanced quality and speed'),
            ('2048', '2048', 'High quality (recommended)'),
            ('4096', '4096', 'Very high quality, slow bake'),
        ],
        default='2048'
    )

    show_suffix_table: bpy.props.BoolProperty(
        name="Show Material Suffix Reference",
        description="Show/hide the material suffix reference table",
        default=False
    )


classes = (
    HZ_InvalidMaterialItem,
    HZ_TexturePackerProperties,
    HZ_OT_ValidateMaterialNames,
    HZ_OT_PackTextures,
    HZ_PT_TexturePackerPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.hz_texture_packer = bpy.props.PointerProperty(type=HZ_TexturePackerProperties)
    bpy.types.Scene.hz_invalid_materials = bpy.props.CollectionProperty(type=HZ_InvalidMaterialItem)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.hz_texture_packer
    del bpy.types.Scene.hz_invalid_materials


if __name__ == "__main__":
    register()