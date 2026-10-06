# ADR-001 — strangler core in stdlib-only Python mirroring target C++ boundaries

## Context

Wave 0 proved the legacy baseline unbuildable here (no C++ toolchain, no
`.sln`, 12/14 ClientSource libs absent from the checkout) while the audit
verified exact serializer behavior from the reference save side. The program
needs build→test→evidence on every slice from day one; waiting for MSVC +
full ClientSource would stall all waves.

## Decision

Implement the strangler foundation (`src/newschool/`) as a dependency-free
Python core whose module boundaries map 1:1 to the future C++ layers
(domain / scripttext / mapfiles / binary / paths / store / document /
commands). Legacy tree untouched. Every format constant cites a
`file:line`; anything unverifiable (GameLib dimensions, PrintfTabs bytes,
loader tolerance) is a parameter or a documented policy — never an
assumption baked into behavior.

## Alternatives considered

- C++ core now: impossible (no compiler); rejected.
- Full legacy build first: blocked on toolchain + absent libs; rejected as
  wave-1 gate, kept as parallel track once environment allows.
- Python with numpy/click/pytest deps: rejected (stdlib-only keeps the
  core reproducible anywhere, matching the deterministic-build goal).

## Compatibility impact

Writers reproduce verified legacy bytes (Setting/MapProperty/AreaProperty/
AreaData/Ambience/attr.atr#2634/water.wtr#5426/chunk `%06u`/portal dedup/
regen intended layout as explicit NEW capability). Unknown keys/lines/groups
preserved. No legacy file is modified by this wave.

## Performance impact

None on legacy (untouched). Core suite runs 94 tests in ~1.1 s; no
performance claim made (Gate H baselines belong to later waves).

## Test evidence

`scripts/test-core.ps1`: 94/94 OK, incl. golden-byte, roundtrip,
transaction/backup, hostile-input and regression tests.

## Rollback plan

Delete `src/`, `tests/`, `scripts/test-core.ps1`, `docs/waves/WAVE_01*` —
legacy repos contain zero tracked changes, so removal is total.
