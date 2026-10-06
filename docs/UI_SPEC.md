# NewSchool UI specification

## Design objective

The application should look like a modern professional DCC/editor tool rather than a reskinned legacy MFC utility. The viewport is the product; the UI organizes editing around it.

## Window

Default adaptive layout targets 1920×1080 but must remain functional at 1366×768, 1600×900, 2560×1440 and 3840×2160. Use DPI-aware metrics, scalable fonts/icons and persisted workspace layouts. Avoid pixel-fixed controls that become unreadable or collide at non-100% scaling.

## Layout

Top: menu/command strip + workspace selector + current map identity + dirty/save state + quick undo/redo + play/test + search/command palette.

Left: compact vertical mode/tool rail. Modes: Select, Move, Rotate, Scale, Terrain, Texture, Attribute, Water, Object, Effect, Spawn/Regen, Environment, Measure, Inspect. Expand into context tool options rather than occupying the whole screen.

Center: main viewport. Supports perspective, orthographic/top mode, wireframe, solid, textured/material preview, collision/attribute/height debug overlays, grid, compass, axis/gizmo, brush cursor, selection outline, object labels and performance overlay.

Right: tabbed Outliner + Inspector + Asset Properties. Outliner has hierarchy, search, type filters, visibility/lock/isolate and multi-select. Inspector uses category grouping, inline numeric editing, reset buttons, relative/local/world transform toggles and validation feedback.

Bottom: contextual console/output/status/timeline. Keep it collapsible. Show operation progress, warnings and errors without modal dialog spam. Map/terrain operation progress must support cancellation.

Floating: minimap, navigator, command palette, asset picker and diagnostics can float/dock.

## Interaction

Left click selects; Ctrl/Shift modify selection according to mode; click-drag box select; right mouse camera navigation; middle mouse pan; wheel zoom; standard W/E/R gizmo convention; shortcuts never depend on hidden focus except text-entry fields. `Esc` cancels current tool/operation. `Ctrl+S` is save. `Ctrl+Z` / `Ctrl+Y` are undo/redo. `F5` may remain the scripting hook if scripting is enabled. `Insert`/`F6` behavior may remain the map snapshot/shadow/minimap command if legacy compatibility requires it.

## Visual language

Dark neutral foundation, restrained high-contrast accent, clear hover/pressed/disabled states, subtle separators, compact spacing, rounded corners only where it improves grouping. Use a single icon family with consistent stroke/weight. Avoid emoji or platform-dependent glyphs for core controls. Tooltips should contain action + shortcut + destructive warning where relevant.

## UX correctness

A button that only changes a visual state without affecting the actual editor is a bug. A panel that displays stale data after a failed load is a bug. A selection highlight that differs from the true command target is a bug. A layout that cannot be restored is a bug.

## Modern extras worth implementing

- command palette;
- searchable menu/actions;
- recent maps + pinned workspaces;
- map health badge;
- asset-missing filter;
- selected-object count and bounds;
- operation history drawer;
- non-blocking notifications;
- viewport screenshot/export;
- lock/isolate/hide selected;
- transform copy/paste as textual payload;
- per-workspace shortcut presets;
- performance HUD;
- diagnostic overlays for terrain/attribute/collision/MDATR/texture layers.
