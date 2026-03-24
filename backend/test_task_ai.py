import asyncio
import os
import sys
import datetime
import time
import json

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from services.automation import analyze_and_link_tasks
from services.event_manager import EventManager
from services.task_manager import TaskManager

async def test_ai_advanced():
    print("🧹 Nettoyage des événements et tâches de test existants...")
    evt_m = EventManager.instance()
    tm = TaskManager.instance()
    
    # Clean previous test entities
    all_tasks = tm.get_all_tasks()
    for t in list(all_tasks):
        if t.get("source") == "test_script":
            tm.delete_task(t["id"])
            
    all_events = evt_m.get_all_events()
    for e in list(all_events):
        if e.source == "local_test" or (e.source == "ai_task" and getattr(e, "external_id", "").startswith("t_")):
            # Note: ai_tasks created during tests use the task id prefix "t_"
            evt_m.delete_event(e.id)
            
    # Force nettoyage brutal si ça accumule trop (failsafe manuel)
    for e in list(evt_m.get_all_events()):
         if e.title in ["Préparation de ski", "Test Vol pour Londres BA74", "Test rendez-vous chez le kiné", "Rendez-vous chez le kiné", "Essayer au parc"]:
             evt_m.delete_event(e.id)
    
    now = datetime.datetime.now()
    d1 = (now + datetime.timedelta(days=1)).isoformat()
    d2 = (now + datetime.timedelta(days=2)).isoformat()
    d3 = (now + datetime.timedelta(days=3)).isoformat()
    d4 = (now + datetime.timedelta(days=4)).isoformat()
    d5 = (now + datetime.timedelta(days=5)).isoformat()
    d8 = (now + datetime.timedelta(days=8)).isoformat()
    d10 = (now + datetime.timedelta(days=10)).isoformat()
    
    timestamp = str(int(time.time()))
    
    # --- Création d'événements mockés (Basés sur les vraies données) ---
    mock_events = [
        {"id": f"evt_ski_{timestamp}", "title": "Ski Bromont", "date": d2},
        {"id": f"evt_fete_{timestamp}", "title": "Fête Alexis / Joyeux anniversaire !", "date": d5},
        {"id": f"evt_moodle1_{timestamp}", "title": "Mécanique Quantique (PHY321)", "date": d10},
        {"id": f"evt_cardio_{timestamp}", "title": "Rendez-vous cardiologue", "date": d2},
        {"id": f"evt_ete_{timestamp}", "title": "Heure d'été", "date": d3},
        {"id": f"evt_reunion_{timestamp}", "title": "Réunion budgétaire Q3", "date": d3},
    ]
    
    for e in mock_events:
        evt_m.create_event(
            external_id=e["id"], source="local_test",
            title=e["title"], start=e["date"], updated=e["date"], desc_hash="hash"
        )
    
    # --- Création de tâches mockées avec résultat ATTENDU ---
    # Format: dict with task details + "expected_action" (link, create, none) + "expected_target" (substring of event title for link)
    mock_tasks = [
        # --- LINK ATTENDU ---
        {
            "task": {"id": f"t_1_{timestamp}", "title": "Préparer le stock de ski", "desc": "Pour en fin de semaine", "due": d1},
            "expected_action": "link", "expected_target": "Ski"
        },
        {
            "task": {"id": f"t_2_{timestamp}", "title": "Acheter le gateau", "desc": "Chocolat", "due": d4},
            "expected_action": "link", "expected_target": "Fête"
        },
        {
            "task": {"id": f"t_3_{timestamp}", "title": "Devoir de mécanique quantique", "desc": "Exercices 1 à 4", "due": d10},
            "expected_action": "link", "expected_target": "Mécanique"
        },
        {
            "task": {"id": f"t_4_{timestamp}", "title": "Faire un backflip sur la neige", "desc": "Essayer au parc", "due": d2},
            "expected_action": "link", "expected_target": "Ski"
        },
        
        # --- CREATE ATTENDU ---
        {
            "task": {"id": f"t_5_{timestamp}", "title": "Test rendez-vous chez le kiné", "desc": "Première séance pour l'épaule", "due": d4},
            "expected_action": "create", "expected_target": "kiné"
        },
        {
            "task": {"id": f"t_6_{timestamp}", "title": "Test Vol pour Londres BA74", "desc": "Départ terminal 1", "due": d8},
            "expected_action": "create", "expected_target": "Londres"
        },
        {
            "task": {"id": f"t_7_{timestamp}", "title": "Test Remise projet final Design", "desc": "Document PDF sur Moodle", "due": d5},
            "expected_action": "create", "expected_target": "Design"
        },
        
        # --- NONE ATTENDU ---
        {
            "task": {"id": f"t_8_{timestamp}", "title": "Faire le ménage de la chambre", "desc": "Passer l'aspirateur", "due": d1},
            "expected_action": "none", "expected_target": ""
        },
        {
            "task": {"id": f"t_9_{timestamp}", "title": "Appeler maman", "desc": "Pour prendre des nouvelles", "due": d2},
            "expected_action": "none", "expected_target": ""
        },
        {
            "task": {"id": f"t_10_{timestamp}", "title": "Faire la vaisselle", "desc": "", "due": None},
            "expected_action": "none", "expected_target": ""
        },
        
        # --- PIÈGES (Doit éviter link abusif) ---
        {
            "task": {"id": f"t_11_{timestamp}", "title": "Acheter des chaussettes de plage", "desc": "Pour l'été", "due": d1},
            # Should NOT link to "Heure d'été" event, it's just a holiday name
            "expected_action": "none", "expected_target": ""
        },
    ]
    
    actual_tasks = []
    for mt in mock_tasks:
        t = mt["task"]
        result = tm.add_task(
            title=t["title"], meta="Test", external_id=t["id"], source="test_script", due_date=t["due"]
        )
        # CRUCIAL: Add description to mimic the API behavior fixes
        result["description"] = t["desc"]
        
        # Store expected behavior in the object for testing later (won't be seen by AI)
        result["_expected_action"] = mt["expected_action"]
        result["_expected_target"] = mt["expected_target"]
        
        actual_tasks.append(result)
        
    print(f"--- Lancement de l'analyse IA sur {len(actual_tasks)} tâches (avec {len(mock_events)} événements contextuels) ---")
    await analyze_and_link_tasks(actual_tasks)
    
    print("\n--- RÉSULTATS ET SCORING ---")
    tm.reload()
    
    score = 0
    total = len(mock_tasks)
    
    for t in actual_tasks:
        found = tm.get_task_object(t["id"])
        if found:
            actual_action = "none"
            actual_target_title = ""
            
            if found.parent_event_id:
                # Resolve event
                evt = evt_m.get_event(found.parent_event_id)
                if not evt:
                    for e in evt_m.get_all_events():
                        if e.external_id == found.parent_event_id:
                            evt = e
                            break
                
                if evt:
                    if evt.source == "ai_task":
                        actual_action = "create"
                        actual_target_title = evt.title
                    else:
                        actual_action = "link"
                        actual_target_title = evt.title
            
            # Vérifications
            expected_action = t["_expected_action"]
            expected_target = t["_expected_target"]
            
            success = False
            if actual_action == expected_action:
                if expected_action == "none":
                    success = True
                else:
                    # Pour link et create, vérifier que la cible est bonne via substring
                    if expected_target.lower() in actual_target_title.lower():
                        success = True
                        
            if success:
                score += 1
                status = "✅ SUCCÈS"
            else:
                status = f"❌ ÉCHEC (Attendu: {expected_action} '{expected_target}')"
                
            print(f"[{status}] {t['title'][:30]:<30} => {actual_action.upper()} {actual_target_title}")

    precision = (score / total) * 100
    print(f"\nScore final : {score}/{total} ({precision:.1f}%)")
    
    if precision >= 80:
        print("🟢 Le modèle performe très bien (>80%).")
    elif precision >= 60:
        print("🟡 Le modèle donne des résultats acceptables, mais améliorables.")
    else:
        print("🔴 Le modèle échoue à classifier correctement. Régression possible.")

if __name__ == "__main__":
    asyncio.run(test_ai_advanced())
