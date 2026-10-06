# Orchestration protocol

## Wave 0 — forensic baseline

No production redesign. Enumerate the full tree, projects, build configurations, runtime assets, dependencies, macros, source modules, map data flow, UI classes, render path and existing tests. Capture build output and a launch/smoke baseline where possible.

Deliverables: `docs/baseline/REPOSITORY_INVENTORY.md`, `DEPENDENCY_GRAPH.md`, `CURRENT_ARCHITECTURE.md`, `KNOWN_FAILURES.md`, `BASELINE_BUILD.md`.

## Wave 1 — compatibility shell

Introduce explicit configuration/path discovery and adapters around ClientSource libraries. Remove hidden assumptions such as fixed absolute paths from the new orchestration layer, but keep compatibility fallbacks where required. Establish deterministic runtime search order.

Gate: old workflow still opens/saves a known map.

## Wave 2 — canonical editor model

Introduce or normalize explicit models for map metadata, terrains, areas, objects, effects, environment, attributes, water, collision/MDATR and selection. Make identities and transforms explicit. No UI redesign yet.

Gate: load -> inspect -> save -> reload without semantic regression.

## Wave 3 — command/undo transaction layer

Centralize mutations through commands. Add save transactions, backup/recovery, dirty tracking and deterministic redo. Commands must be composable for terrain painting and object transforms.

Gate: undo/redo survives reload where supported; failed save leaves the previous map intact.

## Wave 4 — terrain vertical slice

Height, smoothing, flatten, plateau/ramp/noise hooks where compatible; texture brush, falloff, attributes, water and collision/height diagnostics. Add chunk-aware processing.

Gate: terrain golden fixtures and visual smoke pass.

## Wave 5 — object/world vertical slice

Object placement, object hierarchy, multi-selection, transforms, snapping, reset rotation/height, copy/paste payloads, object filtering and scene switching. Include NPC/mob/effect/regen/environment integration where present.

Gate: object transforms roundtrip and selection does not stale/crash.

## Wave 6 — renderer boundary

Separate legacy rendering calls from editor view logic. Establish render backend interface. Keep DX9 compatibility. Add modern shader preview as optional backend/feature flag.

Gate: map can be opened/saved with either preview path enabled/disabled.

## Wave 7 — picking/gizmos/camera

Raycast/bounds picking, box/lasso where useful, hierarchy sync, gizmos, grid/snap, WASD/arrow movement, perspective control, compass, minimap overlays and viewport diagnostics.

Gate: interaction regression matrix.

## Wave 8 — NewSchool shell

Replace legacy UI framing with professional dockable layout. Implement top command area, left tool rail, right Outliner/Inspector, bottom context area, minimap/status overlays and workspace presets.

Gate: all controls functional, DPI/resolution matrix green.

## Wave 9 — asset browser and pack workflow

Browse packed and loose assets, textures, property data, effects, models and environments. Explicitly distinguish unavailable assets from empty selections. Add deterministic cache invalidation and reload.

Gate: pack/Index and file-based workflows both verified where the target client supports them.

## Wave 10 — ReMIX behavior parity program

Implement public behavior targets: undo/redo; auto-backup; map export; direct pack loading; WASD navigation; server_attr generation; water tools; deterministic IDs; preload strategy; Python scripting boundary; GR2 animation toggle; object hierarchy; intersection picking; minimap/MAI controls; reload textures; diagnostics.

Gate: feature matrix in `docs/COMPATIBILITY_MATRIX.md` has evidence per feature.

## Wave 11 — scripting/API

Expose a stable scripting API for map queries, terrain operations, attributes, water cleanup, batch object placement, logging and export helpers. Keep scripting optional.

Gate: scripts cannot corrupt editor state or bypass save transactions.

## Wave 12 — performance and resource lifetime

Profile and remove frame stalls, device/resource leaks, duplicate asset loads, unnecessary full-map work and debug-only slow paths. Add telemetry and a lightweight in-app performance panel.

Gate: agreed frame/load budgets and no new memory growth under repeated open/close.

## Wave 13 — hostile input / recovery

Malformed map, missing texture, missing property, missing model, corrupt image, broken environment, invalid transform, bad path, interrupted save, canceled operation and repeated scene switching.

Gate: no crash, no silent overwrite, useful error state.

## Wave 14 — release hardening

Clean build from scratch, package runtime dependencies, sample data sanity, version manifest, changelog, docs, crash/log path, deterministic export and reviewer sign-off.

Gate: `we-release` complete.

## Delegation strategy

Parallelize orthogonal analysis. Recommended Wave 0 batch: inventory + compatibility + build + QA + security. Recommended renderer/UI waves: renderer + UI + input + performance + QA. Never let two agents independently redesign the same serializer or domain model; the orchestrator owns reconciliation.

## Patch discipline

Prefer vertical slices under one coherent responsibility. After each slice: build, targeted test, review diff, run smoke test if possible, update wave log.
