# Horizon Worlds Texture Packer

A Blender addon that packs PBR textures into Horizon Worlds-optimized BR and MEO formats, validates material names, and exports meshes to FBX.

## Features

- **Texture Packing**: Converts PBR textures into Horizon Worlds format
  - BR texture: RGB = Base Color, Alpha = Roughness
  - MEO texture: R = Metallic, G = Emission, B = Ambient Occlusion
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
- Allowed suffixes: `_Transparent`, `_Masked`, `_MaskedVXM`, `_VXC`, `_VXM`, `_Blend`, `_Unlit`, `_UIO`

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
- `MaterialName_BR.png` - Base color + roughness texture
- `MaterialName_MEO.png` - Metallic + emission + AO texture
- `ObjectName.fbx` - Exported mesh file

All files are saved to the configured output directory.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Author

3 Eyed Tiger

## Version

1.1.0

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
