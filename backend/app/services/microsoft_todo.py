from datetime import datetime, timezone
import requests
from app.services.calendar_sync.microsoft_auth import MicrosoftAuthService

def get_todo_tasks(limit: int = 50) -> list:
    """
    Récupère les tâches Microsoft To Do via Graph API.
    Itère sur toutes les listes de tâches (pas seulement 'Tasks').
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
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            # 1. Lister toutes les listes de tâches
            lists_url = "https://graph.microsoft.com/v1.0/me/todo/lists"
            lists_response = requests.get(lists_url, headers=headers)
            
            if lists_response.status_code != 200:
                print(f"❌ Erreur Graph API To Do Lists pour {email}: {lists_response.status_code}")
                continue
            
            task_lists = lists_response.json().get("value", [])
            
            for task_list in task_lists:
                list_id = task_list.get("id")
                list_name = task_list.get("displayName", "Sans titre")
                
                # 2. Récupérer les tâches de chaque liste
                url = (
                    f"https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks"
                    f"?$top={limit}"
                    f"&$filter=status ne 'completed'"
                    f"&$select=id,title,status,importance,body,createdDateTime,dueDateTime,webLink"
                )
                
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    print(f"❌ Erreur Graph API To Do pour {email}, liste '{list_name}': {response.status_code}")
                    continue
                    
                data = response.json()
                items = data.get("value", [])
                
                for item in items:
                    # Mapping priorité
                    priority = "medium"
                    if item.get("importance") == "high":
                        priority = "high"
                    elif item.get("importance") == "low":
                        priority = "low"
                    
                    # Mapping statut
                    is_done = item.get("status") == "completed"
                    
                    # Mapping date d'échéance (dueDateTime est un objet {dateTime, timeZone})
                    due_date_obj = item.get("dueDateTime")
                    due_date = due_date_obj.get("dateTime") if due_date_obj else None

                    task_dict = {
                        "id": item["id"],  # On garde l'ID Microsoft (sera utilisé comme external_id)
                        "title": item.get("title") or "Sans titre",
                        "priority": priority,
                        "meta": f"Microsoft To Do - Liste: {list_name}",
                        "done": is_done,
                        "parent_event_id": None,
                        "created_at": item.get("createdDateTime", datetime.now(timezone.utc).isoformat()),
                        "source": "microsoft_todo",
                        "link": item.get("webLink", ""),
                        "description": item.get("body", {}).get("content", ""),
                        "due_date": due_date
                    }
                    
                    all_tasks.append(task_dict)
                
        except Exception as e:
            print(f"❌ Exception lors de la récupération des tâches To Do pour {email}: {e}")
            
    return all_tasks

