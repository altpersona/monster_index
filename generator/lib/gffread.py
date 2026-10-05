"""GFF loading — nasher JSON directly, binary GFF via the nwn binary (cached)."""

import json


def load_gff(path, erfutil):
    """path: .json (nasher dump) or binary GFF (.utc/.uti/.ifo/...). Returns the GFF dict.

    Some nasher dumps are not valid UTF-8 (raw windows-1252 bytes inside string
    values) — decode those as cp1252 instead of failing the record.
    """
    p = str(path)
    if p.endswith('.json'):
        with open(p, 'rb') as fh:
            raw = fh.read()
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('windows-1252', errors='replace')
        return json.loads(text)
    return erfutil.gff_to_json(p)


def val(gff, key, default=None):
    """Unwrap a GFF field's {"type":..,"value":..} wrapper."""
    f = gff.get(key) if isinstance(gff, dict) else None
    if isinstance(f, dict) and 'value' in f:
        return f['value']
    return default


def locstr_field(gff, key):
    f = gff.get(key) if isinstance(gff, dict) else None
    if isinstance(f, dict) and isinstance(f.get('value'), dict):
        return f
    return None
