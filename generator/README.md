# Generator

Turns the PRC8 module workdirs (nasher source trees) into the `data/` index
files. Python 3 stdlib only; shells out to the `nwn` binary
(unified neverwinter.nim toolchain) for binary GFF→JSON and ERF unpacking,
with results cached under `generator/.cache/` (gitignored) keyed by
path+mtime+size.

## Pipeline

1. **Discover** modules under `prc_root` (exclusions in `config.json`), walking
   each workdir for `*.utc(.json)` / `*.uti(.json)` while skipping junk dirs
   (`_removed/`, `.nasher/`, `_notes/`). Multi-unit modules (per-chapter
   `src/module/<Unit>/` trees) merge naturally; records dedupe by
   `TemplateResRef`, later-wins in sorted-path order, collisions counted.
2. **Name resolution** per module:
   locstring embedded text wins, else strref via base `dialog.tlk`, else the
   module's custom TLK (`Mod_CustomTlk`), else the fallback chain
   (`prc8_consortium.tlk`). Unresolved strrefs are counted, never fatal.
3. **2DA labels** (Race/Class/BaseItem/Portrait/itemprops) resolve through a
   fixed shadow chain: base game tables → CEP3 → PRC8 trunk → prc8_cep3_merge
   hak, with the base-game key as last-resort fallback (see `twoda_sources`).
4. **Items**: `LocalizedName`/`DescIdentified` locstrings, `BaseItem` →
   `baseitems.2da` name, GP value = `Cost + AddCost`, and full
   `PropertiesList` decoding through `itempropdef.2da` + `iprp_*` tables into
   human-readable strings (`PropertiesDecoded`).
5. **Supplement**: if a workdir's own name-matching `.mod` embeds more
   blueprints than the loose sources (checked against the ERF listing), it is
   unpacked into the cache and merged. Foreign/probe `.mod`s in the workdir
   are ignored.
6. **PRC8 expansion**: `trunk/others/` (the prc8_misc.hak blueprint set) is
   indexed once as its own `kind: "expansion"` pseudo-module instead of being
   merged into all ~65 modules.

`selftest.py` asserts the lookup chain against known values (strrefs 5213/5999,
the merge-TLK dwarf description, 2DA row resolutions, `.tlk.json` loading) —
run it after touching any lib file.

## Known approximations (documented, deliberate)

- **Shared TLK pool**: the merge TLKs (`prc8_cep1_merge`, `prc8_pq31_merge`,
  the CEP2 merges) and the server-fresh `prc8_consortium`/`prc8_ancordia`
  live in `prc/_shared_tlk/` (fetched from the nwserver's `~/nwn/tlk`).
  `prc8_cep271_mrg` does not exist even on the server — `prc8_cep269_mrg` is
  symlinked as its stand-in (CEP 2.71 vs 2.69 merge, near-identical ranges).
  ~32 strrefs remain unresolved machine-wide, visible per module in
  `counts.unresolved_strrefs`.
- **2DA shadow order is global**, not per-module-hak-stack; a module whose hak
  order differs from the fixed chain can label an edge-case row differently
  than in-game.
- **HitPoints = MaxHitPoints** (UTC `HitPoints` is spawn-state, often 1).
- **GP value = Cost + AddCost** (UTI has no single gold-value field).
- Uppercase-extension GFFs (`.UTC`/`.UTI`, common in the PRC8 tree) are
  converted through a lowercased cache copy because `nwn gff` detects the
  format from the extension case-sensitively.
- Some nasher JSON dumps contain raw windows-1252 bytes; those are decoded as
  cp1252 with replacement.
- `name_overrides` in `config.json` fixes workdirs whose `module.ifo` carries
  a copy-pasted `Mod_Name` from an unrelated module (Aielund_PRC8's acts all
  claim "Nature Abhors a Vacuum").

## Config

All machine-local paths live in `config.json` (`prc_root`, `nwn_bin`,
`base_tlk`, the 2DA chain, TLK search paths, skip lists, rarity thresholds).
