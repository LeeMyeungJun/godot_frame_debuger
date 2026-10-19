"""Verify exported assets and produce a contact sheet from a real capture export."""
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

root = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2:
    raise SystemExit('Usage: python tests/verify_capture.py <exported-frame.html>')
html = Path(sys.argv[1])
content = html.read_text(encoding='utf-8')
data = json.loads(re.search(r'<script id="frame-data" type="application/json">(.*?)</script>', content, re.S)[1])
base = html.parent / (html.stem + '_assets')
assert data['schema_version'] == 2
assert data['draw_count'] == len(data['draws'])
references = [t[k] for d in data['draws'] for t in d['targets'] for k in ('before', 'image')]
references += [t['image'] for d in data['draws'] for t in d['textures']]
assert all((base / p).is_file() for p in references), 'Missing exported image'
changed = total = 0
targets = set()
for draw in data['draws']:
    for target in draw['targets']:
        targets.add(target['id'])
        with Image.open(base / target['before']) as before, Image.open(base / target['image']) as after:
            assert before.size == after.size
            changed += ImageChops.difference(before.convert('RGB'), after.convert('RGB')).getbbox() is not None
        total += 1

draws = data['draws']
samples = sorted({0, len(draws)//4, len(draws)//2, 3*len(draws)//4, len(draws)-2, len(draws)-1})
samples = [i for i in samples if i >= 0 and draws[i]['targets']]
sheet = Image.new('RGB', (1200, max(1, (len(samples)+1)//2) * 250), '#151922')
pen = ImageDraw.Draw(sheet)
for pos, index in enumerate(samples):
    draw = draws[index]
    target = draw['targets'][0]
    with Image.open(base / target['image']) as source:
        image = source.convert('RGB')
    image.thumbnail((590, 215))
    x, y = (pos % 2) * 600, (pos // 2) * 250
    sheet.paste(image, (x + (600-image.width)//2, y+28))
    pen.text((x+10, y+6), 'Draw {}/{} - Event {} - Target #{}'.format(index+1, len(draws), draw['event'], target['id']), fill='white')
output = root / 'output' / 'verification'
output.mkdir(parents=True, exist_ok=True)
sheet.save(output / 'draw_progression.jpg')
print('PASS: {} draws, {} before/after pairs, {} visible RGB changes, {} asset references, targets {}'.format(len(draws), total, changed, len(references), sorted(targets)))
