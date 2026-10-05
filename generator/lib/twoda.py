"""2DA V2.0 parsing + shadow-chain resolution.

NWN hak semantics: a 2DA file present in a later source REPLACES the earlier
file entirely (whole-file shadow, not per-row). The chain loader walks sources
in order and the last source that provides a given 2DA wins.
"""

import re

_QUOTED = re.compile(r'"([^"]*)"|(\S+)')


def tokenize_line(line):
    return [a if a else b for a, b in _QUOTED.findall(line)]


class TwoDA:
    def __init__(self, name, text):
        self.name = name
        self.columns = []
        self.rows = {}          # rowid (int) -> {col: str|None}
        self._parse(text)

    def _parse(self, text):
        lines = text.splitlines()
        i = 0
        if not lines or not lines[0].startswith('2DA'):
            # tolerate missing header (some exports) — treat first line as header row anyway
            pass
        else:
            i = 1
        # skip blank lines
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            return
        header = tokenize_line(lines[i])
        # The row-id column placeholder is blank, so it produces no token —
        # use the header tokens as-is. (Files whose first header cell is a
        # real label like "Label" also parse correctly this way.)
        self.columns = header
        i += 1
        for line in lines[i:]:
            if not line.strip():
                continue
            if line.strip().startswith('2DA'):
                continue
            toks = tokenize_line(line)
            if not toks:
                continue
            try:
                rowid = int(toks[0])
            except ValueError:
                continue
            vals = toks[1:]
            row = {}
            for col, val in zip(self.columns, vals):
                row[col] = None if val == '****' else val
            self.rows[rowid] = row

    def get(self, rowid, col, default=None):
        row = self.rows.get(rowid)
        if row is None:
            return default
        return row.get(col, default)

    def __len__(self):
        return len(self.rows)


class TwoDAChain:
    """Resolves 2DAs across dir / hak / key sources; last source that has the file wins."""

    def __init__(self, sources, erfutil, cache_dir):
        self.sources = sources        # list of {"type": "dir"|"hak"|"key", ...}
        self.erf = erfutil            # lib.erf.ErfUtil
        self.cache_dir = cache_dir
        self._loaded = {}             # name -> TwoDA | None

    def get(self, name):
        """name like 'classes.2da'. Returns TwoDA or None."""
        if name in self._loaded:
            return self._loaded[name]
        twoda = self._load(name)
        self._loaded[name] = twoda
        return twoda

    def _load(self, name):
        # dir/hak sources: later source shadows earlier (NWN whole-file semantics).
        # "fallback": true sources (the base-game key) only answer when no
        # dir/hak source provides the file — the key is the bottom of the stack.
        result = None
        for src in self.sources:
            if src.get('fallback'):
                continue
            found = self._from_source(src, name)
            if found is not None:
                result = found
        if result is None:
            for src in self.sources:
                if not src.get('fallback'):
                    continue
                result = self._from_source(src, name)
                if result is not None:
                    break
        return result

    def _from_source(self, src, name):
        stype = src.get('type')
        if stype == 'dir':
            import os
            p = os.path.join(src['path'], name)
            if os.path.isfile(p):
                with open(p, encoding='windows-1252', errors='replace') as fh:
                    return TwoDA(name, fh.read())
            return None
        if stype == 'hak':
            path = self.erf.extract_entry(src['path'], name)
            if path:
                with open(path, encoding='windows-1252', errors='replace') as fh:
                    return TwoDA(name, fh.read())
            return None
        if stype == 'key':
            path = self.erf.extract_from_key(src['root'], name)
            if path:
                with open(path, encoding='windows-1252', errors='replace') as fh:
                    return TwoDA(name, fh.read())
            return None
        raise ValueError(f'unknown 2da source type: {stype}')
