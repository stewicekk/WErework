---
name: qa-stability
description: Specialized guidance for Qa Stability in the Metin2 WorldEditor rebuild.
---

# QA stability skill

Every bug fix requires a regression test or reproducible verification procedure. Prefer golden maps and deterministic fixtures. Test normal, empty, malformed, missing-asset and huge-map cases. Exercise save failure, reload, undo/redo, cancel, repeated open/close and device/resource recreation.
