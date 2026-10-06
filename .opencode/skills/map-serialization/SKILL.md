# Map Serialization Skill

Use for load/save, import/export, autosave and recovery.

Transaction

temporary file -> flush/close -> parse/validate -> backup existing -> replace -> reload verify

Never destroy the last valid document before the new representation is validated.
