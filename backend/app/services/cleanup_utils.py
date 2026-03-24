import os
import json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def reset_all_data():
    """Efface les tâches, l'historique de traitement et les notifications."""
    files_to_reset = {
        "tasks.json": [],
        "notifications.json": [],
        "processed_items.json": {"documents": [], "events": {}},
        "events.json": {},
        "event_metadata.json": {},
        "moodle_ext_events.json": [],
        "moodle_ext_courses.json": [],
        "moodle_ext_downloaded_keys.json": []
    }
    
    results = {}
    
    for filename, empty_value in files_to_reset.items():
        filepath = os.path.join(DATA_DIR, filename)
        # On force la création si n'existe pas, ou on écrase
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(empty_value, f, indent=2)
            results[filename] = "Reset"
        except Exception as e:
            results[filename] = f"Error: {e}"
    
    # Recharger les singletons pour qu'ils reflètent l'état post-reset
    try:
        from app.services.task_manager import TaskManager
        TaskManager.instance().reload()
    except Exception as e:
        results["TaskManager.reload"] = f"Error: {e}"

    try:
        from app.services.event_manager import EventManager
        EventManager.instance().reload()
    except Exception as e:
        results["EventManager.reload"] = f"Error: {e}"

    try:
        from app.services.notification_manager import NotificationManager
        NotificationManager.instance().reload()
    except Exception as e:
        results["NotificationManager.reload"] = f"Error: {e}"
            
    return results
