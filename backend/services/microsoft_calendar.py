"""
NovaFlow - Service Microsoft Calendar (Outlook)

Récupère les événements Outlook via Microsoft Graph API
en utilisant les tokens d'authentification stockés.
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from services.microsoft_auth import MicrosoftAuthService, TOKENS_DIR


def _get_access_token(email: str) -> Optional[str]:
    """Récupère l'access token pour un compte Microsoft."""
    auth_service = MicrosoftAuthService()
    token_data = auth_service.get_token_for_email(email)
    if not token_data:
        return None
    
    access_token = token_data.get("access_token")
    
    # Tentative de refresh si le token a expiré
    if not access_token:
        return None
    
    # Vérifier si le token est expiré et tenter un refresh
    expires_in = token_data.get("expires_in")
    token_acquired_at = token_data.get("token_acquired_at")
    
    # Si on a un refresh_token, on peut tenter de rafraîchir
    refresh_token = token_data.get("refresh_token")
    if refresh_token:
        try:
            result = auth_service.app.acquire_token_by_refresh_token(
                refresh_token,
                scopes=auth_service.scopes
            )
            if "access_token" in result:
                # Sauvegarder le nouveau token
                result["email"] = email
                auth_service._save_token(email, result)
                return result["access_token"]
        except Exception as e:
            print(f"Erreur refresh token Microsoft pour {email}: {e}")
    
    return access_token


def get_outlook_events(days: int = 30, max_results: int = 250) -> List[Dict]:
    """
    Récupère les événements Outlook de TOUS les comptes Microsoft connectés.
    Retourne les événements dans le même format que google_service.get_upcoming_events().
    """
    accounts = MicrosoftAuthService.list_connected_accounts()
    all_events = {}  # dedup_key -> event
    
    for email in accounts:
        access_token = _get_access_token(email)
        if not access_token:
            print(f"⚠️ Pas de token valide pour {email}, skip.")
            continue
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Prefer": 'outlook.timezone="UTC"'
            }
            
            # Fenêtre temporelle - Graph API veut le format YYYY-MM-DDTHH:MM:SS sans offset
            now = datetime.now(timezone.utc)
            time_min = now.strftime("%Y-%m-%dT%H:%M:%S")
            time_max = (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")
            
            # Appel Microsoft Graph API - Calendar Events
            url = (
                f"https://graph.microsoft.com/v1.0/me/calendarView"
                f"?startDateTime={time_min}"
                f"&endDateTime={time_max}"
                f"&$top={max_results}"
                f"&$orderby=start/dateTime"
                f"&$select=id,subject,start,end,location,bodyPreview,body,isAllDay,webLink,lastModifiedDateTime,iCalUId"
            )
            
            response = requests.get(url, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ Erreur Graph API pour {email}: {response.status_code} - {response.text[:200]}")
                continue
            
            data = response.json()
            items = data.get("value", [])
            
            for item in items:
                ical_uid = item.get("iCalUId", item["id"])
                
                # Extraire les dates
                start_raw = item.get("start", {})
                end_raw = item.get("end", {})
                
                start = start_raw.get("dateTime", "")
                end = end_raw.get("dateTime", "")
                
                is_all_day = item.get("isAllDay", False)
                
                # Normaliser le format de date pour être cohérent avec Google
                if is_all_day and start:
                    # Pour les événements journée entière, on garde juste la date
                    start = start[:10]  # YYYY-MM-DD
                    end = end[:10]
                
                # Clé de déduplication similaire à Google
                clean_start = start[:19] if "T" in start else start
                dedup_key = f"outlook_{ical_uid}_{clean_start}"
                
                # Description : on prend le body text ou le bodyPreview
                description = ""
                body = item.get("body", {})
                if body.get("contentType") == "text":
                    description = body.get("content", "")
                else:
                    description = item.get("bodyPreview", "")
                
                # Location
                location = ""
                loc_data = item.get("location", {})
                if isinstance(loc_data, dict):
                    location = loc_data.get("displayName", "")
                elif isinstance(loc_data, str):
                    location = loc_data
                
                if dedup_key in all_events:
                    if email not in all_events[dedup_key]["accounts"]:
                        all_events[dedup_key]["accounts"].append(email)
                else:
                    all_events[dedup_key] = {
                        "id": dedup_key,
                        "uid": ical_uid,
                        "accounts": [email],
                        "calendar_name": "Outlook",
                        "title": item.get("subject", "Sans titre"),
                        "start": start,
                        "end": end,
                        "location": location,
                        "description": description,
                        "all_day": is_all_day,
                        "link": item.get("webLink", ""),
                        "updated": item.get("lastModifiedDateTime", ""),
                    }
                    
            print(f"✅ {len(items)} événements Outlook récupérés pour {email}")
            
        except Exception as e:
            print(f"❌ Erreur récupération Outlook pour {email}: {e}")
    
    # Convertir en liste triée
    events_list = list(all_events.values())
    events_list.sort(key=lambda x: x["start"])
    return events_list


def get_today_outlook_events() -> List[Dict]:
    """Raccourci pour les événements Outlook d'aujourd'hui."""
    return get_outlook_events(days=1, max_results=50)
