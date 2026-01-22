# Changelog

All notable changes to the Horizon Worlds Texture Packer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
