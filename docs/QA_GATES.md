# QA gates

## Gate A — clean build

Build every supported configuration. Record compiler version, configuration, warnings, target architecture and produced binaries.

## Gate B — launch

Start the editor with missing optional assets, missing config, empty map directory and a valid sample map. The application must fail gracefully and explain what it needs.

## Gate C — roundtrip

Open known maps, perform a no-op save, reload, then compare semantic model snapshots. For formats where byte preservation is expected, compare bytes as well.

## Gate D — edit transactions

Test terrain height, texture paint, attributes, water, object translate/rotate/scale, selection, multi-selection, copy/paste, undo/redo, save and reload.

## Gate E — missing assets

Delete/rename texture, property, SPT, GR2, environment and effect inputs. Verify the editor presents a missing state and does not keep stale names from the previous asset.

## Gate F — stress

Repeatedly open/close maps and scenes, reload textures, switch workspaces, run save/export, create/delete many objects, and leave the editor running long enough to detect resource growth.

## Gate G — UI

Validate 1366×768, 1920×1080, 2560×1440 and 3840×2160; 100/125/150/200% DPI; mouse/keyboard focus; docking; workspace persistence; disabled states; tooltips; keyboard shortcuts; text input; viewport resize.

## Gate H — performance

Collect frame time and operation durations for startup, map load, terrain crossing, brush stroke, multi-select transform, minimap/shadow generation, save and export. Compare against baseline before claiming a performance improvement.

## Gate I — malformed input

Fuzz text and binary boundaries that are safe to test: empty records, invalid indices, truncated files, bad dimensions, duplicate IDs, NaN/Inf transforms, unsupported versions and paths containing `..`.

## Gate J — release

Clean checkout build, package runtime files, generate manifest/checksums, verify sample map, verify logs/crash path and perform final read-only code review.
