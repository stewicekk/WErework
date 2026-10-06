# Target architecture

```text
                    +-----------------------------+
                    |        NewSchool UI         |
                    |  Dock / Tools / Inspector   |
                    +--------------+--------------+
                                   |
                         Editor Commands
                                   |
                    +--------------v--------------+
                    |      Editor Domain Model    |
                    | Map / Terrain / Object / FX |
                    | Env / Attr / Water / Regen  |
                    +-----+-------------+---------+
                          |             |
                +---------v--+      +---v----------+
                | Undo/Redo  |      | Validation   |
                +---------+--+      +---+----------+
                          |             |
                 +--------v-------------v--------+
                 | Compatibility Serialization  |
                 | map/area/property/etc.       |
                 +--------+-------------+--------+
                          |             |
              +-----------v--+      +--v-----------+
              | Legacy Adapters|      | Modern Assets |
              | Eter/Game/GR2 |      | cache/index   |
              +-------+-------+      +------+--------+
                      |                     |
              +-------v---------------------v-------+
              |          Renderer Boundary          |
              | DX9 compatibility | modern preview  |
              +-------------------------------------+
```

## Core principles

### Canonical model

The editor state is not the same thing as the renderer object graph and not the same thing as the serialized file layout. Keep these separate.

### Commands

Every user-visible mutation should be represented as a reversible command. Commands own validation and dirty-state updates.

### Serialization

Loaders populate the canonical model. Savers serialize from the canonical model. Unknown fields/records must be preserved or explicitly rejected; they may not disappear silently.

### Renderer

Rendering consumes read-only editor snapshots. Resource lifetimes are explicit. Device loss/recreation is handled at the renderer boundary.

### UI

UI reads state and dispatches commands. UI must not directly mutate serialized data or renderer internals.

### Threading

File loading, asset decoding and heavy offline generation may run on worker threads. All editor-state mutations that feed the viewport must cross a controlled main-thread boundary. Never access MFC/UI objects from worker threads unless the existing framework explicitly permits it and the ownership contract is documented.
