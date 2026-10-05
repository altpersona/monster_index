"""TLK (talk table) reading — binary TLK V3.0 and nasher .tlk.json.

Binary format (verified against prc8_consortium.tlk / dialog.tlk):
  header 20 bytes: magic[8] "TLK V3.0", langId u32, stringCount u32, stringEntriesOffset u32
  entries, 40 bytes each, in strref order:
    flags u32, soundResRef[16], volumeVar u32, pitchVar u32,
    offset u32 (relative to stringEntriesOffset), stringSize u32, soundLen f32

Strings are decoded lazily — eagerly materialising ~170k python strings for the
base tlk is what OOMs; keeping the raw bytes and decoding per-index is cheap.

nasher .tlk.json shape: {"language": .., "entries": [{"id": N, "text": ".."}, ..]}
where id is the custom-range index (final strref = 16777216 + id).
"""

import json
import struct

TEXT_FLAG = 0x1
CUSTOM_STRREF_BASE = 16777216


class Tlk:
    def __init__(self, path):
        self.path = str(path)
        self._raw = None
        self._entries = None      # list of (offset_abs, size) for binary
        self._jsonmap = None      # {index: text}
        self._cache = {}

        if self.path.endswith('.json'):
            with open(self.path, encoding='utf-8') as fh:
                doc = json.load(fh)
            self._jsonmap = {int(e['id']): e.get('text', '')
                             for e in doc.get('entries', [])}
        else:
            with open(self.path, 'rb') as fh:
                raw = fh.read()
            magic, _lang, count, entries_off = struct.unpack_from('<8sIII', raw, 0)
            if not magic.startswith(b'TLK '):
                raise ValueError(f'{self.path}: not a TLK file (magic {magic!r})')
            self._raw = raw
            self._entries = []
            pos = 20
            for _ in range(count):
                flags, _snd, _vol, _pitch, off, size, _slen = \
                    struct.unpack_from('<I16sIIIIf', raw, pos)
                self._entries.append((entries_off + off, size) if flags & TEXT_FLAG else None)
                pos += 40

    def get(self, index):
        """Return the string at table index, or None if absent/empty."""
        if index is None or index < 0:
            return None
        if self._jsonmap is not None:
            text = self._jsonmap.get(int(index))
            return text if text else None
        if index >= len(self._entries):
            return None
        if index in self._cache:
            return self._cache[index]
        ent = self._entries[index]
        if ent is None:
            return None
        off, size = ent
        text = self._raw[off:off + size].decode('windows-1252', errors='replace')
        if not text:
            return None
        self._cache[index] = text
        return text

    def __len__(self):
        if self._jsonmap is not None:
            return max(self._jsonmap) + 1 if self._jsonmap else 0
        return len(self._entries)


def is_custom(strref):
    return strref is not None and strref >= CUSTOM_STRREF_BASE


def custom_index(strref):
    return strref - CUSTOM_STRREF_BASE
