#!/usr/bin/env bash
# Deploy the index to production: https://raptio.us/monster_index/
# (rsyncs to the nwserver box behind the raptio.us edge; run after regenerating data/)
set -euo pipefail
cd "$(dirname "$0")"

DEST=42.80.0.22:/var/www/html/monster_index

# no trailing slash on data — it must land as a subdirectory, not flatten.
# --delete keeps stale files from accumulating (including the flattened
# jsons from the first deploy). data/portraits is generated content
# (generator/portraits.py) and syncs like everything else.
rsync -r --delete index.html data "$DEST/"

echo "deployed -> https://raptio.us/monster_index/"
