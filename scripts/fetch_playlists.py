#!/usr/bin/env python3
"""Fetch ALL playlists from o9o.net using only stdlib (no pip needed)."""
import urllib.request, re, json, os, time, sys

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120'}
PATTERN = re.compile(r'const playlistData = (\[.*?\]);', re.DOTALL)
BASE = "https://www.o9o.net"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

GRADES = [
    ("k4",  "2023-k4",  170), ("k5",  "2023-k5",  170),
    ("g1",  "2023-01",  170), ("g2",  "2023-02",  170),
    ("g3",  "2023-03",  170), ("g4",  "2023-04",  170),
    ("g5",  "2023-05",  170), ("g6",  "2023-06",  170),
    ("g7",  "2023-07",  170), ("g8",  "2023-08",  170),
    ("g9",  "2023-09",  170), ("g10", "2023-10",  170),
    ("g11", "2023-11",  170), ("g12", "2023-12",  170),
]

def fetch(grade, code):
    url = f"{BASE}/{grade}/?lesson={code}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8")
        m = PATTERN.search(html)
        return json.loads(m.group(1)) if m else None
    except:
        return None

total_ok = total_skip = total_err = 0
for grade, prefix, count in GRADES:
    grade_dir = os.path.join(DATA_DIR, grade)
    os.makedirs(grade_dir, exist_ok=True)
    existing = {f[:-5] for f in os.listdir(grade_dir) if f.endswith(".json")}
    print(f"\n📚 {grade}: {count} lessons ({len(existing)} cached)", flush=True)
    for i in range(1, count + 1):
        code = f"{prefix}-{i:03d}"
        if code in existing:
            total_skip += 1
            continue
        data = fetch(grade, code)
        if data:
            path = os.path.join(grade_dir, f"{code}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            total_ok += 1
            print(f"  ✅ {code} ({len(data)} videos)", flush=True)
        else:
            total_err += 1
            print(f"  ❌ {code}", flush=True)
        time.sleep(0.35)

print(f"\n🎉 Done: {total_ok} fetched, {total_skip} skipped, {total_err} errors")
