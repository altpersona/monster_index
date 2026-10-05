"""Thin wrappers around the `nwn` binary for ERF/HAK access and GFF conversion."""

import hashlib
import json
import os
import subprocess


class ErfUtil:
    def __init__(self, nwn_bin, cache_dir):
        self.nwn_bin = str(nwn_bin)
        self.cache_dir = str(cache_dir)
        self._erf_cache_dir = os.path.join(self.cache_dir, 'erf')
        self._key_cache_dir = os.path.join(self.cache_dir, 'key2da')
        self._gff_cache_dir = os.path.join(self.cache_dir, 'gff')
        os.makedirs(self._erf_cache_dir, exist_ok=True)
        os.makedirs(self._key_cache_dir, exist_ok=True)
        os.makedirs(self._gff_cache_dir, exist_ok=True)

    def _run(self, args, cwd=None, check=True):
        proc = subprocess.run([self.nwn_bin] + args, cwd=cwd,
                              capture_output=True, text=True, errors='replace')
        if check and proc.returncode != 0:
            raise RuntimeError(f'nwn {" ".join(args)} failed: {proc.stderr.strip()[:400]}')
        return proc

    # ---- ERF/HAK ----

    def erf_cache_path(self, erf_path, entry):
        """Stable per-(erf,entry) extraction path. Re-extracts when the erf changes."""
        erf_path = str(erf_path)
        tag = hashlib.sha1(f'{erf_path}|{os.path.getmtime(erf_path):.0f}|{os.path.getsize(erf_path)}'.encode()).hexdigest()[:16]
        d = os.path.join(self._erf_cache_dir, tag)
        return os.path.join(d, entry.replace('/', '_'))

    def extract_entry(self, erf_path, entry):
        """Extract one entry (e.g. 'racialtypes.2da') from an erf/hak; returns path or None."""
        target = self.erf_cache_path(erf_path, entry)
        if os.path.isfile(target):
            return target
        d = os.path.dirname(target)
        os.makedirs(d, exist_ok=True)
        listing = self._run(['erf', '-f', str(erf_path), '-t'], check=False).stdout
        if entry not in listing:
            return None
        self._run(['erf', '-f', str(erf_path), '-x', entry], cwd=d)
        if os.path.isfile(target):
            return target
        # some versions emit lowercase / resref-only names
        for f in os.listdir(d):
            if f.lower() == entry.lower():
                return os.path.join(d, f)
        return None

    def unpack_erf(self, erf_path, dest_dir):
        """Unpack a whole erf/hak/mod into dest_dir."""
        os.makedirs(dest_dir, exist_ok=True)
        self._run(['erf', '-f', str(erf_path), '-x'], cwd=dest_dir)
        return dest_dir

    # ---- KEY (base game) ----

    def extract_from_key(self, root, name):
        """Pull an exact-named resource from the base-game key stack under root."""
        target = os.path.join(self._key_cache_dir, name)
        if os.path.isfile(target):
            return target
        self._run(['resman', 'extract', '--root', str(root),
                   '-p', name, '-d', self._key_cache_dir], check=False)
        if os.path.isfile(target):
            return target
        return None

    # ---- GFF ----

    def gff_to_json(self, gff_path):
        """Convert a binary GFF to JSON via `nwn gff`; cached by (path, mtime, size).

        nwn gff detects the format from the file extension case-sensitively, so
        uppercase (.UTC/.UTI — common in the PRC8 tree) is converted through a
        lowercase-named copy in the cache.
        """
        import shutil
        gff_path = str(gff_path)
        base, ext = os.path.splitext(gff_path)
        if ext and ext != ext.lower():
            lowered = os.path.join(self._gff_cache_dir,
                                   hashlib.sha1(gff_path.encode()).hexdigest() + ext.lower())
            if not os.path.isfile(lowered) or os.path.getmtime(lowered) < os.path.getmtime(gff_path):
                shutil.copyfile(gff_path, lowered)
            gff_path = lowered
        st = os.stat(gff_path)
        key = hashlib.sha1(f'{gff_path}|{st.st_mtime:.0f}|{st.st_size}'.encode()).hexdigest()
        out = os.path.join(self._gff_cache_dir, key + '.json')
        if os.path.isfile(out):
            with open(out, encoding='utf-8') as fh:
                return json.load(fh)
        tmp = out + '.tmp'
        self._run(['gff', '-i', gff_path, '-k', 'json', '-o', tmp,
                   '--nwn-encoding', 'windows-1252'])
        os.replace(tmp, out)
        with open(out, encoding='utf-8') as fh:
            return json.load(fh)
