import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.event_manager import EventManager
from services.task_manager import TaskManager
from services.automation import analyze_calendar_for_tasks
import datetime

async def run_test():
    print("--- Démarrage du test pour la logique Orpheline ---")
    tm = TaskManager.instance()
    em = EventManager.instance()
    
    # 1. Clean existing state for testing
    for t in tm.get_all_tasks():
        tm.delete_task(t["id"])
    for e in em.get_all_events():
        em.delete_event(e.id)
        
    print("État initial nettoyé.")

    # 2. Créer un événement localement pour simuler la base de données NovaFlow
    now = datetime.datetime.now()
    event_time = now + datetime.timedelta(hours=2)
    now_iso = now.isoformat()
    event_iso = event_time.isoformat()
    
    test_event = em.create_event(
        external_id="test_ext_123",
        source="google_calendar",
        title="Événement Test",
        start=event_iso,
        updated=event_iso,
        desc_hash="123"
    )
    print(f"Événement NovaFlow créé avec ID interne: {test_event.id}")

    # 3. Créer une tâche externe liée à cet événement
    test_task = tm.add_task(
        title="Acheter du lait",
        parent_event_id=test_event.id,
        source="google_tasks",
        external_id="ext_task_123"
    )
    print(f"Tâche associée à l'événement: {test_task['title']} (Parent: {test_task['parent_event_id']})")
    
    # Validation du setup
    assert tm.get_task_object(test_task["id"]).parent_event_id == test_event.id, "Setup Échec: le parent n'est pas lié"

    # --- SIMULATION 1 : SUPPRESSION D'UN ÉVÈNEMENT ---
    print("\n--- TEST 1: Suppression d'événement ---")
    
    # Mocker l'API AI pour ne pas consommer de crédits
    from unittest.mock import patch
    with patch('services.automation.chat') as mock_chat:
        # L'IA va proposer de ne pas lier la tâche
        mock_chat.return_value = '{"reasoning": "Test mockup", "action": "none"}'
        
        # On simule un retour de google calendar VIDE (donc l'event a été supprimé)
        test_events_from_google = []
        
        await analyze_calendar_for_tasks(events=test_events_from_google, source="google_calendar")
        
        # Vérification: l'événement doit être supprimé
        assert em.get_event(test_event.id) is None, "L'événement n'a pas été supprimé"
        print("✅ Événement supprimé de la BD.")
        
        # Vérification: la tâche doit être désolidarisée
        updated_task = tm.get_task_object(test_task["id"])
        if updated_task.parent_event_id is None:
            print("✅ Tâche correctement désolidarisée (parent_event_id = None).")
        else:
            print(f"❌ Échec de désolidarisation. Parent: {updated_task.parent_event_id}")
            
        # L'IA a du être appelée (1 fois pour la tâche orpheline)
        if mock_chat.called:
            print("✅ L'IA a été appelée pour ré-analyser la tâche orpheline.")
        else:
            print("❌ L'IA n'a pas été appelée.")


    # --- SIMULATION 2 : CRÉATION D'UN NOUVEL ÉVÈNEMENT ---
    print("\n--- TEST 2: Création d'un nouvel événement ---")
    
    with patch('services.automation.chat') as mock_chat:
        # L'IA va proposer de lier la tâche orpheline existante au nouvel événement
        # Pour ce mock, on lui dit action="link" et on donne l'ID externe du mock de calendrier
        # On va créer le mock google data
        new_google_event = {
            "id": "new_google_ext_789",
            "title": "Supermarché",
            "start": now_iso,
            "description": "Faire les courses"
        }
        
        # Attention: la logique d'assignation dans analyze_and_link_tasks utilise les index "1", "2"
        # On va donc mocker le payload de retour
        mock_chat.return_value = '{"reasoning": "Mockup link", "action": "link", "event_id": "1"}'
        
        # The AI triggers on event addition
        await analyze_calendar_for_tasks(events=[new_google_event], source="google_calendar")
        
        # Vérifier si l'event a été inséré
        nf_new_evt = em.get_event_by_external_id("new_google_ext_789", "google_calendar")
        
        if nf_new_evt:
            print("✅ Nouvel événement inséré en BD.")
            
            # Vérifier si la tâche a été linkée à cause de mock_chat
            updated_task2 = tm.get_task_object(test_task["id"])
            if updated_task2.parent_event_id == nf_new_evt.id:
                 print("✅ Tâche orpheline correctement linkée au nouvel événement !")
            else:
                 print(f"❌ La tâche est toujours orpheline ou mal liée. Parent = {updated_task2.parent_event_id}")
                 
        else:
            print("❌ Le nouvel événement n'a pas été inséré.")
            
        if mock_chat.call_count > 0:
            print("✅ L'IA a été appelée pour analyser les tâches orphelines.")
        else:
            print("❌ L'IA n'a pas été appelée sur le nouvel event.")

    print("\nTests terminés !")

if __name__ == "__main__":
    asyncio.run(run_test())
