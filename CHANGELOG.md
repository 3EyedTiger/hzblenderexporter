# Changelog

All notable changes to the Horizon Worlds Texture Packer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.11.0] - 2026-01-22

### Added
- **`_UIO` material suffix support**: Materials ending with `_UIO` are now recognized as high-quality UI textures
  - Outputs only a BA texture (no BR or MEO)
  - RGB = Base Color/Albedo
  - Alpha = Transparency/Alpha from the base color texture
  - Output filename removes the `_UIO` suffix (e.g., `Button_UIO` → `Button_BA.png`)
  - Designed for incredibly high-quality user interface elements

### Changed
- Updated material suffix reference table to include `_UIO`
- Updated documentation to explain `_UIO` material export behavior

## [1.10.0] - 2026-01-22

### Added
- **Material Suffix Reference Table**: Added a collapsible reference table in the UI panel
  - Shows all material suffix types and their output files
  - Displays naming conventions for easy reference while editing materials
  - Can be expanded/collapsed to save space
  - Includes note about conditional MEO export for _VXM materials

### Changed
- **Standard materials now have optional MEO export**: Materials without special suffixes now only export MEO texture if metallic, emission, or AO data is present
  - BR texture is always exported
  - MEO texture is only created when metallic, emission, or ambient occlusion data is detected
  - Matches the same conditional export behavior as `_VXM` materials
  - Reduces unnecessary texture files when MEO data isn't needed
- Updated UI panel with collapsible reference section

## [1.9.0] - 2026-01-22

### Added
- **`_VXM` materials now support optional MEO texture export**: `_VXM` materials can now export a secondary MEO texture alongside the BR texture
  - MEO texture is automatically exported if metallic, emission, or ambient occlusion data is detected
  - MEO format: R = Metallic, G = Emission, B = Ambient Occlusion (same as standard MEO)
  - BR texture is always exported, MEO is conditional based on available data
  - Output filenames: `MaterialName_BR.png` (always) and `MaterialName_MEO.png` (conditional)

### Changed
- Updated `_VXM` material processing to search for and process AO textures (previously skipped)
- Updated documentation to explain `_VXM` optional MEO export behavior

## [1.8.0] - 2026-01-22

### Added
- **`_VXM` material suffix support**: Materials ending with `_VXM` now export with special behavior
  - Outputs only a BR texture (no MEO)
  - RGB = Base Color/Albedo
  - Alpha = Roughness value or map
  - Output filename removes the `_VXM` suffix (e.g., `RockSurface_VXM` → `RockSurface_BR.png`)
  - Uses the standard BR texture creation method
  - In Horizon Worlds, vertex color is multiplied on top of this texture for per-vertex tinting and gradients

### Changed
- Updated documentation to explain `_VXM` material export behavior

## [1.7.0] - 2026-01-22

### Added
- **`_VXC` material suffix support**: Materials ending with `_VXC` are now recognized as pure vertex color materials
  - No texture files are exported for `_VXC` materials
  - The suffix acts as a marker for Horizon Worlds to use only vertex color data
  - Material is successfully processed but skips texture generation entirely
  - Ideal for purely vertex-painted meshes without texture requirements

### Changed
- Updated documentation to explain `_VXC` material behavior

## [1.6.0] - 2026-01-22

### Added
- **`_MaskedVXM` material suffix support**: Materials ending with `_MaskedVXM` now export with special behavior
  - Outputs only a BA texture (no BR or MEO)
  - RGB = Base Color/Albedo
  - Alpha = Transparency/Alpha from the base color texture
  - Output filename removes the `_MaskedVXM` suffix (e.g., `Grass_MaskedVXM` → `Grass_BA.png`)
  - Uses the same export format as `_Blend` and `_Masked` materials
  - In Horizon Worlds, vertex color is multiplied on top of this texture for tinting variations

