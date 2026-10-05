#!/usr/bin/env python3
"""Populate data/portraits/ with PNGs for every portrait the index references.

Reads each data/<module>.json monster's Portrait field (a portraits.2da
BaseResRef like 'po_a_bat_'), derives the filename the viewer loads
(po_ prefix and trailing _ stripped, lowercased), finds the best-size TGA
(l > m > h > plain) in the portrait haks, and converts it to PNG.

Usage: python3 generator/portraits.py [--force]
"""

import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PIL import Image

from lib.erf import ErfUtil

CFG = json.load(open(os.path.join(HERE, 'config.json')))
REPO = os.path.dirname(HERE)
PORTRAIT_HAKS = [
    # in rack_maint/hak — CEP1/CEP3/q additions on top of the base game set
    '/home/default/projects/projects/rack_maint/hak/cepportrait.hak',
    '/home/default/projects/projects/rack_maint/hak/cep3_portraits.hak',
    '/home/default/projects/projects/rack_maint/hak/q_portraits.hak',
]
CLIENT_ROOT = '/home/default/Beamdog Library/00785'   # full client install: has the base portraits in its bifs
SIZE_PREFERENCE = ['l', 'm', '', 'h', 's', 't']   # best-looking first for an 80px circle


def viewer_name(base_resref):
    name = base_resref.lower()
    if name.startswith('po_'):
        name = name[3:]
    if name.endswith('_'):
        name = name[:-1]
    return name


def unpack_sources(erf):
    """One-time prep: bulk po_* extract from the client key + full hak unpacks."""
    srcs = []
    key_dest = os.path.join(erf.cache_dir, 'portraits_key')
    if not os.path.isdir(key_dest) or len(os.listdir(key_dest)) < 1000:
        print('  extracting po_* from the client install…')
        os.makedirs(key_dest, exist_ok=True)
        erf._run(['resman', 'extract', '--root', CLIENT_ROOT,
                  '-p', 'po_', '-d', key_dest], check=False)
    print(f'  client key: {len(os.listdir(key_dest))} files')
    srcs.append(key_dest)
    for hak in PORTRAIT_HAKS:
        if not os.path.isfile(hak):
            print(f'  (missing hak, skipping: {hak})')
            continue
        dest = os.path.join(erf.cache_dir, 'portraits_src',
                            os.path.basename(hak) + f'_{os.path.getmtime(hak):.0f}')
        if not os.path.isdir(dest) or len(os.listdir(dest)) < 100:
            print(f'  unpacking {os.path.basename(hak)}…')
            erf.unpack_erf(hak, dest)
        n = len(os.listdir(dest))
        print(f'  {os.path.basename(hak)}: {n} files')
        srcs.append(dest)
    return srcs


def find_tga(base, srcs):
    """Best-size TGA for a BaseResRef across sources.

    portraits.2da BaseResRefs are inconsistent: base-game rows are bare
    ('bat_') while the files are po_bat_l.tga; CEP rows usually carry the
    po_ prefix themselves. Try both prefix forms × size suffixes.
    """
    low = base.lower()
    prefixes = [low] if low.startswith('po_') else [low, 'po_' + low]
    for prefix in prefixes:
        for suffix in SIZE_PREFERENCE:
            fname = f'{prefix}{suffix}.tga'
            for src in srcs:
                p = os.path.join(src, fname)
                if os.path.isfile(p) and os.path.getsize(p) > 0:
                    return p
    return None


def sweep_haks(erf, bases):
    """Last resort for still-missing portraits: every hak in the live server
    library AND the prc workdirs, each listed once, matching all wanted names."""
    wanted = {}   # entry filename -> base
    for base in bases:
        low = base.lower()
        prefixes = [low] if low.startswith('po_') else [low, 'po_' + low]
        for prefix in prefixes:
            for suffix in SIZE_PREFERENCE:
                wanted[f'{prefix}{suffix}.tga'] = base

    haks = sorted(glob.glob('/home/default/projects/projects/rack_maint/hak/*.hak'))
    for root, dirs, files in os.walk(CFG['prc_root']):
        dirs[:] = [d for d in dirs if d not in set(CFG['skip_dirs'])]
        for f in files:
            if f.lower().endswith('.hak'):
                haks.append(os.path.join(root, f))

    found = {}
    for hak in haks:
        if not wanted:
            break
        listing = erf._run(['erf', '-f', hak, '-t'], check=False).stdout.lower()
        hits = [e for e in list(wanted) if e in listing]
        for entry in hits:
            path = erf.extract_entry(hak, entry)
            if path and os.path.getsize(path) > 0:
                base = wanted.pop(entry)
                best = found.get(base)
                if best is None or SIZE_PREFERENCE.index(
                        entry.rsplit('.tga', 1)[0].rsplit('_', 1)[-1] or '') < SIZE_PREFERENCE.index(
                        best.rsplit('.tga', 1)[0].rsplit('_', 1)[-1] or ''):
                    found[base] = path
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true', help='regenerate existing PNGs too')
    args = ap.parse_args()

    needed = set()
    for f in glob.glob(os.path.join(REPO, 'data', '*.json')):
        if f.endswith('manifest.json'):
            continue
        doc = json.load(open(f))
        for m in doc.get('monsters', []):
            p = m.get('Portrait')
            if p:
                needed.add(p)
    print(f'portrait resrefs referenced: {len(needed)}')

    out_dir = os.path.join(REPO, 'data', 'portraits')
    os.makedirs(out_dir, exist_ok=True)

    erf = ErfUtil(CFG['nwn_bin'], os.path.join(HERE, '.cache'))
    srcs = unpack_sources(erf)

    # pre-sweep: which bases still lack a source TGA?
    unresolved = [b for b in sorted(needed)
                  if not find_tga(b, srcs)
                  and not os.path.isfile(os.path.join(out_dir, viewer_name(b) + '.png'))]
    if unresolved:
        print(f'sweeping {len(unresolved)} unresolved resrefs across all haks…')
        swept = sweep_haks(erf, unresolved)
        print(f'  sweep found {len(swept)}')
        sweep_dir = os.path.join(erf.cache_dir, 'portraits_swept')
        os.makedirs(sweep_dir, exist_ok=True)
        for base, path in swept.items():
            import shutil
            dest = os.path.join(sweep_dir, os.path.basename(path))
            if not os.path.isfile(dest):
                shutil.copyfile(path, dest)
        srcs.append(sweep_dir)

    made = missing = skipped = errors = 0
    missing_samples = []
    for base in sorted(needed):
        out = os.path.join(out_dir, viewer_name(base) + '.png')
        if os.path.isfile(out) and not args.force:
            skipped += 1
            continue
        tga = find_tga(base, srcs)
        if not tga:
            missing += 1
            if len(missing_samples) < 8:
                missing_samples.append(base)
            continue
        try:
            img = Image.open(tga)
            img.save(out)
            made += 1
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f'  error on {tga}: {e}')

    print(f'converted={made} already-present={skipped} missing={missing} errors={errors}')
    if missing_samples:
        print('  missing examples:', missing_samples)


if __name__ == '__main__':
    main()
