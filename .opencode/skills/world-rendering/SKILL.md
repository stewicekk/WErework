---
name: world-rendering
description: Specialized guidance for World Rendering in the Metin2 WorldEditor rebuild.
---

# World rendering skill

Use renderer abstraction. Legacy backend preserves compatibility. Modern backend owns shaders, material preview, depth/normal diagnostics, outline, grid, gizmos, editor lighting and dynamic shadow preview. GPU resources are explicit RAII-owned objects. Never let renderer state mutate serialized map state.
