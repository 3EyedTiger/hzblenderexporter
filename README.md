![https://github.com/3EyedTiger/hzblenderexporter/blob/d8d9c1148e0c7caac3d07fa7eefbd33d477b7acd/icon.png](https://github.com/3EyedTiger/hzblenderexporter/blob/d8d9c1148e0c7caac3d07fa7eefbd33d477b7acd/icon.png)

# Horizon Worlds Texture Packer

A Blender addon that packs PBR textures into Horizon Worlds-optimized BR and MEO formats, validates material names, and exports meshes to FBX.

## Features

- **Texture Packing**: Converts PBR textures into Horizon Worlds format
  - BR texture: RGB = Base Color, Alpha = Roughness (always exported)
  - MEO texture: R = Metallic, G = Emission, B = Ambient Occlusion (exported only when data is present)
- **Auto-Baking**: Automatically bakes AO and Emission maps if missing
- **Material Validation**: Validates and auto-renames materials to meet Horizon Worlds naming requirements
- **FBX Export**: Automatically exports selected meshes alongside packed textures (added in v1.1.0)

## Installation

1. Download or clone this repository
2. In Blender, go to `Edit > Preferences > Add-ons`
3. Click `Install...` and select `vrc_texture_packer.py`
4. Enable the addon by checking the box next to "Material: Horizon Worlds Texture Packer"

## Usage

### Basic Workflow

1. Open the sidebar in the 3D Viewport (press `N`)
2. Navigate to the "Horizon Tools" tab
3. Select your mesh(es)
4. Configure settings:
   - Set output directory
   - Choose texture resolution
   - Enable auto-baking if needed
5. Click "Pack Selected"

### Material Validation

Horizon Worlds has strict material naming rules:
- Only alphanumeric characters (no spaces or underscores)
- Cannot start with a number
- Allowed suffixes: `_Transparent`, `_Masked`, `_MaskedVXM`, `_VXC`, `_VXM`, `_Blend`, `_Unlit`, `_UIO`, `_Metal`

### Special Material Suffixes

Some material suffixes trigger special export behaviors:

#### `_Metal` Materials
Materials ending with `_Metal` export only a BR texture with:
- RGB channels = Base Color (albedo/diffuse)
- Alpha channel = Metallic value or map

The output file will be named `MaterialName_BR.png` (the `_Metal` suffix is removed from the filename).

**Example:**
- Material name: `SteelBeam_Metal`
- Output file: `SteelBeam_BR.png` (only BR, no MEO)

#### `_Blend` Materials
Materials ending with `_Blend` export only a BA texture with:
- RGB channels = Base Color (albedo/diffuse)
- Alpha channel = Transparency/Alpha from the base color texture

The output file will be named `MaterialName_BA.png` (the `_Blend` suffix is removed from the filename).

**Example:**
- Material name: `Glass_Blend`
- Output file: `Glass_BA.png` (only BA, no BR or MEO)

#### `_Transparent` Materials
Materials ending with `_Transparent` export two textures:
1. **BR texture** - Standard format:
   - RGB channels = Base Color (albedo/diffuse)
   - Alpha channel = Roughness value or map
2. **MESA texture** - Special transparent format:
   - Red channel = Metallic value or map
   - Green channel = Specular value or map
   - Blue channel = Emission value or map (converted to grayscale)
   - Alpha channel = Transparency/Alpha from the base color texture

The output files will be named `MaterialName_BR.png` and `MaterialName_MESA.png` (the `_Transparent` suffix is removed from the filename).

**Example:**
- Material name: `Window_Transparent`
- Output files: `Window_BR.png` and `Window_MESA.png`

#### `_Masked` Materials
Materials ending with `_Masked` export only a BA texture with:
- RGB channels = Base Color (albedo/diffuse)
- Alpha channel = Transparency/Alpha from the base color texture

The output file will be named `MaterialName_BA.png` (the `_Masked` suffix is removed from the filename).

**Example:**
- Material name: `Foliage_Masked`
- Output file: `Foliage_BA.png` (only BA, no BR or MEO)

#### `_MaskedVXM` Materials
Materials ending with `_MaskedVXM` export only a BA texture with:
- RGB channels = Base Color (albedo/diffuse)
- Alpha channel = Transparency/Alpha from the base color texture

The output file will be named `MaterialName_BA.png` (the `_MaskedVXM` suffix is removed from the filename).

**Note:** In Horizon Worlds, the vertex color is multiplied on top of this texture, making it ideal for adding variated tints using mesh vertex color information.

**Example:**
- Material name: `Grass_MaskedVXM`
- Output file: `Grass_BA.png` (only BA, no BR or MEO)
- The texture output is identical to `_Masked`, but Horizon Worlds will multiply vertex colors for tinting

#### `_VXC` Materials
Materials ending with `_VXC` are pure vertex color materials and **do not export any texture files**. The `_VXC` suffix is simply a marker that tells Horizon Worlds to use only vertex color data for this material.

**Note:** No texture images are generated for `_VXC` materials. All color information comes from the mesh's vertex colors in Horizon Worlds.

**Example:**
- Material name: `VertexPainted_VXC`
- Output files: None (vertex color only)

#### `_VXM` Materials
Materials ending with `_VXM` export a BR texture and optionally a MEO texture:
- **BR texture** (always exported):
  - RGB channels = Base Color (albedo/diffuse)
  - Alpha channel = Roughness value or map
- **MEO texture** (exported if metallic, emission, or AO data is present):
  - Red channel = Metallic value or map
  - Green channel = Emission value or map
  - Blue channel = Ambient Occlusion value or map

The output files will be named `MaterialName_BR.png` (and `MaterialName_MEO.png` if MEO data exists). The `_VXM` suffix is removed from the filename.

**Note:** In Horizon Worlds, the vertex color is multiplied on top of this texture, allowing for per-vertex tinting and gradients to provide more variance to the base texture.

**Example:**
- Material name: `RockSurface_VXM`
- Output files: `RockSurface_BR.png` (always) and `RockSurface_MEO.png` (if metallic/emission/AO present)
- The texture provides base color and roughness (and optionally metallic/emission/AO), while Horizon Worlds multiplies vertex colors for tinting

#### `_UIO` Materials
Materials ending with `_UIO` are user interface textures exported at incredibly high quality with only a BA texture:
- RGB channels = Base Color (albedo/diffuse)
- Alpha channel = Transparency/Alpha from the base color texture

The output file will be named `MaterialName_BA.png` (the `_UIO` suffix is removed from the filename).

**Note:** `_UIO` materials are designed for user interface elements where high visual quality is essential.

**Example:**
- Material name: `Button_UIO`
- Output file: `Button_BA.png` (only BA, no BR or MEO)

To validate materials:
1. Click "Validate Material Names"
2. Review any invalid materials
3. Click OK to auto-rename them

### Auto-Baking

If your materials don't have AO or Emission textures, enable auto-baking:
- Check "Auto-bake AO" and/or "Auto-bake Emission"
- Select bake resolution (1024, 2048, or 4096)
- The addon will automatically bake missing maps using Cycles

## Requirements

- Blender 3.0 or higher (tested on Blender 5.0)
- Cycles render engine (for auto-baking features)

## Output

The addon creates:
- `MaterialName_BR.png` - Base color + roughness texture (always created)
- `MaterialName_MEO.png` - Metallic + emission + AO texture (only created if metallic, emission, or AO data is present)
- `ObjectName.fbx` - Exported mesh file

All files are saved to the configured output directory.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Author

3 Eyed Tiger

## Version

1.11.0

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
