# Tunarr channel images

Original channel icons exported from Tunarr. `channels.json` records each
channel's UUID, number, name, icon settings, original upload URL, local image
filename, and SHA-256 checksum. Sitcoms and Sitcoms 2 share `sitcoms.png`.

Tunarr uses public URLs with this format:

```text
https://raw.githubusercontent.com/marklester/lesterlab/master/images/tunarr/cartoons.png
```

Keep these files in regular Git so the URLs return image bytes. Publish new
images before changing the corresponding URL in Tunarr. Changing a filename
also requires updating `channels.json` and the live channel's `icon.path`.

To restore the icon settings from this directory, run the following from the
repository root after the images have been pushed. It fetches each channel's
current settings and replaces only its icon settings. It does not create
missing channels; if a channel has been recreated, update its UUID in the
manifest first.

```bash
python3 - <<'PY'
import json
import sys
from pathlib import Path

sys.path.insert(0, '.agents/skills/tunarr/scripts')
from tunarr_cli.client import TunarrClient

client = TunarrClient('http://tunarr.home')
for entry in json.loads(Path('images/tunarr/channels.json').read_text()):
    channel = client.get(f"channels/{entry['id']}")
    if channel['icon'] == entry['icon']:
        continue
    channel['icon'] = entry['icon']
    for key in ('fallback', 'programCount', 'transcoding', 'sessions'):
        channel.pop(key, None)
    if channel.get('watermark') is None:
        channel.pop('watermark', None)
    client.request('PUT', f"channels/{entry['id']}", channel)
    print(f"Updated {entry['number']}: {entry['name']}")
PY
```

GitHub documents [raw repository URLs](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits#text-limits).
Unauthenticated raw downloads are subject to
[rate limits](https://github.blog/changelog/2025-05-08-updated-rate-limits-for-unauthenticated-requests/).
