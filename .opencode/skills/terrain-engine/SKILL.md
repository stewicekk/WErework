# Terrain Engine Skill

Use for terrain, water, attributes, brushes and spatial editing.

Rules
centralize coordinate conversion
clamp all editable regions
keep height/attribute/texture updates consistent
update only dirty regions when possible
keep spatial indexing deterministic
route user mutations through commands
provide undo/redo
test borders, empty maps and extreme values
