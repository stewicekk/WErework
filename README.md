# Metin2 NewSchool WorldEditor

> Production-grade rework of a Metin2 WorldEditor with modern architecture, NewSchool UX, controlled compatibility and deterministic data handling.

---

## 1. Mission

Rebuild the current WorldEditor into a professional native Windows editor for Metin2 maps and world data.

The project may radically modernize:

* architecture
* renderer
* UI
* interaction model
* performance
* asset workflow
* tooling
* diagnostics
* automation

But it must **not silently change the meaning of supported Metin2 data**.

The core principle is:

```text
MODERN EDITOR
      ↓
CANONICAL DOMAIN MODEL
      ↓
EXPLICIT METIN2 COMPATIBILITY LAYER
      ↓
DETERMINISTIC SERIALIZATION
```

The editor is allowed to become modern.

The game-facing data semantics are not allowed to become accidental.

---

# 2. Primary Goals

The finished application should provide:

* professional NewSchool desktop UI
* modern 3D viewport
* fast map loading
* terrain editing
* texture / textureset workflow
* object placement
* NPC / mob / regen editing
* attribute editing
* water editing
* collision visualization
* environment editing
* shadows
* minimap workflow
* effects integration
* sound/BGM hooks
* pack/index integration
* deterministic saving
* backup and crash recovery
* undo/redo
* asset browser
* scene hierarchy
* inspector
* search/filter
* diagnostics
* validation
* CLI automation
* automated regression testing

The editor should feel like a **professional production tool**, not a legacy utility with a skin.

---

# 3. Compatibility Philosophy

Compatibility is based on evidence.

### Source-of-truth priority

1. actual checked-out target repository
2. existing implementation and build configuration
3. passing baseline tests
4. real Metin2 maps/assets
5. format structures discovered in source
6. verified public reference implementations
7. documented public behavior
8. generic engine conventions

Generic assumptions are the lowest priority.

If a generic 3D-engine design conflicts with actual Metin2 behavior, Metin2 behavior wins.

---

# 4. Reference Baseline

The public:

`Debloat/WorldEditor-Renewal`

may be used as a compatibility/reference baseline.

Relevant documented legacy ecosystem may include:

* EffectLib
* EterBase
* EterGrnLib
* EterImageLib
* EterLib
* EterLocale
* EterPack
* GameLib
* MilesLib
* ScriptLib
* SpeedTreeLib
* SphereLib
* WorldEditor

These are **reference integrations**, not unconditional dependencies.

The actual target repository must always be inspected first.

Do not hard-code a specific ClientSource tree into the new architecture.

---

# 5. Legacy Compatibility

The legacy renderer/data behavior must remain available through explicit boundaries.

Do not perform a blind:

```text
DX9 → DX11
```

replacement.

Instead:

```text
Legacy Backend
      │
      ├── Compatibility Adapter
      │
      ▼
Canonical Editor Model
      ▲
      │
Modern Editor Backend
```

Modern rendering may provide:

* improved viewport
* dynamic lighting
* shadows
* diagnostics
* overlays
* GPU acceleration
* modern materials
* editor-only effects

Modern rendering must not silently modify serialized map data.

---

# 6. Architecture

Preferred architecture:

```text
Application
│
├── Core
│   ├── Result / Error
│   ├── Logging
│   ├── Memory
│   ├── Threading
│   └── Services
│
├── Platform
│   ├── Windows
│   ├── Input
│   └── Window
│
├── Editor
│   ├── Document
│   ├── Scene
│   ├── Selection
│   ├── Commands
│   ├── Undo/Redo
│   └── Workspace
│
├── Metin2
│   ├── VFS
│   ├── Map
│   ├── Terrain
│   ├── Objects
│   ├── Attributes
│   ├── Water
│   ├── Environment
│   ├── Regen
│   ├── Textureset
│   └── Serialization
│
├── Assets
│   ├── GR2
│   ├── SMD
│   ├── FBX
│   ├── DDS
│   ├── MSE
│   └── MDE
│
├── Renderer
│   ├── Legacy
│   ├── DX11
│   ├── Terrain
│   ├── Materials
│   ├── Shadows
│   ├── Particles
│   └── Debug
│
├── UI
│   ├── Workspace
│   ├── Viewport
│   ├── Inspector
│   ├── Hierarchy
│   ├── AssetBrowser
│   ├── Tools
│   └── Diagnostics
│
└── CLI
    ├── Validate
    ├── Inspect
    ├── Convert
    └── Regression
```

Keep:

```text
DATA
≠
EDITOR STATE
≠
RENDERER STATE
≠
UI STATE
```

---

# 7. Strangler Architecture

Do not rewrite the entire legacy application in one pass.

Use:

```text
Existing System
      ↓
Adapter
      ↓
Canonical Model
      ↓
New System
```

