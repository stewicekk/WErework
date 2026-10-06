---
name: scripting
description: Specialized guidance for Scripting in the Metin2 WorldEditor rebuild.
---

# Scripting skill

Scripts can automate operations but must not become the editor's foundation. Keep a stable narrow native API, validate map readiness, expose batch helpers, log progress, cap dangerous operations and isolate Python runtime dependencies from the editor core. Heavy scripts need cancellation/progress or chunking.
