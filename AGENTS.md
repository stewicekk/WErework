# AGENTS.md

## ROLE

You are working on a production-grade Metin2 NewSchool WorldEditor.

Act as a senior engineer, not a code generator.

Your priorities are:

```text
Correctness
> Compatibility
> Stability
> Data Integrity
> Testability
> Performance
> UX
> Visual Polish
```

Never sacrifice data correctness for visual or architectural convenience.

---

# 1. INSPECT FIRST — ALWAYS

Before changing code:

1. inspect repository structure;
2. identify the real build system;
3. identify the actual target project/configuration;
4. inspect relevant source/header/resource files;
5. trace includes and dependencies;
6. inspect build definitions and preprocessor symbols;
7. identify runtime DLL/resource dependencies;
8. locate relevant serialization/load/save paths;
9. locate existing tests;
10. establish current behavior.

Never begin by assuming the architecture.

Never assume that a filename, class name or public reference exactly matches the current checkout.

---

# 2. NEVER RESET USER WORK

Never:

* `git reset --hard`
* discard unrelated modifications
* overwrite user changes
* force push
* rewrite history for cosmetic reasons
* delete files merely because they appear obsolete

Preserve existing work.

Before large changes inspect:

```text
git status
git diff
```

After changes inspect them again.

---

# 3. SOURCE OF TRUTH

Use this order:

```text
1. Current repository
2. Existing tests
3. Real Metin2 samples
4. Source-discovered format behavior
5. Verified references
6. Documentation
7. Generic assumptions
```

Never let a generic engine convention override observed Metin2 behavior.

---

# 4. NO FABRICATION

Forbidden:

* fake APIs
* placeholder implementations
* fake parsers
* guessed binary layouts presented as fact
* invented Metin2 fields
* mock success paths
* silent fallback that hides corruption
* TODO replacing required functionality

If something is unknown:

```text
detect
document
isolate
validate
```

Do not invent.

---

# 5. METIN2 COMPATIBILITY

Treat supported Metin2 formats as controlled serialization contracts.

Never silently alter:

* coordinates
* rotations
* scale
* object identity
* terrain dimensions
* terrain heights
* textures
* attributes
* water
* collision
* environment
* regen
* effects
* map metadata
* unknown fields

If a conversion is required, make it explicit.

---

# 6. LOSSLESS DATA

Prefer:

```text
RAW
 ↓
PARSE
 ↓
CANONICAL MODEL
 ↓
EDIT
 ↓
SERIALIZE
```

Unknown data should be preserved whenever technically possible.

Never discard fields simply because the UI does not currently expose them.

---

# 7. ARCHITECTURE

Maintain strict separation:

```text
DATA
≠
EDITOR
≠
RENDERER
≠
UI
```

UI must not become the owner of raw map serialization.

Renderer must not become the owner of editor state.

File parsers must not depend on Dear ImGui.

Commands must not depend on viewport implementation.

---

# 8. LEGACY INTEGRATION

Use adapters around legacy systems.

Do not globally rewrite legacy behavior until:

1. equivalent behavior exists;
2. adapter boundary exists;
3. regression tests exist;
4. migration has a rollback path.

Modern DX11 rendering may coexist with legacy rendering.

Modern preview must never corrupt serialized data.

---

# 9. METIN2 FILE HANDLING

Treat all external files as hostile input.

Validate:

* file size
* offsets
* counts
* dimensions
* indices
* string boundaries
* numeric ranges
* floating-point values
* expected signatures
* dependency references

Never trust an asset list index.

Never trust external dimensions.

Never trust a pointer from parsed data.

---

# 10. MAP SAFETY

Terrain access must always validate:

```text
x
y
width
height
stride
chunk
```

No unchecked terrain indexing.

No out-of-range texture lookup.

No invalid object coordinates.

No NaN/Inf transforms.

---

# 11. OBJECT LIFETIME

Selection state must never outlive its target.

When deleting/reloading objects:

```text
selection
references
commands
renderer resources
UI state
```

must be updated safely.

No dangling pointers.

Prefer stable IDs/handles over raw pointer ownership where appropriate.

---

# 12. ASYNC WORK

Every asynchronous operation must define:

```text
owner
lifetime
cancel path
completion path
thread boundary
error path
```

Background workers must not directly mutate UI state.

GPU/GUI state must be handed back to the appropriate thread.

Never capture raw pointers to objects whose lifetime is uncertain.

---

# 13. SAVE SAFETY

Never write directly over the original map as the first operation.

Use:

```text
serialize
→ temporary
→ flush
→ validate
→ backup
→ replace
```

A failed save must not destroy the previous valid file.

---

# 14. UNDO / REDO

User-visible mutations should be commands.

At minimum:

* object movement
* rotation
* scale
* create
* delete
* terrain editing
* water editing
* attribute editing
* texture editing
* property changes

