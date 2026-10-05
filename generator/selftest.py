"""Golden selftest for the generator plumbing (Stage 1).

Run: python3 generator/selftest.py   (from the repo root)
Every assertion corresponds to a fact verified against real files during planning.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib.tlk import Tlk                                    # noqa: E402
from lib.locstr import locstr_text                         # noqa: E402
from lib.twoda import TwoDAChain                           # noqa: E402
from lib.erf import ErfUtil                                # noqa: E402

CFG = json.load(open(os.path.join(HERE, 'config.json')))
PRC = CFG['prc_root']

checks = []


def check(label, cond, detail=''):
    checks.append((label, bool(cond), detail))
    mark = 'PASS' if cond else 'FAIL'
    print(f'{mark}  {label}{"  — " + detail if detail and not cond else ""}')


# ---- TLK binary ----
base = Tlk(CFG['base_tlk'])
check('base tlk[5213] == "Barbarian"', base.get(5213) == 'Barbarian', repr(base.get(5213)))
check('base tlk[5999] == "Imp"', base.get(5999) == 'Imp', repr(base.get(5999)))

merge_tlk = Tlk(os.path.join(PRC, 'Underworld 2 [PRC8-CEP3]', 'prc8_cep3_merge.tlk'))
dwarf_desc = merge_tlk.get(49738)
check('merge tlk[49738] Dwarf description', bool(dwarf_desc and dwarf_desc.startswith('Dwarves are known')),
      repr(dwarf_desc)[:80] if dwarf_desc else 'None')

consortium = Tlk(os.path.join(PRC, 'PRC8', 'nwn/nwnprc/trunk/tlk/prc8_consortium.tlk'))
check('consortium tlk loads (non-empty)', len(consortium) > 1000, f'{len(consortium)} entries')

# ---- TLK json (nasher) ----
salt_path = os.path.join(PRC, 'TSSoS_PRC8', 'src/module/tlk/salt_prc8_merge.tlk.json')
if os.path.isfile(salt_path):
    salt = Tlk(salt_path)
    some = salt.get(0) or salt.get(1)
    check('salt .tlk.json loads', some is not None, 'entries=%d' % len(salt))
else:
    check('salt .tlk.json loads', False, f'missing: {salt_path}')

# ---- locstring resolution ----
emb, res = locstr_text({'value': {'0': 'Mithril Imp', 'id': 5999}}, base)
check('locstring embedded-0 wins', emb == 'Mithril Imp' and res)

via_strref, res = locstr_text({'value': {'id': 5213}}, base)
check('locstring strref -> base tlk', via_strref == 'Barbarian' and res)

via_custom, res = locstr_text({'value': {'id': 16777216 + 49738}}, base, custom_tlk=merge_tlk)
check('locstring custom strref -> merge tlk', via_custom == dwarf_desc and res)

unres, res = locstr_text({'value': {'id': 16777216 + 4000000}}, base, custom_tlk=merge_tlk)
check('unresolvable strref -> empty, resolved=False', unres == '' and not res)

# ---- 2DA shadow chain ----
erf = ErfUtil(CFG['nwn_bin'], os.path.join(HERE, '.cache'))


def resolve_src(src):
    s = dict(src)
    if s.get('prc_root_relative'):
        s['path'] = os.path.join(os.path.dirname(PRC), s['path'])
    elif s['type'] == 'dir' and not os.path.isabs(s['path']):
        s['path'] = os.path.join(PRC, s['path'])
    return s


chain = TwoDAChain([resolve_src(s) for s in CFG['twoda_sources']], erf, erf.cache_dir)
classes = chain.get('classes.2da')
check('classes.2da chain resolves', classes is not None and len(classes) > 200,
      f'{len(classes) if classes else 0} rows')

name_strref = int(classes.get(0, 'Name', -1))
check('classes.2da[0].Name -> "Barbarian"',
      locstr_text({'value': {'id': name_strref}}, base, consortium)[0] == 'Barbarian',
      f'strref={name_strref}')

races = chain.get('racialtypes.2da')
race0 = locstr_text({'value': {'id': int(races.get(0, 'Name', -1))}}, base, merge_tlk, (consortium,))[0]
check('racialtypes.2da[0].Name -> "Dwarf"', race0 == 'Dwarf', repr(race0))

items2da = chain.get('baseitems.2da')
bi24 = locstr_text({'value': {'id': int(items2da.get(24, 'Name', -1))}}, base, merge_tlk, (consortium,))[0]
check('baseitems.2da[24].Name resolves', bool(bi24), repr(bi24))

portraits = chain.get('portraits.2da')
p243 = portraits.get(243, 'BaseResRef') if portraits else None
check('portraits.2da[243].BaseResRef present', bool(p243), repr(p243))

# ---- summary ----
failed = [c for c in checks if not c[1]]
print(f'\n{len(checks) - len(failed)}/{len(checks)} passed')
sys.exit(1 if failed else 0)
