import os
import sys

# Ajouter le dossier backend au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.google_calendar import get_upcoming_events, is_connected

print("--- DEBUG CALENDAR ---")
print(f"Connected: {is_connected()}")

if is_connected():
    print("Attempting to fetch events...")
    try:
        events = get_upcoming_events(days=3)
        print(f"Success! Found {len(events)} events.")
        for e in events:
            print(f"- {e['title']} ({e['start']})")
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
else:
    print("Not connected.")