### Changed
- Updated `_Masked` material detection to exclude `_MaskedVXM` to prevent false positives
- Updated documentation to explain `_MaskedVXM` material export behavior

## [1.5.0] - 2026-01-22

### Added
- **`_Masked` material suffix support**: Materials ending with `_Masked` now export with special behavior
  - Outputs only a BA texture (no BR or MEO)
  - RGB = Base Color/Albedo
  - Alpha = Transparency/Alpha from the base color texture
  - Output filename removes the `_Masked` suffix (e.g., `Foliage_Masked` → `Foliage_BA.png`)
  - Uses the same export format as `_Blend` materials

### Changed
- Updated documentation to explain `_Masked` material export behavior

## [1.4.0] - 2026-01-22

### Added
- **`_Transparent` material suffix support**: Materials ending with `_Transparent` now export with special behavior
  - Outputs two textures: BR and MESA
  - **BR texture**: RGB = Base Color, Alpha = Roughness (standard format)
  - **MESA texture**: R = Metallic, G = Specular, B = Emission (grayscale), A = Alpha from base color
  - Output filenames remove the `_Transparent` suffix (e.g., `Window_Transparent` → `Window_BR.png` + `Window_MESA.png`)
- Added specular texture extraction from Principled BSDF shader

### Changed
- Updated documentation to explain `_Transparent` material export behavior

## [1.3.0] - 2026-01-22

### Added
- **`_Blend` material suffix support**: Materials ending with `_Blend` now export with special behavior
  - Outputs only a BA texture (no BR or MEO)
  - RGB = Base Color/Albedo
  - Alpha = Transparency/Alpha from the base color texture
  - Output filename removes the `_Blend` suffix (e.g., `Glass_Blend` → `Glass_BA.png`)

### Changed
- Updated documentation to explain `_Blend` material export behavior

## [1.2.0] - 2026-01-22

### Added
- **`_Metal` material suffix support**: Materials ending with `_Metal` now export with special behavior
  - Outputs only a BR texture (no MEO)
  - RGB = Base Color/Albedo
  - Alpha = Metallic value or map
  - Output filename removes the `_Metal` suffix (e.g., `SteelBeam_Metal` → `SteelBeam_BR.png`)
- Added `_Metal` to list of allowed material name suffixes

### Changed
- Material validation now accepts `_Metal` as a valid suffix
- Updated documentation to explain `_Metal` material export behavior

## [1.1.0] - 2026-01-22

### Added
- FBX export functionality integrated into "Pack Selected" button
  - Automatically exports selected meshes to the same output directory as packed textures
  - Single mesh exports use the mesh name for the FBX file
  - Multiple meshes export to "exported_meshes.fbx"
- Material name validator now checks ALL materials in the blend file (not just selected objects)
- MIT License file
- .gitignore file for version control
- README.md with complete documentation
- CHANGELOG.md to track version history

### Changed
- Renamed "Pack Textures" button to "Pack Selected" for clarity
- Fixed material name validator to scan entire blend file instead of only selected objects
- Fixed duplicate `execute()` method in material validator class

### Fixed
- Material validator now properly catches invalid material names like "wonder __dd" with spaces and underscores

## [1.0.0] - 2026-01-22

### Added
- Initial release
- PBR texture packing to BR (Base Color RGB + Roughness Alpha) format
- PBR texture packing to MEO (Metallic R + Emission G + AO B) format
- Auto-baking for Ambient Occlusion maps
- Auto-baking for Emission maps
- Material name validation for Horizon Worlds compliance
- Auto-rename functionality for invalid material names
- Support for allowed suffixes: _Transparent, _Masked, _MaskedVXM, _VXC, _VXM, _Blend, _Unlit, _UIO
- BFS node graph traversal to find textures through intermediate nodes
- Bilinear interpolation for texture resizing
- Configurable output directory
- Configurable texture resolution (1024, 2048, 4096)
- Configurable bake resolution
- Footer logo display in UI panel
- Blender 5.0 compatibility
