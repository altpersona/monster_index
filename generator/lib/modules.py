"""Module discovery over the prc/ workdir tree."""

import os
import re

BLUEPRINT_EXTS = ('.utc.json', '.uti.json', '.utc', '.uti')


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", '-', name.lower()).strip('-')
    return slug or 'module'


def iter_files(module_dir, skip_dirs):
    """Yield sorted blueprint file paths under module_dir, skipping junk dirs."""
    found = []
    for root, dirs, files in os.walk(module_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            low = f.lower()
            if low.endswith(BLUEPRINT_EXTS):
                found.append(os.path.join(root, f))
    return sorted(found)


def find_module_ifos(module_dir, skip_dirs):
    """All module.ifo / module.ifo.json under the workdir (may be several units)."""
    hits = []
    for root, dirs, files in os.walk(module_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for f in files:
            if f.lower() in ('module.ifo', 'module.ifo.json'):
                hits.append(os.path.join(root, f))
    return sorted(hits)


class ModuleSpec:
    def __init__(self, module_dir, name, slug, custom_tlk, files, ifo_paths):
        self.dir = module_dir
        self.name = name
        self.slug = slug
        self.custom_tlk = custom_tlk          # tlk name string or None
        self.files = files                    # sorted blueprint paths
        self.ifo_paths = ifo_paths

    @property
    def utc_files(self):
        return [f for f in self.files if f.lower().endswith(('.utc', '.utc.json'))]

    @property
    def uti_files(self):
        return [f for f in self.files if f.lower().endswith(('.uti', '.uti.json'))]


def find_tlk(name, search_paths):
    """Locate <name>.tlk or <name>.tlk.json in the search paths (already made absolute)."""
    for d in search_paths:
        for ext in ('.tlk', '.tlk.json'):
            p = os.path.join(d, name + ext)
            if os.path.isfile(p):
                return p
    return None


def discover(config):
    """Enumerate module workdirs under prc_root. Returns list of ModuleSpec (no tlk/ifo resolution yet)."""
    prc_root = config['prc_root']
    excluded = set(config['excluded_dirs'])
    skip_dirs = set(config['skip_dirs'])
    specs = []
    for entry in sorted(os.listdir(prc_root)):
        path = os.path.join(prc_root, entry)
        if not os.path.isdir(path) or entry in excluded or entry.startswith('.'):
            continue
        files = iter_files(path, skip_dirs)
        ifos = find_module_ifos(path, skip_dirs)
        specs.append(ModuleSpec(path, entry, slugify(entry), None, files, ifos))
    return specs


def tlk_search_paths(config, module_dir):
    paths = []
    for pat in config['tlk_search_paths']:
        p = pat.replace('{module_dir}', module_dir).replace('{prc_root}', config['prc_root'])
        if not os.path.isabs(p):
            p = os.path.join(config['prc_root'], p)
        paths.append(p)
    # the module's own subdirs (custom tlks often sit next to the ifo)
    paths.insert(0, os.path.join(module_dir, '_module', 'tlk'))
    paths.insert(0, os.path.join(module_dir, '_content', 'tlk'))
    paths.insert(0, os.path.join(module_dir, 'src', 'module', 'tlk'))
    return paths
