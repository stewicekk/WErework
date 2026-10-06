# Migration policy

## What may be rewritten

UI, command routing, domain-model internals, renderer abstraction, cache architecture, build organization, diagnostics, asset browser, configuration system and editor-only rendering may be significantly modernized.

## What must be proven before rewriting

Anything that serializes map data; coordinate conversion; object identity; attribute bits; collision/height data; environment and regen files; packed asset lookup; Granny/GR2 contracts; SpeedTree assumptions; minimap/MAI rules; ClientSource macro boundaries.

## Strangler sequence

1. Wrap legacy subsystem.
2. Add characterization tests.
3. Add canonical representation.
4. Route one use case through canonical path.
5. Compare legacy and new output.
6. Flip default only after parity.
7. Remove dead legacy code only after a later release gate confirms it is unused.

## Never do

- blanket search/replace across C++ source;
- replace a serializer before fixtures exist;
- migrate all rendering and UI in one wave;
- introduce a giant god-class `EditorState` with every field;
- keep two sources of truth for selection/transform;
- swallow exceptions/load errors and show stale UI;
- silently normalize unknown data.