Replace components gradually.

Every migration must have:

* old behavior identified
* new implementation
* compatibility bridge
* tests
* regression verification
* removal plan for obsolete code

---

# 8. Metin2 Data Domains

The editor must be prepared to handle the real structures used by the target client.

Important domains include:

```text
MAP
├── Setting
├── HeightMap
├── TileMap
├── WaterMap
├── Attribute
├── Textureset
├── Environment
├── Objects
├── Regen
├── Collision
├── Minimap
├── Shadows
├── Effects
└── Audio/BGM
```

Potential asset formats include:

```text
.prb
.prt
.pre
.pda
.smd
.gr2
.fbx
.dds
.mse
.mde
```

Do not assume every client uses every format.

Detect capabilities from the actual project.

---

# 9. Lossless Data Policy

Whenever possible:

```text
Unknown data
      ↓
Preserve
      ↓
Write back unchanged
```

Do not discard unknown fields merely because the editor does not expose them yet.

When exact preservation is impossible:

1. detect it;
2. report it;
3. prevent silent corruption;
4. add a regression fixture;
5. document the limitation.

---

# 10. Canonical Editor Model

The editor should operate on a normalized internal representation.

Example:

```text
MapDocument
 ├── Metadata
 ├── Terrain
 ├── TextureSet
 ├── Water
 ├── Attributes
 ├── Objects
 ├── Spawns/Regen
 ├── Environment
 ├── Effects
 └── Unknown/Preserved Data
```

Serialization adapters translate between:

```text
Metin2 files
      ↕
Canonical model
```

Never make the UI directly manipulate raw binary/text structures.

---

# 11. Terrain

Terrain system should support:

* height editing
* smoothing
* flattening
* leveling
* controlled noise
* falloff
* texture painting
* water editing
* attribute painting
* terrain picking
* brush preview
* chunk updates
* frustum culling
* optional LOD
* diagnostics

Avoid full-map GPU rebuilds for local edits.

Prefer dirty regions:

```text
Brush
 ↓
Dirty Region
 ↓
CPU/Data Update
 ↓
GPU Partial Update
```

---

# 12. World Objects

Objects must support:

* placement
* deletion
* duplication
* multi-selection
* translation
* rotation
* scaling
* snapping
* alignment
* focus
* hide/isolate
* visibility groups
* source tracking
* transform validation

Every object should have stable identity inside the editor.

---

# 13. Picking

Required picking layers:

```text
Terrain
Object
Mesh
Submesh
Vertex
Bone
Water
Attribute
```

Selection priority must be deterministic.

Example:

```text
Bone
↓
Submesh
↓
Object
↓
Terrain
```

when appropriate to the active editor mode.

---

# 14. Undo / Redo

All meaningful mutations must use commands.

```text
User Action
 ↓
Command
 ↓
Apply
 ↓
Record
 ↓
Undo / Redo
```

Commands should support:

* object transforms
* placement
* deletion
* terrain edits
* texture edits
* water edits
* attribute edits
* property changes

No hidden mutations outside the command system.

---

# 15. NewSchool UI

The UI must prioritize:

```text
Clarity
↓
Speed
↓
Workflow
↓
Consistency
↓
Visual polish
```

Not the other way around.

Recommended layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ GLOBAL TOOLBAR / WORKSPACE / SEARCH / FILE                  │
├──────────────┬──────────────────────────────┬───────────────┤
│              │                              │               │
│ TOOL / ASSET │                              │ HIERARCHY /   │
│ PANEL        │          3D VIEWPORT         │ INSPECTOR     │
│              │                              │               │
│              │                              │               │
├──────────────┴──────────────────────────────┴───────────────┤
│ CONSOLE / STATUS / OUTPUT / TIMELINE / DIAGNOSTICS          │
└──────────────────────────────────────────────────────────────┘
```

Required:

* docking
* DPI scaling
* 1366×768 support
* 1920×1080 baseline
* 1440p
* 4K
* responsive panel widths
* persistent layouts
* search
* contextual inspectors
* keyboard navigation
* tooltips
* clear selection state
* consistent icons
* non-modal workflow

---

# 16. Visual Direction

NewSchool visual language:

* dark
* clean
* high-tech
* restrained
* professional
* dense but readable
* strong hierarchy
* subtle accents
* minimal decoration

Avoid:

* excessive glow
* giant buttons
* unnecessary gradients
* random colors
* oversized panels
* excessive modal dialogs
* decorative UI without function

---

# 17. Input

Centralized input system.

Baseline shortcuts:

```text
WASD        Camera
QE          Vertical camera
RMB         Look
MMB         Pan
Wheel       Zoom
W           Translate
E           Rotate
R           Scale
F           Focus
Delete      Delete
Ctrl+D      Duplicate
Ctrl+Z      Undo
Ctrl+Y      Redo
Ctrl+S      Save
Ctrl+Shift+S Save As
Tab         Editor mode
```

Do not scatter keyboard handling across unrelated panels.

---

# 18. Performance

Target principles:

* no unnecessary per-frame allocations
* resource caching
* asynchronous loading where safe
* lazy asset loading
* GPU resource reuse
* frustum culling
* batching
* instancing
* partial terrain updates
* minimal render-state changes
* responsive UI
* cancellation for long operations

Expose diagnostics:

```text
FPS
Frame Time
Draw Calls
Triangles
Visible Objects
Loaded Assets
CPU Time
GPU Time
Memory
Terrain Chunks
```

---

# 19. Safety

Mandatory:

* RAII
* smart pointers for ownership
* explicit lifetime for async tasks
* bounds checks
* finite float validation
* terrain coordinate validation
* null/state validation
* transactional saves
* backup before destructive replacement
* cancellation
* main-thread handoff for UI/GPU state

Never allow:

```text
load failure → stale document
failed save → destroyed original
deleted object → dangling selection
async completion → dead object access
invalid transform → NaN scene state
```

---

# 20. Save / Recovery

Saving:

```text
Edit
 ↓
