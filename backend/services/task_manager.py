"""
NovaFlow - Service Task Manager

Gère le stockage et la manipulation des tâches (Todo List).
Stockage simple dans un fichier JSON pour la persistance locale.
"""

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

# Chemin du fichier de données
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TASKS_FILE = os.path.join(DATA_DIR, "tasks.json")


def _ensure_data_dir():
    """Vérifie que le dossier data existe."""
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_tasks() -> List[Dict[str, Any]]:
    """Charge les tâches depuis le fichier JSON."""
    if not os.path.exists(TASKS_FILE):
        return []
    
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_tasks(tasks: List[Dict[str, Any]]):
    """Sauvegarde les tâches dans le fichier JSON."""
    _ensure_data_dir()
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def get_tasks() -> List[Dict[str, Any]]:
    """Récupère toutes les tâches."""
    return _load_tasks()


def add_task(title: str, priority: str = "medium", meta: str = "NovaFlow") -> Dict[str, Any]:
    """
    Crée une nouvelle tâche.
    
    Args:
        title: Le titre de la tâche.
        priority: Priorité ('high', 'medium', 'low').
        meta: Métadonnées ou catégorie.
    
    Returns:
        La tâche créée.
    """
    tasks = _load_tasks()
    
    # DEDUPLICATION: Vérifier si une tâche identique existe déjà et n'est pas terminée
    for task in tasks:
        if task["title"] == title and task["meta"] == meta and not task["done"]:
            return task
    
    new_task = {
        "id": str(uuid.uuid4()),
        "title": title,
        "priority": priority,
        "meta": meta,
        "done": False,
        "created_at": datetime.now().isoformat(),
    }
    
    tasks.insert(0, new_task)  # Ajouter au début
    _save_tasks(tasks)
    return new_task


def update_task(task_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Met à jour une tâche existante.
    
    Args:
        task_id: ID de la tâche à modifier.
        updates: Dictionnaire des champs à modifier (ex: {"done": True}).
        
    Returns:
        La tâche mise à jour ou None si non trouvée.
    """
    tasks = _load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task.update(updates)
            _save_tasks(tasks)
            return task
    return None


def delete_task(task_id: str) -> bool:
    """
    Supprime une tâche.
    
    Returns:
        True si supprimée, False si non trouvée.
    """
    tasks = _load_tasks()
    initial_len = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]
    
    if len(tasks) < initial_len:
        _save_tasks(tasks)
        return True
    return False


def toggle_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Inverse le statut 'done' d'une tâche."""
    tasks = _load_tasks()
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = not task["done"]
            _save_tasks(tasks)
            return task
    return None
