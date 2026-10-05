#!/usr/bin/env python3
"""Generate monster/item index data files from the prc/ module workdirs.

Usage (from repo root):
  python3 generator/generate.py --list
  python3 generator/generate.py --only UW2_PRC8
  python3 generator/generate.py --all            # all modules + PRC8 expansion + manifest
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib.tlk import Tlk                                    # noqa: E402
from lib.twoda import TwoDAChain                           # noqa: E402
from lib.erf import ErfUtil                                # noqa: E402
from lib.gffread import load_gff, val                      # noqa: E402
from lib.modules import (discover, find_tlk, tlk_search_paths, slugify)  # noqa: E402
from lib.records import Counters, ModuleContext, monster_from_utc, item_from_uti  # noqa: E402

REPO = os.path.dirname(HERE)


def resolve_source_paths(config, src):
    s = dict(src)
    if s.get('prc_root_relative'):
        s['path'] = os.path.join(os.path.dirname(config['prc_root'].rstrip('/')), s['path'])
    elif s.get('type') == 'dir' and not os.path.isabs(s['path']):
        s['path'] = os.path.join(config['prc_root'], s['path'])
    return s


class Generator:
    def __init__(self, config):
        self.cfg = config
        self.erf = ErfUtil(config['nwn_bin'], os.path.join(REPO, config['cache_dir']))
        self.base_tlk = Tlk(config['base_tlk'])
        self.fallback_tlks = []
        for name in config['tlk_fallback_chain']:
            p = find_tlk(name, tlk_search_paths(config, ''))
            if p:
                self.fallback_tlks.append(Tlk(p))
        self.chain = TwoDAChain([resolve_source_paths(config, s) for s in config['twoda_sources']],
                                self.erf, self.erf.cache_dir)
        self.data_dir = os.path.join(REPO, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, 'portraits'), exist_ok=True)

    # ---- per-module context ----

    def module_info(self, spec):
        """(display_name, custom_tlk_name, custom_tlk_path)"""
        from lib.gffread import locstr_field
        from lib.locstr import locstr_text
        name = getattr(spec, 'name', None) or spec.dir.rsplit(os.sep, 1)[-1]
        custom_tlk_name = None
        if spec.ifo_paths:
            try:
                ifo = load_gff(spec.ifo_paths[0], self.erf)
            except Exception:
                ifo = {}
            if ifo:
                nm, _ = locstr_text(locstr_field(ifo, 'Mod_Name'), self.base_tlk)
                if nm:
                    name = nm.strip()
                custom_tlk_name = val(ifo, 'Mod_CustomTlk') or None
        # explicit overrides beat the ifo: some converted modules carry a
        # copy-pasted Mod_Name from an unrelated module (e.g. Aielund_PRC8's
        # acts all say "Nature Abhors a Vacuum")
        overrides = self.cfg.get('name_overrides', {})
        dirname = spec.dir.rsplit(os.sep, 1)[-1]
        if dirname in overrides:
            name = overrides[dirname]
        custom_tlk_path = find_tlk(custom_tlk_name, tlk_search_paths(self.cfg, spec.dir)) \
            if custom_tlk_name else None
        return name, custom_tlk_name, custom_tlk_path

    def make_context(self, spec):
        counters = Counters()
        _name, tlk_name, tlk_path = self.module_info(spec)
        custom = Tlk(tlk_path) if tlk_path else None
        ctx = ModuleContext(self.base_tlk, custom, self.fallback_tlks, self.chain, counters)
        return ctx, tlk_name, tlk_path is not None

    # ---- record collection ----

    def collect(self, spec, kinds=('utc', 'uti'), extra_files=None):
        """Map blueprint files to records in one pass; dedupe by resref, later-wins."""
        ctx, tlk_name, tlk_found = self.make_context(spec)
        counters = ctx.counters
        out = {k: {} for k in kinds}
        exts = {'utc': ('.utc', '.utc.json'), 'uti': ('.uti', '.uti.json')}

        for path in list(spec.files) + list(extra_files or []):
            low = path.lower()
            kind = next((k for k in kinds if low.endswith(exts[k])), None)
            if kind is None:
                continue
            try:
                gff = load_gff(path, self.erf)
            except Exception as e:
                counters.bump('read_errors')
                counters.note('read_errors', f'{os.path.basename(path)}: {e}')
                continue
            stem = os.path.basename(low).replace('.json', '').rsplit('.', 1)[0]
            if kind == 'utc':
                rec = monster_from_utc(gff, ctx, stem)
            else:
                rec = item_from_uti(gff, ctx, stem,
                                    truncate=self.cfg.get('description_truncate', 280))
            if rec['ResRef'] in out[kind]:
                counters.bump('collisions')
                counters.note('collisions', rec['ResRef'])
            out[kind][rec['ResRef']] = rec

        return out, counters, tlk_name, tlk_found

    # ---- module file emit ----

    def emit_module(self, spec, kinds=('utc', 'uti'), used_slugs=None):
        extra, mod_name = self.supplement_files(spec)
        out, counters, tlk_name, tlk_found = self.collect(spec, kinds, extra)
        name, _, _ = self.module_info(spec)
        slug = slugify(name)
        if used_slugs is not None:
            if slug in used_slugs:
                suffix = 2
                while f'{slug}-{suffix}' in used_slugs:
                    suffix += 1
                slug = f'{slug}-{suffix}'
            used_slugs.add(slug)
        monsters = [out['utc'][k] for k in sorted(out['utc'])] if 'utc' in out else []
        items = [out['uti'][k] for k in sorted(out['uti'])] if 'uti' in out else []
        counts = counters.report()
        counts.update({
            'monsters': len(monsters),
            'items': len(items),
            'collisions': collision_summary(counters),
            'custom_tlk': tlk_name,
            'custom_tlk_found': tlk_found,
        })
        notes = []
        if mod_name:
            notes.append(f'supplemented from {mod_name}')
        if notes:
            counts['notes'] = notes
        doc = {
            'schema': 2,
            'module': name,
            'id': slug,
            'kind': 'module',
            'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'counts': counts,
            'monsters': monsters,
            'items': items,
        }
        path = os.path.join(self.data_dir, slug + '.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(doc, fh, ensure_ascii=False, separators=(',', ':'))
        return path, doc


    # ---- .mod supplement ----

    def supplement_files(self, spec):
        """If the workdir's own .mod (name-matched — several workdirs carry
        copies of other modules' mods) embeds more blueprints than the loose
        sources have, unpack it and use its utc/uti as extra sources."""
        mods = []
        for root, dirs, files in os.walk(spec.dir):
            dirs[:] = [d for d in dirs if d not in set(self.cfg['skip_dirs'])]
            for f in files:
                if f.lower().endswith('.mod'):
                    mods.append(os.path.join(root, f))
        if not mods:
            return [], None

        def norm(s):
            return ''.join(ch for ch in s.lower() if ch.isalnum())

        want = norm(spec.dir.rsplit(os.sep, 1)[-1])
        matching = [m for m in mods
                    if want in norm(os.path.basename(m)) or
                    norm(os.path.basename(m)[:-4]) in want]
        if not matching:
            return [], None          # only foreign/probe mods present
        matching.sort(key=lambda p: os.path.getsize(p), reverse=True)
        mod = matching[0]

        def count_type(ext):
            return sum(1 for f in spec.files if f.lower().endswith(ext))

        listing = self.erf._run(['erf', '-f', mod, '-t'], check=False).stdout.lower()
        mod_utc = listing.count('.utc')
        mod_uti = listing.count('.uti')
        need = mod_utc > count_type(('.utc', '.utc.json')) or \
               mod_uti > count_type(('.uti', '.uti.json'))
        if not need:
            return [], None

        tag = os.path.basename(mod)
        dest = os.path.join(self.erf.cache_dir, 'modsup',
                            tag.replace('/', '_') + f'_{os.path.getmtime(mod):.0f}')
        if not os.path.isdir(dest) or not os.listdir(dest):
            self.erf.unpack_erf(mod, dest)
        extra = []
        for root, dirs, files in os.walk(dest):
            for f in files:
                if f.lower().endswith(('.utc', '.uti')):
                    extra.append(os.path.join(root, f))
        return sorted(extra), os.path.basename(mod)


def collision_summary(counters):
    return {'count': counters.data.get('collisions', 0),
            'samples': counters.data.get('collisions_samples', [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', help='module workdir name (e.g. UW2_PRC8)')
    ap.add_argument('--all', action='store_true', help='all modules + PRC8 expansion + manifest')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, 'config.json')))
    gen = Generator(cfg)
    specs = discover(cfg)

    if args.list:
        for s in specs:
            n = len(s.utc_files) + len(s.uti_files)
            print(f'{s.dir.rsplit(os.sep,1)[-1]:40} {n:6d} blueprints')
        return

    if args.only:
        matches = [s for s in specs if args.only.lower() in s.dir.lower()]
        if not matches:
            sys.exit(f'no module matches {args.only!r}')
        for spec in matches:
            path, doc = gen.emit_module(spec)
            c = doc['counts']
            print(f'{doc["module"]}: {c["monsters"]} monsters, {c["items"]} items '
                  f'-> {os.path.relpath(path, REPO)}')
            print(f'  custom_tlk={c["custom_tlk"]} found={c["custom_tlk_found"]} '
                  f'unresolved_strrefs={c.get("unresolved_strrefs", 0)} '
                  f'unmapped_races={c.get("unmapped_races", 0)} '
                  f'unmapped_classes={c.get("unmapped_classes", 0)} '
                  f'collisions={c["collisions"]["count"]}')
        return

    if args.all:
        used_slugs = set()
        manifest_modules = []
        skipped = []
        for spec in specs:
            try:
                path, doc = gen.emit_module(spec, used_slugs=used_slugs)
            except Exception as e:
                skipped.append((spec.dir.rsplit(os.sep, 1)[-1], str(e)[:120]))
                continue
            c = doc['counts']
            if c['monsters'] == 0 and c['items'] == 0:
                os.remove(path)
                skipped.append((doc['module'], 'no blueprints'))
                continue
            manifest_modules.append({
                'id': doc['id'], 'name': doc['module'], 'kind': doc['kind'],
                'file': os.path.basename(path),
                'counts': {'monsters': c['monsters'], 'items': c['items']},
            })
            print(f'{doc["module"][:45]:45} {c["monsters"]:5d}m {c["items"]:6d}i'
                  f'{"  [mod]" if doc["counts"].get("notes") else ""}')

        # PRC8 expansion pseudo-module (Stage 6)
        exp_path, exp_doc = emit_prc8_expansion(gen)
        if exp_doc:
            manifest_modules.append({
                'id': exp_doc['id'], 'name': exp_doc['module'], 'kind': exp_doc['kind'],
                'file': os.path.basename(exp_path),
                'counts': {'monsters': exp_doc['counts']['monsters'],
                           'items': exp_doc['counts']['items']},
            })
            print(f'{exp_doc["module"][:45]:45} {exp_doc["counts"]["monsters"]:5d}m '
                  f'{exp_doc["counts"]["items"]:6d}i')

        manifest = {
            'schema': 2,
            'generated': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'modules': manifest_modules,
        }
        with open(os.path.join(gen.data_dir, 'manifest.json'), 'w', encoding='utf-8') as fh:
            json.dump(manifest, fh, ensure_ascii=False, separators=(',', ':'))
        print(f'\nmanifest: {len(manifest_modules)} modules; skipped: {len(skipped)}')
        for name, why in skipped:
            print(f'  skipped {name}: {why}')
        return


def emit_prc8_expansion(gen):
    """Index PRC8's own blueprint set (prc8_misc.hak content) as a pseudo-module."""
    from lib.modules import ModuleSpec
    cfg = gen.cfg
    src = os.path.join(cfg['prc_root'], cfg['prc8_expansion']['source_dir'])
    if not os.path.isdir(src):
        return None, None
    skip = set(cfg['skip_dirs'])
    files = []
    for root, dirs, fnames in os.walk(src):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in fnames:
            if f.lower().endswith(('.utc', '.uti', '.utc.json', '.uti.json')):
                files.append(os.path.join(root, f))
    spec = ModuleSpec(src, cfg['prc8_expansion']['name'], 'prc8-expansion', None,
                      sorted(files), [])
    path, doc = gen.emit_module(spec)
    doc['kind'] = 'expansion'
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, ensure_ascii=False, separators=(',', ':'))
    return path, doc


if __name__ == '__main__':
    main()
