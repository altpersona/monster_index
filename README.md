# Monster & Item Index

Indexes the creatures (`.utc`) and items (`.uti`) of the Neverwinter Nights 1
modules I host/maintain — the PRC8 conversion workspace — into per-module JSON
files browsable through a static viewer.

Two parts:

- **Content** — `data/<module>.json`, one file per module (plus the PRC8
  expansion's own blueprint set), with a `data/manifest.json` index. Generated
  by `generator/` from the module workdirs.
- **Presentation** — `index.html`, a no-build vanilla-JS viewer (faceted
  filters, rarity-tiered cards, portraits with text fallback, monster and item
  tabs). Works over any static file server.

## Serve

    cd monster_index
    python3 -m http.server 8000
    # open http://localhost:8000/   (#items deep-links to the items tab)

Opening index.html directly off disk (file://) does NOT work — the viewer
fetch()es data/, which browsers block for local files.

## Deploy (production)

    ./deploy.sh        # rsyncs index.html + data/ to the nwserver box
                       # → https://raptio.us/monster_index/

Deploy path: raptio.us edge (openresty) → nwserver Apache default vhost →
`/var/www/html/monster_index/`. Drop-in portraits on the prod side are
preserved by the deploy (excluded from --delete).

## Regenerate

    python3 generator/generate.py --list      # enumerate module workdirs
    python3 generator/generate.py --only UW2_PRC8
    python3 generator/generate.py --all       # all modules + PRC8 expansion + manifest

Paths (module workspace, base game data, the `nwn` toolchain binary) are
configured in `generator/config.json` — see `generator/README.md` for the
pipeline, the data schemas, and the known approximations.

## Data shape

Each `data/<module>.json` wraps `{schema, module, id, kind, generated, counts,
monsters[], items[]}`. Counts include collision/unresolved/unmapped tallies so
quality issues are visible per module, not silent. Portraits are not bundled;
drop PNGs into `data/portraits/` named after the portrait resref (lowercase,
`po_` prefix and trailing `_` stripped) to light them up.

`legacy/` holds the original 2024 Vue attempt and its two data files.
