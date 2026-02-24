import json
import os
import sys

def check_and_fix(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            json.load(f)
        # print(f"✅ OK: {path}")
    except Exception as e:
        print(f"❌ CORRUPT: {path} ({e})")
        try:
            os.remove(path)
            print(f"🗑️ DELETED: {path}")
        except Exception as del_err:
            print(f"⚠️ DELETE FAILED: {path} ({del_err})")

dirs = ["backend/data", "backend/credentials"]

print("🔍 Scanning for corrupted JSON files...")
for d in dirs:
    if os.path.exists(d):
        for root, _, files in os.walk(d):
            if "venv" in root: continue
            for f in files:
                if f.endswith(".json"):
                    check_and_fix(os.path.join(root, f))
print("🏁 Done.")
