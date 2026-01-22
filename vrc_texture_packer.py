bl_info = {
    "name": "Horizon Worlds Texture Packer",
    "author": "3 Eyed Tiger",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Horizon Tools",
    "description": "Pack PBR textures into Horizon Worlds-optimized BR and MEO format",
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
    - Allowed suffixes: _Transparent, _Masked, _MaskedVXM, _VXC, _VXM, _Blend, _Unlit, _UIO
    """
    ALLOWED_SUFFIXES = ['_Transparent', '_Masked', '_MaskedVXM', '_VXC', '_VXM', '_Blend', '_Unlit', '_UIO']

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
    ALLOWED_SUFFIXES = ['_Transparent', '_Masked', '_MaskedVXM', '_VXC', '_VXM', '_Blend', '_Unlit', '_UIO']

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
    """Pack PBR textures and export selected meshes"""
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
        
        processed_count = 0
        for mat in materials:
            success = self.process_material(mat, output_dir, context)
            if success:
                processed_count += 1

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
                bpy.ops.export_scene.fbx(
                    filepath=fbx_path,
                    use_selection=True,
                    object_types={'MESH'},
                    use_mesh_modifiers=True,
                    add_leaf_bones=False,
                    bake_anim=False
                )
                print(f"Exported FBX to: {fbx_path}")
                self.report({'INFO'}, f"Processed {processed_count} materials and exported {len(selected_meshes)} mesh(es)")
            except Exception as e:
                print(f"Error exporting FBX: {e}")
                self.report({'WARNING'}, f"Processed {processed_count} materials but FBX export failed: {e}")
        else:
            self.report({'INFO'}, f"Processed {processed_count} materials")

        return {'FINISHED'}
    
    def process_material(self, mat, output_dir, context):
        """Process a single material and pack its textures"""
        props = context.scene.hz_texture_packer

        # Find Principled BSDF node
        principled = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break

        if not principled:
            self.report({'WARNING'}, f"Material '{mat.name}' has no Principled BSDF")
            return False

        # Extract texture paths
        textures = {
            'base_color': self.get_texture_from_socket(principled.inputs['Base Color']),
            'roughness': self.get_texture_from_socket(principled.inputs['Roughness']),
            'metallic': self.get_texture_from_socket(principled.inputs['Metallic']),
            'emission': self.get_texture_from_socket(principled.inputs['Emission Color']),
            'ao': None  # AO is typically not directly connected to Principled BSDF
        }

        # Debug output
        print(f"\nProcessing material: {mat.name}")
        for key, tex in textures.items():
            if tex:
                print(f"  {key}: {tex.name} ({tex.size[0]}x{tex.size[1]})")
            else:
                print(f"  {key}: None")

        # Try to find AO texture from other nodes (common setup)
        for node in mat.node_tree.nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                img_name = node.image.name.lower()
                if 'ao' in img_name or 'occlusion' in img_name or 'ambient' in img_name:
                    textures['ao'] = node.image
                    print(f"  Found AO texture by name search: {node.image.name}")
                    break

        # Auto-bake if enabled
        if props.auto_bake_ao and not textures['ao']:
            print(f"  Auto-baking AO for {mat.name}...")
            textures['ao'] = self.bake_ao(context, mat, props.bake_resolution)

        if props.auto_bake_emission and not textures['emission']:
            print(f"  Auto-baking Emission for {mat.name}...")
            textures['emission'] = self.bake_emission(context, mat, props.bake_resolution)
        
        # Determine resolution
        resolution = self.get_resolution(textures, props.default_resolution)
        
        # Create packed textures
        br_image = self.create_br_texture(textures, resolution)
        meo_image = self.create_meo_texture(textures, resolution)

        # Save images
        safe_name = self.sanitize_filename(mat.name)
        br_path = os.path.join(output_dir, f"{safe_name}_BR.png")
        meo_path = os.path.join(output_dir, f"{safe_name}_MEO.png")

        # Save using Blender's image save
        br_image.filepath_raw = br_path
        br_image.file_format = 'PNG'
        br_image.save()

        meo_image.filepath_raw = meo_path
        meo_image.file_format = 'PNG'
        meo_image.save()

        # Clean up temporary images
        bpy.data.images.remove(br_image)
        bpy.data.images.remove(meo_image)

        # Clean up baked images (AO and Emission)
        for key in ['ao', 'emission']:
            if textures[key] and textures[key].name.endswith('_baked'):
                print(f"  Cleaning up baked image: {textures[key].name}")
                bpy.data.images.remove(textures[key])

        print(f"Saved {safe_name}_BR.png and {safe_name}_MEO.png")
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
            print(f"  Running AO bake with {context.scene.cycles.samples} samples...")
            bpy.ops.object.bake(type='AO')
            print(f"  Successfully baked AO texture")

            # Debug: Check if image has any variation
            pixels = list(bake_image.pixels)
            if pixels:
                min_val = min(pixels)
                max_val = max(pixels)
                avg_val = sum(pixels) / len(pixels)
                print(f"  AO Bake stats - Min: {min_val:.3f}, Max: {max_val:.3f}, Avg: {avg_val:.3f}")

        except Exception as e:
            print(f"  Error baking AO: {e}")
            bpy.data.images.remove(bake_image)
            nodes.remove(temp_node)
            context.scene.render.engine = original_engine
            context.view_layer.objects.active = original_active
            context.scene.cycles.samples = original_samples
            return None
        finally:
            # Restore settings
            context.scene.render.engine = original_engine
            context.view_layer.objects.active = original_active
            context.scene.cycles.samples = original_samples

            # Remove temp node
            nodes.remove(temp_node)

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
            bpy.ops.object.bake(type='EMIT')
            print(f"  Successfully baked Emission texture")
        except Exception as e:
            print(f"  Error baking Emission: {e}")
            bpy.data.images.remove(bake_image)
            nodes.remove(temp_node)
            context.scene.render.engine = original_engine
            return None
        finally:
            # Restore settings
            context.scene.render.engine = original_engine

            # Remove temp node
            nodes.remove(temp_node)

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

        box = layout.box()
        box.label(text="Output Format:", icon='INFO')
        box.label(text="BR: RGB=BaseColor, A=Roughness")
        box.label(text="MEO: R=Metallic, G=Emission, B=AO")

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