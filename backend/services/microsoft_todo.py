from datetime import datetime, timezone
import requests
from services.microsoft_auth import MicrosoftAuthService

def get_todo_tasks(limit: int = 50) -> list:
    """
    Récupère les tâches Microsoft To Do via Graph API.
    Utilise la liste par défaut 'Tasks'.
    """
    ms_auth = MicrosoftAuthService()
    accounts = MicrosoftAuthService.list_connected_accounts()
    
    all_tasks = []

    for email in accounts:
        # Utiliser la méthode robuste qui gère le refresh token
        token_data = ms_auth.get_token_for_email(email)
        if not token_data or "access_token" not in token_data:
            print(f"⚠️ Pas de token valide pour {email}, skip.")
            continue
        
        access_token = token_data["access_token"]
        
        try:
            # Récupérer les tâches de la liste par défaut ('Tasks')
            # Note: Pour l'instant on hardcode la liste 'Tasks', 
            # mais l'API permet de lister toutes les listes via /me/todo/lists
            url = (
                f"https://graph.microsoft.com/v1.0/me/todo/lists/Tasks/tasks"
                f"?$top={limit}"
                f"&$filter=status ne 'completed'"  # On ne veut que les tâches non terminées
                f"&$select=id,title,status,importance,body,createdDateTime,dueDateTime,webLink"
            )
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Erreur Graph API To Do pour {email}: {response.status_code}")
                continue
                
            data = response.json()
            items = data.get("value", [])
            
            for item in items:
                # Mapper vers le format NovaFlow Task (dict)
                # Structure attendue par TaskManager / Frontend :
                # {
                #   "id": str,
                #   "title": str,
                #   "priority": "high"|"medium"|"low",
                #   "meta": str (contexte),
                #   "done": bool,
                #   "parent_event_id": str (optionnel),
                #   "created_at": str (iso),
                #   "source": "microsoft_todo",
                #   "link": str (webLink)
                # }
                
                # Mapping priorité
                priority = "medium"
                if item.get("importance") == "high":
                    priority = "high"
                elif item.get("importance") == "low":
                    priority = "low"
                
                # Mapping statut
                is_done = item.get("status") == "completed"
                
                task_dict = {
                    "id": item["id"],  # On garde l'ID Microsoft (sera utilisé comme external_id)
                    "title": item.get("title") or "Sans titre",
                    "priority": priority,
                    "meta": "Microsoft To Do",
                    "done": is_done,
                    "parent_event_id": None,
                    "created_at": item.get("createdDateTime", datetime.now(timezone.utc).isoformat()),
                    "source": "microsoft_todo",
                    "link": item.get("webLink", ""),
                    "description": item.get("body", {}).get("content", "")
                }
                
                all_tasks.append(task_dict)
                
        except Exception as e:
            print(f"❌ Exception lors de la récupération des tâches To Do pour {email}: {e}")
            
    return all_tasks