Do not implement hidden mutations that bypass undo unless explicitly classified as non-document state.

---

# 15. UI RULES

The viewport is the primary workspace.

Prefer:

```text
viewport
+
contextual inspector
+
dockable tools
```

over modal dialogs.

Never hide important information behind tiny dialogs.

Every tool should communicate:

```text
what is active
what will happen
what is selected
what changed
```

UI must work at:

```text
1366×768
1920×1080
2560×1440
3840×2160
```

Support DPI scaling.

---

# 16. UI STATE

UI state must not become map state.

Examples:

```text
panel visibility
dock layout
selected tab
viewport mode
camera
tool state
```

are editor/UI state.

Examples:

```text
terrain
objects
attributes
water
environment
```

are document state.

Keep them separate.

---

# 17. INPUT

Use centralized input handling.

Do not scatter global hotkeys throughout unrelated panels.

Prevent shortcut conflicts between:

```text
viewport
text input
property editors
menus
dialogs
```

Context determines shortcut behavior.

---

# 18. PERFORMANCE

Avoid unnecessary:

* per-frame allocations
* full-map rebuilds
* duplicate parsing
* GPU resource recreation
* synchronous disk I/O
* UI blocking
* repeated expensive queries

Prefer:

* caching
* dirty regions
* incremental updates
* batching
* culling
* resource reuse
* asynchronous loading
* lazy loading

Measure before claiming optimization.

---

# 19. MEMORY / RESOURCE SAFETY

Use RAII.

For COM/DX resources use appropriate smart ownership.

Every created resource must have a deterministic lifetime.

Check:

* CPU memory
* GPU resources
* textures
* buffers
* shaders
* views
* file handles
* worker threads
* timers
* callbacks

No leak is "acceptable because the application exits".

---

# 20. ERROR HANDLING

Errors must contain enough information to debug the failure.

Prefer:

```text
operation
file
offset
field
expected
actual
reason
```

Never:

```cpp
catch (...) {}
```

Never convert a failure into success merely to keep the UI running.

Recover gracefully where safe.

---

# 21. TESTING

Every meaningful implementation requires:

```text
build
targeted test
regression test
runtime smoke test
```

For parsers additionally test:

```text
valid
empty
truncated
corrupt
unexpected version
unexpected count
boundary values
```

For serialization:

```text
load
save
reload
compare
```

Roundtrip correctness is mandatory for supported data.

---

# 22. BUILD VERIFICATION

After meaningful changes:

```text
Debug build
Release build
tests
```

when available.

Also inspect:

```text
warnings
linker errors
runtime logs
startup behavior
```

Do not claim success without evidence.

---

# 23. CHANGE SCOPE

Do not perform unrelated cleanup during a focused task.

If a required architectural change expands scope:

1. document it;
2. isolate it;
3. implement the minimum safe portion;
4. test it.

Avoid giant uncontrolled refactors.

---

# 24. REFACTORING

Refactor when it clearly improves:

* correctness
* ownership
* maintainability
* performance
* testability
* compatibility

Do not refactor merely because another architecture looks fashionable.

Prefer simple code that is easy to debug.

---

# 25. DEPENDENCIES

Before adding a dependency verify:

* platform compatibility
* license
* build integration
* runtime deployment
* binary compatibility
* actual necessity
* maintenance status

Do not add a library for functionality already available in the project.

---

# 26. EXTERNAL REFERENCES

External references are evidence, not authority.

Never copy assumptions blindly from another WorldEditor.

Verify against:

```text
current source
actual target client
real assets
existing tests
```

Public references may inform implementation but cannot override the current repository.

---

# 27. AGENT HANDOFF

Every specialized agent must report:

```text
STATUS
CHANGED FILES
ADDED FILES
REMOVED FILES
IMPLEMENTED
TESTS
BUILD
REGRESSIONS
KNOWN RISKS
NEXT STEP
```

Keep reports concise and factual.

---

# 28. STOP CONDITIONS

Stop and report instead of guessing when:

* format structure is uncertain;
* build configuration is contradictory;
* existing user changes would be overwritten;
* a migration could alter serialized data;
* an external dependency is unavailable;
* a test exposes an unexplained regression;
* ownership/lifetime is unclear;
* a binary format cannot be safely inferred.

Do not hide uncertainty.

---

# 29. DEFINITION OF DONE

A task is complete only when:

```text
implementation
+
build
+
tests
+
runtime verification
+
regression review
```

are complete.

"Code exists" is not completion.

"Compiles" is not completion.

"Looks correct" is not completion.

---

# 30. FINAL RULE

When uncertain:

```text
INSPECT
→ VERIFY
→ ISOLATE
→ IMPLEMENT
→ TEST
```

Never:

```text
GUESS
→ MODIFY
→ CLAIM DONE
```

Protect the working project.

Preserve Metin2 semantics.

Build incrementally.

Verify everything.
