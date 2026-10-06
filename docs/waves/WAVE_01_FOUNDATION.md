# Wave 01 — strangler foundation core

Date: 2026-10-06

## Objective

Wave 0 forensic audit (16/16 topics) + buildable canonical core (Waves 1–4
foundation fast-tracked): domain model, byte-exact serializers, transactional
store, command/undo, path resolution — stdlib-only, tested, with evidence.

## Agents consulted

- compatibility (evidence scan): chunk/file/path/attribute entry points + UNVERIFIED list
- qa (stability sweep): 40 file:line findings (crash/data-loss/hang/corruption)
- reviewer (read-only): 25 findings on the new core, verdict REJECT → all
  CRITICAL/HIGH + most MEDIUM fixed in-wave, re-tested to green

## Changed files

New core (`src/newschool/`): `__init__.py`, `errors.py`, `chunks.py`,
`scripttext.py`, `mapfiles.py`, `binary.py`, `paths.py`, `store.py`,
`document.py`, `commands.py`.
Tests (`tests/`): 9 files, 94 tests. Runner: `scripts/test-core.ps1`.
Audit (`WorldEditor-Renewal/ClientSource/WorldEditor/docs/audit/`):
`INVENTORY/ARCHITECTURE/FEATURES/DATA_FLOW/FORMATS/COMPATIBILITY/RENDERING.md`
+ `AUDIT_CONSOLIDATED.md` (UI/INPUT/SERIALIZATION/TESTS/BUILD/PERF/RISKS/TECH_DEBT/MIGRATION).
Legacy tracked files: **zero modifications** (`git status` clean except untracked audit docs).

## Architecture decisions

See `docs/waves/ADR-001-strangler-core.md`. Key points: canonical model owns
game data only; serializers reproduce verified legacy bytes; unknown
data preserved, never dropped; transactional temp→validate→replace+backup;
commands own undo state (no borrowed refs); Python core mirrors the target
C++ boundaries (no compiler in this environment — legacy build BLOCKED).

## Build evidence

- Legacy baseline build: BLOCKED (no cl/msbuild/ninja/gcc/clang; no .sln;
  12/14 ClientSource libs absent). Evidence: `docs/baseline/20261006-032207/`.
- New core: `py_compile` clean on all 19 files; `scripts/test-core.ps1` green.

## Test evidence

`python -m unittest discover -s tests`: **94 tests, OK in ~1.1 s**.
Coverage: chunk scheme, script-text preservation, golden-byte writers
(Setting/MapProperty/AreaProperty/AreaData/Ambience/regen/AtlasInfo),
attr/water magic + truncation, pack Index pairs, loose-first precedence,
path-escape rejection, atomic write + backup + failure-keeps-original,
document save/load roundtrip, env lifecycle, snapshot recover, undo/redo,
grouping, composite rollback, stack-failure retention.

## Runtime evidence

N/A (headless core; no viewport/renderer in this wave — by design).

## Metrics

- 94/94 tests pass (started 78, +16 from reviewer follow-ups)
- 0 legacy tracked files touched
- ~2 800 lines new code+tests, stdlib-only, no dependencies

## Regressions checked

- No-op save byte-stability: deterministic writers (Setting/AreaData/…);
  environment whitespace policy documented (indent bytes excepted).
- Failed save/load leaves previous content + document identity intact
  (R4 regression tests); dirty flag untouched by failed save.

## Remaining risks

- R1-class whole-tree atomicity is per-file (staging/rollback future work).
- Load-side struct sizes (GameLib constants) still UNVERIFIED — counts are
  parameters, never assumed.
- PrintfTabs indent bytes assumed tabs for new env files (documented).
- No BOM tolerance; UTF-8 strict fails loudly (documented, acceptable).
- Reviewer LOW leftovers: backup-replace failure simulation, MapSize 1..64
  bound review, sky-face emptiness policy.

## Reviewer findings

First pass REJECT (25 findings) → all CRITICAL/HIGH fixed, most MEDIUM
fixed (env unknown-group blocks, resolver MoveObjectCommand, composite
rollback, copy-backup, CRLF normalization, strict arity/bool/portal-0,
path drive-letter bypass, doc corrections). Re-test: 94/94 green.
Second full re-review deferred to Wave 02 gate (reviewer already consumed
this wave's findings list as checklist).

## Status

PASS (foundation) / NEEDS FOLLOW-UP (risks above → Wave 02)
