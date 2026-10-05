"""UTC -> monster record and UTI -> item record mapping."""

from .gffread import val, locstr_field
from .locstr import locstr_text


class Counters:
    def __init__(self):
        self.data = {}

    def bump(self, key, n=1):
        self.data[key] = self.data.get(key, 0) + n

    def note(self, key, value, limit=5):
        samples = self.data.setdefault(key + '_samples', [])
        if len(samples) < limit:
            samples.append(str(value))

    def report(self):
        out = {k: v for k, v in self.data.items() if not k.endswith('_samples')}
        return out


class ModuleContext:
    """Per-module name-resolution context: base tlk + module custom tlk + fallbacks + 2DA chain."""

    def __init__(self, base_tlk, custom_tlk, fallback_tlks, twoda_chain, counters):
        self.base = base_tlk
        self.custom = custom_tlk
        self.fallbacks = tuple(fallback_tlks)
        self.chain = twoda_chain
        self.counters = counters

    def locstr(self, field):
        if field is None:
            return '', True
        text, resolved = locstr_text(field, self.base, self.custom, self.fallbacks)
        if not resolved:
            self.counters.bump('unresolved_strrefs')
        return text, resolved

    def _2da_name(self, twoda_name, row, counters_key, label_fmt):
        """Resolve a 2DA row's human name: Name column (strref or text), else Label column text."""
        if row is None:
            return None
        twoda = self.chain.get(twoda_name)
        if twoda is None or row not in twoda.rows:
            self.counters.bump(counters_key)
            self.counters.note(counters_key, row)
            return None
        raw = twoda.get(row, 'Name')
        if raw is not None:
            text = raw
            if raw.lstrip('-').isdigit():
                text, _ = locstr_text({'value': {'id': int(raw)}},
                                      self.base, self.custom, self.fallbacks)
            if text:
                return text
        label = twoda.get(row, 'Label') or twoda.get(row, 'label')
        if label:
            return label
        return None

    def race_name(self, race_id):
        return self._2da_name('racialtypes.2da', race_id, 'unmapped_races', 'Race')

    def class_name(self, class_id):
        return self._2da_name('classes.2da', class_id, 'unmapped_classes', 'Class')

    def baseitem_name(self, baseitem_id):
        return self._2da_name('baseitems.2da', baseitem_id, 'unmapped_baseitems', 'BaseItem')

    def portrait_resref(self, portrait_id):
        if portrait_id is None:
            return ''
        twoda = self.chain.get('portraits.2da')
        resref = twoda.get(portrait_id, 'BaseResRef') if twoda else None
        if not resref:
            self.counters.bump('unmapped_portraits')
            return ''
        return resref


def monster_from_utc(gff, ctx, fallback_resref):
    counters = ctx.counters
    first, _ = ctx.locstr(locstr_field(gff, 'FirstName'))
    last, _ = ctx.locstr(locstr_field(gff, 'LastName'))

    race_id = val(gff, 'Race')
    race = ctx.race_name(race_id)
    if race is None:
        race = f'Race {race_id}'

    classes = []
    for entry in (val(gff, 'ClassList') or []):
        cid = val(entry, 'Class')
        cname = ctx.class_name(cid)
        if cname is None:
            cname = f'Class {cid}'
        classes.append({'Class': cname, 'Level': val(entry, 'ClassLevel')})

    hp = val(gff, 'MaxHitPoints')
    if hp is None:
        hp = val(gff, 'HitPoints')

    return {
        'ResRef': val(gff, 'TemplateResRef') or fallback_resref,
        'FirstName': first,
        'LastName': last,
        'Race': race,
        'ChallengeRating': val(gff, 'ChallengeRating'),
        'CR_Adjust': val(gff, 'CRAdjust'),
        'HitPoints': hp,
        'Stats': {
            'Str': val(gff, 'Str'),
            'Dex': val(gff, 'Dex'),
            'Con': val(gff, 'Con'),
            'Int': val(gff, 'Int'),
            'Wis': val(gff, 'Wis'),
            'Cha': val(gff, 'Cha'),
        },
        'Classes': classes,
        'Portrait': ctx.portrait_resref(val(gff, 'PortraitId')),
        'Tag': val(gff, 'Tag') or '',
    }


def item_from_uti(gff, ctx, fallback_resref, truncate=280):
    name, _ = ctx.locstr(locstr_field(gff, 'LocalizedName'))

    desc, _ = ctx.locstr(locstr_field(gff, 'DescIdentified'))
    if not desc:
        desc, _ = ctx.locstr(locstr_field(gff, 'Description'))
    if len(desc) > truncate:
        desc = desc[:truncate - 1] + '…'

    baseitem_id = val(gff, 'BaseItem')
    baseitem = ctx.baseitem_name(baseitem_id)
    if baseitem is None:
        baseitem = f'BaseItem {baseitem_id}'

    props = val(gff, 'PropertiesList') or []
    props = [p for p in props if val(p, 'PropertyName') is not None]

    from .itemprop import ItemPropDecoder
    decoder = getattr(ctx, '_itemprop_decoder', None)
    if decoder is None:
        decoder = ItemPropDecoder(ctx)
        ctx._itemprop_decoder = decoder
    decoded = []
    for p in props:
        text = decoder.decode(p)
        decoded.append(text if text else f"Property {val(p, 'PropertyName')}/{val(p, 'Subtype')}")

    rec = {
        'ResRef': val(gff, 'TemplateResRef') or fallback_resref,
        'Name': name,
        'Description': desc,
        'BaseItem': baseitem,
        'BaseItemId': baseitem_id,
        'GoldPieceValue': (val(gff, 'Cost') or 0) + (val(gff, 'AddCost') or 0),
        'StackSize': val(gff, 'StackSize'),
        'Charges': val(gff, 'Charges'),
        'Plot': bool(val(gff, 'Plot')),
        'Identified': bool(val(gff, 'Identified')),
        'Stolen': bool(val(gff, 'Stolen')),
        'Cursed': bool(val(gff, 'Cursed')),
        'PropertiesCount': len(props),
        'Tag': val(gff, 'Tag') or '',
    }
    if props:
        rec['PropertiesDecoded'] = decoded
    return rec
