"""cexolocstring resolution.

GFF/nasher JSON shape: {"type": "cexolocstring", "value": {"0": "Text", "id": 5999, ..}}
Resolution order (matches NWN's own precedence for our purposes):
  1. embedded language-0 (English) string, when non-empty
  2. strref: < 16777216 -> base dialog.tlk; >= 16777216 -> custom tlk
     (index = strref - 16777216), then any fallback tlks, in order
"""

from .tlk import Tlk, CUSTOM_STRREF_BASE


def resolve_strref(strref, base_tlk=None, custom_tlk=None, fallback_tlks=()):
    if strref is None or strref < 0:
        return None
    if strref < CUSTOM_STRREF_BASE:
        return base_tlk.get(strref) if base_tlk else None
    for tlk in ((custom_tlk,) if custom_tlk is not None else ()) + tuple(fallback_tlks):
        text = tlk.get(strref - CUSTOM_STRREF_BASE)
        if text is not None:
            return text
    return None


def locstr_text(field, base_tlk=None, custom_tlk=None, fallback_tlks=()):
    """field: the GFF field dict (with 'value'), or the inner value dict, or None.

    Returns (text, resolved) — text is '' when nothing resolved; resolved is
    False when a strref was present but no table produced a string.
    """
    value = field
    if isinstance(field, dict) and 'value' in field and isinstance(field['value'], dict):
        value = field['value']
    if not isinstance(value, dict):
        return '', True

    embedded = value.get('0')
    if isinstance(embedded, str) and embedded:
        return embedded, True

    strref = value.get('id', -1)
    if isinstance(strref, int) and strref >= 0:
        text = resolve_strref(strref, base_tlk, custom_tlk, fallback_tlks)
        if text is not None:
            return text, True
        return '', False
    return '', True
