---
name: performance
description: Specialized guidance for Performance in the Metin2 WorldEditor rebuild.
---

# Performance skill

Measure, do not guess. Track startup, map load, first frame, terrain crossing, brush latency, multi-select transform, minimap/shadow build, save/export and steady-state frame time. Avoid whole-map work on mouse move or per-frame UI. Cache by stable asset identity and invalidate explicitly.
