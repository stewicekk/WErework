# Metin2 compatibility matrix

| Area | Required behavior | Verification |
|---|---|---|
| Map open/save | Existing supported map files open and save without semantic drift | Golden map roundtrip |
| Map metadata | Name/type/ID/bounds/base XY/terrain count preserved | Unit + roundtrip |
| Terrain | Height/texture/chunk structure preserved | Golden terrain + binary/semantic diff |
| Textureset | Texture index mapping preserved | Fixture comparison |
| Attributes | Bit semantics and launcher-facing constraints preserved | Flag matrix |
| Water | Placement/height/cleanup semantics preserved | Water fixture |
| Objects | Identity, transform, type/class/property and ordering preserved where meaningful | Object roundtrip |
| Object IDs | Deterministic ID rules when enabled; no accidental collisions | CRC/ID fixture |
| Environment | Environment script/path and values preserved | Environment fixture |
| Regen/NPC | Load/save semantics preserved | regen fixture |
| Collision/MDATR | Editor diagnostics and export remain compatible | MDATR fixture |
| Minimap/MAI | Expected outputs and toggles preserved | Snapshot fixture |
| Shadow | Legacy output remains available; modern preview may be optional | Visual + smoke |
| Pack/Index | Packed and loose asset discovery follows deterministic precedence | Asset fixture |
| Property | Loose and packed property discovery is explicit | Property fixture |
| GR2/Granny | Version/backend compatibility is detected, not assumed | Fixture + capability report |
| SpeedTree | Missing/invalid SPT assets fail safely | Negative test |
| DDS/TGA | Header mismatch/missing/corrupt texture does not crash | Negative test |
| Export | Release-ready clean map export has no hidden editor-only files | Package diff |
| Backup | Save creates recoverable backup before destructive replacement | Recovery test |
| Undo/redo | Terrain/object mutations reverse correctly | Command test |
| Script API | Optional; disabled core still works | Headless/startup test |
| x86/x64 | Target-dependent configurations build where source/toolchain supports them | Build matrix |

## Reference compatibility baseline

`Debloat/WorldEditor-Renewal` publicly identifies Mainline + DX9 + Granny 2.11.8 + static DevIL 1.8.0 and describes direct integration into a ClientSource solution. The orchestrator must discover the real project rather than assume those versions are universal.

## ReMIX behavior targets

Public ReMIX material describes 64-bit support, DX11, embedded Python 3.8, undo/redo, auto-backup, pack/Index loading, one-click export, WASD navigation, server_attr generation, water tools, deterministic object IDs, terrain preloading, GR2 animation, object hierarchy, intersection picking and configuration-driven behavior. These are target behaviors; verify them against the actual public documentation before implementing each one.
