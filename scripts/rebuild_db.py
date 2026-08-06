import os
import json
import re

DATA_DIR = "/media/vpsg24gb/DATA/o9o/data"
BASE_DIR = "/media/vpsg24gb/DATA/o9o"

GRADE_MAPPING = {
    'k4': 'K4 (Age 4)',
    'k5': 'K5 (Age 5)',
    'g1': 'Grade 1',
    'g2': 'Grade 2',
    'g3': 'Grade 3',
    'g4': 'Grade 4',
    'g5': 'Grade 5',
    'g6': 'Grade 6',
    'g7': 'Grade 7',
    'g8': 'Grade 8',
    'g9': 'Grade 9',
    'g10': 'Grade 10',
    'g11': 'Grade 11',
    'g12': 'Grade 12',
}

def sanitize_filename(name):
    # Same logic as in step1_direct_stream.py if possible, usually just replace / or : 
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

for folder in os.listdir(DATA_DIR):
    folder_path = os.path.join(DATA_DIR, folder)
    if not os.path.isdir(folder_path): continue
    if folder not in GRADE_MAPPING: continue
    
    actual_g_name = GRADE_MAPPING[folder]
    db_file = os.path.join(BASE_DIR, f"database_{actual_g_name}.json")
    
    db = []
    
    for f in os.listdir(folder_path):
        if not f.endswith(".json"): continue
        day_match = re.search(r'-(\d{3})\.json$', f)
        if not day_match: continue
        day = day_match.group(1)
        
        json_path = os.path.join(folder_path, f)
        with open(json_path, 'r', encoding='utf-8') as jf:
            try:
                playlist = json.load(jf)
            except Exception:
                continue
                
        for item in playlist:
            subject = sanitize_filename(item.get("title", ""))
            
            link = f"{actual_g_name}/Ngày {day}/{subject}/{actual_g_name} - {day} - {subject}.mp4"
            
            db.append({
                "grade": actual_g_name,
                "day": day,
                "subject": subject,
                "link": link
            })
            
    if db:
        print(f"Saving {len(db)} records to {db_file}")
        with open(db_file, 'w', encoding='utf-8') as outf:
            json.dump(db, outf, ensure_ascii=False, indent=4)
