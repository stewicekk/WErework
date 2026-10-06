"""NewSchool editor core — canonical domain + compatibility adapters.

Strangler foundation around the legacy WorldEditor: game data lives in
the canonical model (:mod:`newschool.document`), file bytes are handled
by verified serializers (:mod:`newschool.mapfiles`, :mod:`newschool.binary`),
mutations flow through commands (:mod:`newschool.commands`) and every
write is transactional (:mod:`newschool.store`).

Standard library only — no compiler, MFC, DirectX or Granny required.
"""

from . import binary, chunks, commands, document, errors, mapfiles, paths, scripttext, store

__all__ = [
    "binary", "chunks", "commands", "document", "errors",
    "mapfiles", "paths", "scripttext", "store",
]

__version__ = "0.1.0"
