import asyncio
import os
import sys

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.event_manager import EventManager
from services.task_manager import TaskManager
from main import app
import datetime

async def test_update_delete_logic():
    print("--- Démarrage du test pour la suppression d' इवेंट liée aux tâches ---")
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
    
    # Évènement IA
    ai_event = em.create_event(
        external_id="ai_ext_123",
        source="ai_task",
        title="Rendez-vous AI",
        start=event_iso,
        updated=event_iso,
        desc_hash="123"
    )
    
    # Évènement NON IA
    google_event = em.create_event(
        external_id="google_ext_456",
        source="google_calendar",
        title="Fête Normale",
        start=event_iso,
        updated=event_iso,
        desc_hash="456"
    )

    print(f"Événement IA créé: {ai_event.id}")
    print(f"Événement Google créé: {google_event.id}")

    # 3. Créer une tâche externe liée à chaque événement
    task_ai = tm.add_task(
        title="Tâche AI",
        parent_event_id=ai_event.id,
        source="google_tasks",
        external_id="ext_task_ai"
    )
    
    task_google = tm.add_task(
        title="Tâche Google",
        parent_event_id=google_event.id,
        source="google_tasks",
        external_id="ext_task_google"
    )
    
    # On importe update_existing_task et remove_task
    from main import remove_task, update_existing_task
    from fastapi import BackgroundTasks
    
    # Mocking BackgroundTasks
    class MockBgTasks:
        def __init__(self):
            self.tasks = []
        def add_task(self, func, *args, **kwargs):
            self.tasks.append((func, args, kwargs))
            print(f"MockBgTasks: Task {func.__name__} added.")

    mock_bg = MockBgTasks()

    # --- SIMULATION 1 : SUPPRESSION d'une tâche liée à un event NON IA ---
    print("\n--- TEST 1: Suppression d'une tâche liée à un event Google ---")
    remove_task(task_google["id"])
    
    if em.get_event(google_event.id):
        print("✅ L'événement Google n'a pas été supprimé (comportement attendu).")
    else:
        print("❌ L'événement Google a été supprimé !")

    # --- SIMULATION 2 : SUPPRESSION d'une tâche liée à un event IA ---
    print("\n--- TEST 2: Suppression d'une tâche liée à un event IA ---")
    remove_task(task_ai["id"])
    
    if em.get_event(ai_event.id) is None:
        print("✅ L'événement IA a été supprimé car il est vide !")
    else:
        print("❌ L'événement IA n'a pas été supprimé !")

    # --- SIMULATION 3 : MODIFICATION d'une tâche liée à un event IA ---
    print("\n--- TEST 3: Modification d'une tâche liée à un event IA ---")
    
    ai_event_2 = em.create_event(
        external_id="ai_ext_789",
        source="ai_task",
        title="Rendez-vous AI 2",
        start=event_iso,
        updated=event_iso,
        desc_hash="789"
    )
    
    task_ai_2 = tm.add_task(
        title="Tâche AI 2",
        parent_event_id=ai_event_2.id,
        source="google_tasks",
        external_id="ext_task_ai_2"
    )
    
    # Modif update
    await update_existing_task(task_ai_2["id"], {"title": "Nouveau Titre AI"}, mock_bg)
    
    if em.get_event(ai_event_2.id) is None:
        print("✅ L'événement IA 2 a été supprimé suite à la modif !")
    else:
        print("❌ L'événement IA 2 n'a pas été supprimé lors de la modif !")
        
    updated_t2 = tm.get_task_object(task_ai_2["id"])
    if updated_t2.parent_event_id is None:
        print("✅ La tâche est bien désolidarisée de son ancien event IA.")
    else:
        print("❌ La tâche a gardé l'ancien event IA.")
        
    if any(f.__name__ == 'analyze_and_link_tasks' for f, a, kw in mock_bg.tasks):
        print("✅ L'analyse IA en background a été déclenchée pour la tâche modifiée.")
    else:
        print("❌ L'analyse IA n'a pas été déclenchée.")
        

    print("\nTests terminés !")

if __name__ == "__main__":
    asyncio.run(test_update_delete_logic())
