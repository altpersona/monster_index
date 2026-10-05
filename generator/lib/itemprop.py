"""Item property decoding: UTI PropertiesList structs -> human-readable strings.

Chain per property struct {PropertyName, Subtype, CostTable, CostValue, Param1, Param1Value}:
  PropertyName -> itempropdef.2da row:
      Name (strref) / Label              -> property name ("CastSpell", "Enhancement"...)
      SubTypeResRef (e.g. IPRP_SPELLS)   -> <lower>.2da, row = Subtype    -> subtype name
      CostTableResRef (int)              -> iprp_costtable.2da row -> Name (e.g. IPRP_MELEECOST)
                                            -> iprp_meleecost.2da row = CostValue -> value label
      Param1ResRef (int)                 -> iprp_param1.2da row -> Name (e.g. IPRP_ALIGNMENT)
                                            -> <lower>.2da row = Param1Value -> label
Anything unresolvable degrades to a "Property P/S" placeholder, counted as undecoded.
"""

from .gffread import val

NA = '****'


class ItemPropDecoder:
    def __init__(self, ctx):
        self.ctx = ctx
        self.chain = ctx.chain
        self.itempropdef = self.chain.get('itempropdef.2da')
        self.costtable = self.chain.get('iprp_costtable.2da')
        self.param1table = self.chain.get('iprp_param1.2da')

    def _row_name(self, twoda, row):
        """Best human text for a 2DA row: Name strref, else Label."""
        if twoda is None or row is None or row < 0:
            return None
        raw = twoda.get(row, 'Name')
        if raw is not None:
            text = raw
            # resolve numeric Name as strref via the module context
            if raw.lstrip('-').isdigit():
                from .locstr import locstr_text
                text, _ = locstr_text({'value': {'id': int(raw)}},
                                      self.ctx.base, self.ctx.custom, self.ctx.fallbacks)
            if text:
                return text
        return twoda.get(row, 'Label')

    def _table_from_ref(self, reftable, refrow, prefix=''):
        """Follow a <X>ResRef int: reftable[refrow].Name -> lowercased .2da file."""
        if reftable is None or refrow is None or refrow < 0:
            return None
        name = reftable.get(refrow, 'Name')
        if not name or name == NA:
            return None
        return self.chain.get(name.lower() + '.2da')

    def decode(self, prop):
        """prop: raw GFF struct dict. Returns decoded string (never raises)."""
        try:
            return self._decode(prop)
        except Exception:
            self.ctx.counters.bump('undecoded_properties')
            return None

    def _decode(self, prop):
        pname_id = val(prop, 'PropertyName')
        if pname_id is None or self.itempropdef is None or pname_id not in self.itempropdef.rows:
            self.ctx.counters.bump('undecoded_properties')
            return None

        parts = []

        prop_label = self._row_name(self.itempropdef, pname_id)
        subres = self.itempropdef.get(pname_id, 'SubTypeResRef')
        costref = self.itempropdef.get(pname_id, 'CostTableResRef')
        paramref = self.itempropdef.get(pname_id, 'Param1ResRef')

        # property name (suffix-style names read better without the raw label alone)
        prop_name = prop_label or f'Property {pname_id}'

        # subtype (e.g. the actual spell / ability / damage type)
        subtype_txt = None
        if subres and subres != NA:
            sub2da = self.chain.get(subres.lower() + '.2da')
            st = val(prop, 'Subtype')
            if st is not None:
                subtype_txt = self._row_name(sub2da, st)

        # param1 (rare; e.g. alignment keys)
        param_txt = None
        p1 = val(prop, 'Param1')
        if paramref and paramref != NA:
            p1t = self._table_from_ref(self.param1table, int(paramref) if str(paramref).isdigit() else None)
            if p1t is not None and p1 is not None:
                label = self._row_name(p1t, p1)
                if label:
                    param_txt = label

        # cost value (e.g. "+5", "1d6")
        value_txt = None
        ct = val(prop, 'CostTable')
        cv = val(prop, 'CostValue')
        if costref and str(costref) not in (NA, '0') and ct is not None and cv is not None:
            costtable2da = self._table_from_ref(self.costtable, int(costref) if str(costref).isdigit() else None)
            if costtable2da is not None:
                value_txt = self._row_name(costtable2da, cv)

        if subtype_txt:
            parts.append(subtype_txt)
        parts.append(prop_name)
        if value_txt:
            parts.append(value_txt)
        if param_txt:
            parts.append(f'({param_txt} {val(prop, "Param1Value")})')

        return ' '.join(parts)
