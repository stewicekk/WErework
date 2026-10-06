# WorldEditor ReMIX behavior research

Primary public sources:

- https://worldeditorremix.github.io/
- https://github.com/WorldEditorRemix/Docs/blob/main/docs/CONFIGURATION.md
- https://github.com/WorldEditorRemix/Docs/blob/main/docs/SCRIPTING.md
- https://github.com/WorldEditorRemix/Docs/blob/main/docs/API_REFERENCE.md
- https://github.com/WorldEditorRemix/Docs/blob/main/docs/TERRAIN_OPERATIONS.md
- https://github.com/WorldEditorRemix/Docs/blob/main/docs/SHORTCUTS.md
- https://github.com/WorldEditorRemix/Docs/blob/main/docs/UI.md
- https://github.com/WorldEditorRemix/Docs/blob/main/docs/KNOWN_ISSUES.md

## Current public ReMIX claims/behavior

The public project page currently describes v60 as a drop-in replacement with native 64-bit support, embedded Python 3.8, DX11 rendering, undo/redo, auto-backup, direct pack/Index loading, map export, WASD navigation, server_attr generation and water tools. It also publishes 200+ API functions and 35+ bug fixes.

The configuration documentation exposes useful engineering targets such as window dimensions/FOV, camera movement/zoom, F6/Insert behavior, atlas/minimap options, MDATR height detection, fog defaults, automatic backups, deterministic object IDs from CRC, terrain preloading, embedded scripting, GR2 animation, new compass, object hierarchy and intersection-based picking.

The shortcut documentation maps `Ctrl+S`, `Insert/F6`, `F5`, `R`, `H`, `Y`, `T`, WASD/arrow movement, `F11` wireframe and several diagnostic controls. Preserve compatibility where possible, but make conflicts visible in a shortcut editor.

The scripting docs describe an embedded Python 3.8 runtime, a single `WorldEditorRemix.py` entry point run by F5, a native `WorldEditor` extension, wrapper helpers, terrain operation helpers and logging through `dbg`. The docs explicitly warn that scripts run synchronously on the editor main thread and that map-readiness checks are essential.

The known-issues page documents remaining problems around BGM, MDATR refresh, monster-area-info lag, multi-texture deletion, terrain texture caps, minimap/Ymir cache behavior, stale filenames on load failure, packed property discovery, water brush visibility and other edge cases. The orchestrator must convert these from tribal knowledge into explicit regression tests or redesigned safe failure paths.

## ReMIX V45-era features relevant to parity

Public release summaries mention reset rotation/height controls, refactored yaw/pitch/roll sliders, textual Ctrl+C/Ctrl+V across map instances, GR2 animation toggle, minimap effect snapshots, server_attr/atlas stability fixes, Python 3 expansion and TGA/DDS loading fixes.
