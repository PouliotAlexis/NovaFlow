
import json
import os

PROCESSED_DATA_FILE = os.path.join("backend", "data", "processed_items.json")

def reset_events_history():
    print(f"Reading {PROCESSED_DATA_FILE}...")
    if not os.path.exists(PROCESSED_DATA_FILE):
        return

    with open(PROCESSED_DATA_FILE, "r") as f:
        data = json.load(f)
    
    # Clear events to force re-processing and hashing
    count = len(data.get("events", {}))
    data["events"] = {}
    
    with open(PROCESSED_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"Cleared {count} events from history. Next sync will re-hash everything.")

if __name__ == "__main__":
    reset_events_history()
