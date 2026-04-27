#!/usr/bin/env python3
"""Fetch geopolitical news from NewsAPI and write feed.json to repo root."""
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime, timezone

NEWS_API_KEY = os.environ.get('NEWS_API_KEY', '')
if not NEWS_API_KEY:
    print('ERROR: NEWS_API_KEY secret is not set', file=sys.stderr)
    sys.exit(1)

QUERY = (
    'war OR military OR sanctions OR coup OR nuclear OR geopolitics '
    'OR ukraine OR taiwan OR iran OR israel OR nato OR conflict'
)

params = urllib.parse.urlencode({
    'q': QUERY,
    'language': 'en',
    'sortBy': 'publishedAt',
    'pageSize': 30,
    'apiKey': NEWS_API_KEY,
})

try:
    req = urllib.request.Request(
        f'https://newsapi.org/v2/everything?{params}',
        headers={'User-Agent': 'GeoLens/1.0'},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
except Exception as e:
    print(f'Fetch error: {e}', file=sys.stderr)
    sys.exit(1)

if data.get('status') != 'ok':
    print(f'API error: {data.get("message")}', file=sys.stderr)
    sys.exit(1)

REGIONS = {
    'EU-EAST': [
        'ukraine', 'russia', 'kyiv', 'moscow', 'nato', 'poland', 'belarus',
        'donetsk', 'crimea', 'moldova', 'zelensky', 'putin', 'zaporizhzhia',
        'kharkiv', 'finland nato', 'sweden nato', 'baltics',
    ],
    'MENA': [
        'iran', 'israel', 'gaza', 'hamas', 'hezbollah', 'saudi', 'yemen',
        'houthi', 'iraq', 'syria', 'lebanon', 'middle east', 'persian gulf',
        'hormuz', 'irgc', 'netanyahu', 'rafah', 'west bank', 'sinai',
    ],
    'INDO-PAC': [
        'china', 'taiwan', 'japan', 'south korea', 'north korea', 'philippines',
        'south china sea', 'indo-pacific', 'asean', 'pla', 'tsmc',
        'semiconductor', 'xi jinping', 'myanmar', 'indonesia', 'strait',
    ],
    'AFRICA': [
        'niger', 'mali', 'sahel', 'sudan', 'ethiopia', 'congo', 'nigeria',
        'kenya', 'libya', 'burkina faso', 'somalia', 'mozambique', 'zimbabwe',
        'wagner', 'al-shabaab', 'africa coup',
    ],
    'AMERICAS': [
        'mexico cartel', 'brazil', 'colombia', 'venezuela', 'haiti', 'cuba',
        'latin america', 'us mexico border', 'narco', 'maduro',
    ],
}

def classify_region(text):
    t = text.lower()
    for region, keywords in REGIONS.items():
        if any(kw in t for kw in keywords):
            return region
    return 'GLOBAL'

def classify_severity(text):
    t = text.lower()
    if any(w in t for w in [
        'killed', 'dead', 'attack', 'strike', 'bombing', 'missile',
        'war', 'invasion', 'coup', 'nuclear', 'explosion', 'casualties',
        'airstrike', 'drone strike',
    ]):
        return 'high'
    if any(w in t for w in [
        'military', 'sanctions', 'crisis', 'conflict', 'tensions',
        'threat', 'warning', 'troops', 'escalat', 'arrest', 'protest',
    ]):
        return 'med'
    return 'low'

def classify_type(text):
    t = text.lower()
    if any(w in t for w in [
        'attack', 'strike', 'bomb', 'missile', 'drone attack',
        'combat', 'killed', 'fighting', 'airstrike',
    ]):
        return 'KINETIC'
    if any(w in t for w in [
        'oil', 'gas', 'energy', 'uranium', 'grain', 'wheat',
        'food security', 'mineral', 'lithium', 'resource',
    ]):
        return 'RESOURCE'
    if any(w in t for w in [
        'troops', 'navy', 'army', 'air force', 'military exercise',
        'weapons', 'arsenal', 'deployment', 'warship', 'regiment',
    ]):
        return 'MIL'
    if any(w in t for w in [
        'economy', 'financial', 'market', 'trade', 'currency',
        'inflation', 'gdp', 'tariff', 'imf', 'sanction', 'bank',
    ]):
        return 'FIN'
    if any(w in t for w in [
        'infrastructure', 'pipeline', 'grid', 'port', 'power plant', 'railway',
    ]):
        return 'INFRA'
    return 'DIPLO'

items = []
seen = set()

for a in data.get('articles', []):
    title = (a.get('title') or '').strip()
    if not title or '[Removed]' in title or title.lower() in seen:
        continue
    seen.add(title.lower())

    desc = (a.get('description') or '').strip()[:300]
    combined = f'{title} {desc}'

    published = a.get('publishedAt', '')
    try:
        dt = datetime.fromisoformat(published.replace('Z', '+00:00'))
        time_str = dt.strftime('%H:%M')
    except Exception:
        time_str = '--:--'

    region = classify_region(combined)
    items.append({
        'time': time_str,
        'region': region,
        'sev': classify_severity(combined),
        'type': classify_type(combined),
        'title': title[:120],
        'src': a.get('source', {}).get('name', 'Unknown'),
        'desc': desc,
        'url': a.get('url', ''),
        'filter': region,
    })

    if len(items) >= 20:
        break

out = {
    'updated': datetime.now(timezone.utc).isoformat(),
    'items': items,
}

repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
out_path = os.path.join(repo_root, 'feed.json')

with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print(f'Wrote {len(items)} items to feed.json')
