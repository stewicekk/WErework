---
name: metin2-compatibility
description: Specialized guidance for Metin2 Compatibility in the Metin2 WorldEditor rebuild.
---

# Metin2 compatibility skill

Protect legacy semantics. Search source for exact loaders/savers before redesigning. Identify coordinate units, terrain chunk dimensions, texture index conventions, attribute bit meanings, object IDs, map type, environment names, regen serialization, minimap/MAI generation and collision/MDATR relationships. For every change, define legacy input -> canonical model -> legacy output and a roundtrip invariant. Prefer byte-preserving or semantic-preserving storage for data the editor does not understand.