Validate
 ↓
Write Temporary
 ↓
Flush
 ↓
Validate Temporary
 ↓
Backup Original
 ↓
Atomic Replace
```

Support:

* autosave
* backup
* crash recovery
* dirty state
* save validation
* recovery detection

---

# 21. CLI

CLI must reuse the same core libraries as the GUI.

Possible commands:

```text
validate
info
map-info
asset-info
validate-map
validate-asset
convert
regression
```

Never implement a second independent parser only for CLI.

---

# 22. Multi-Agent System

Recommended agents:

```text
orchestrator
explorer
architect
build-engineer
metin2-specialist
data-engineer
terrain-engineer
renderer-engineer
asset-engineer
editor-tools
ui-ux
performance
qa
reviewer
release
```

Each specialist owns a domain but must obey `AGENTS.md`.

---

# 23. Agent Workflow

Every meaningful task follows:

```text
INSPECT
 ↓
UNDERSTAND
 ↓
PLAN
 ↓
IMPLEMENT
 ↓
BUILD
 ↓
TEST
 ↓
REVIEW
 ↓
REGRESSION
 ↓
REPORT
```

Never:

```text
PROMPT
 ↓
BLIND CODE
 ↓
DONE
```

---

# 24. First Run

The first operation in a new checkout is always:

```text
Repository Audit
```

Inspect:

* complete tree
* build files
* projects
* solution files
* CMake
* source
* headers
* resources
* scripts
* data
* dependencies
* DLLs
* preprocessor definitions
* include paths
* linker inputs
* runtime paths

Then produce:

```text
docs/baseline/
```

with:

```text
repository.md
build.md
dependencies.md
architecture.md
runtime.md
formats.md
ui.md
risks.md
baseline-results.md
```

Only then begin migration.

---

# 25. Wave Model

Use incremental waves.

```text
WAVE 0   Recon
WAVE 1   Baseline
WAVE 2   Architecture
WAVE 3   Build Stabilization
WAVE 4   Data/VFS
WAVE 5   Terrain
WAVE 6   Scene/Object
WAVE 7   Renderer
WAVE 8   Editor Tools
WAVE 9   UI/UX
WAVE 10  Performance
WAVE 11  QA
WAVE 12  Release
```

Additional waves may be created when required.

Never force a wave to finish if its exit criteria are not met.

---

# 26. Wave Exit Criteria

Every wave must have:

```text
IMPLEMENTED
BUILD GREEN
TARGETED TESTS GREEN
REGRESSION GREEN
RUNTIME CHECK
DOCUMENTATION
KNOWN RISKS
```

---

# 27. Git Rules

Never:

* reset user work
* force push
* delete unrelated changes
* rewrite history for cosmetic reasons
* checkout over uncommitted user changes

Before large modifications:

```text
git status
git diff
```

After modifications:

```text
git diff
git status
```

Keep logical checkpoints.

---

# 28. Definition of Done

The project is DONE only when:

* clean build works
* Release build works
* Debug build works
* tests pass
* real Metin2 data has been tested
* map load/save roundtrip is verified
* no critical regression exists
* UI is production-ready
* renderer is stable
* undo/redo works
* save/recovery works
* diagnostics work
* packaging works
* documentation reflects reality

"Compiles" is not "Done".

---

# 29. Final Principle

The project should become:

> **A modern, fast, professional Metin2 WorldEditor that respects the original game's data and behavior while replacing the old editing experience with a dramatically better production workflow.**

Modernize the editor.

Preserve the game.

Verify everything.
