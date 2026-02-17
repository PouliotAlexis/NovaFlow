"""
NovaFlow - Service Google (Multi-Comptes)

Gère l'authentification OAuth2, Google Calendar et Google Drive pour plusieurs comptes.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# === Configuration ===

CREDENTIALS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "credentials",
)
TOKENS_DIR = os.path.join(CREDENTIALS_DIR, "tokens")
CLIENT_SECRET_FILE = os.path.join(CREDENTIALS_DIR, "google_client_secret.json")

# Scopes étendus : Calendar, Drive, et Profil pour identifier le compte
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid"
]


# === OAuth Flow ===

def get_auth_url() -> str:
    """Génère l'URL d'autorisation Google."""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/auth/google/callback",
    )
    
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    
    return auth_url


def handle_callback(authorization_code: str) -> dict:
    """Traite le callback OAuth, identifie l'utilisateur et sauvegarde le token."""
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/auth/google/callback",
    )
    
    flow.fetch_token(code=authorization_code)
    credentials = flow.credentials
    
    # 1. Identifier l'utilisateur via l'API userinfo
    user_info_service = build("oauth2", "v2", credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    email = user_info.get("email")
    
    if not email:
        return {"status": "error", "message": "Impossible de récupérer l'email du compte."}

    # 2. Sauvegarder les tokens sous {email}.json
    token_data = {
        "email": email,
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }
    
    os.makedirs(TOKENS_DIR, exist_ok=True)
    token_file = os.path.join(TOKENS_DIR, f"{email}.json")
    
    with open(token_file, "w") as f:
        json.dump(token_data, f, indent=2, default=str)
    
    return {"status": "connected", "message": f"Compte {email} connecté avec succès !"}


def list_connected_accounts() -> List[str]:
    """Liste les emails des comptes Google connectés."""
    if not os.path.exists(TOKENS_DIR):
        return []
    
    accounts = []
    for filename in os.listdir(TOKENS_DIR):
        if filename.endswith(".json"):
            accounts.append(filename.replace(".json", ""))
    return accounts


def _get_credentials_for_email(email: str) -> Optional[Credentials]:
    """Charge les credentials pour un compte spécifique."""
    token_file = os.path.join(TOKENS_DIR, f"{email}.json")
    if not os.path.exists(token_file):
        return None
    
    with open(token_file, "r") as f:
        token_data = json.load(f)
    
    return Credentials(
        token=token_data["token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )


def is_any_connected() -> bool:
    """Vérifie si au moins un compte est connecté."""
    return len(list_connected_accounts()) > 0


def disconnect_account(email: str) -> bool:
    """Déconnecte un compte Google spécifique."""
    token_file = os.path.join(TOKENS_DIR, f"{email}.json")
    if os.path.exists(token_file):
        os.remove(token_file)
        return True
    return False


# === Calendar API (Aggregated) ===

def get_upcoming_events(days: int = 30, max_results: int = 250) -> List[Dict]:
    """Récupère et fusionne les événements de TOUS les comptes et TOUS les calendriers connectés."""
    emails = list_connected_accounts()
    events_by_uid = {} # iCalUID -> EventData
    
    for email in emails:
        creds = _get_credentials_for_email(email)
        if not creds:
            continue
            
        try:
            service = build("calendar", "v3", credentials=creds)
            
            # 1. Lister tous les calendriers auxquels l'utilisateur a accès
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get("items", [])
            
            now = datetime.utcnow()
            time_min = now.isoformat() + "Z"
            time_max = (now + timedelta(days=days)).isoformat() + "Z"
            
            for cal in calendars:
                cal_id = cal["id"]
                # On ignore les calendriers masqués ou sans importance si nécessaire
                # Mais par défaut, on prend tout ce qui est sélectionné
                
                try:
                    events_result = service.events().list(
                        calendarId=cal_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=max_results,
                        singleEvents=True,
                        orderBy="startTime",
                    ).execute()
                    
                    items = events_result.get("items", [])
                    for item in items:
                        uid = item.get("iCalUID", item["id"])
                        start = item["start"].get("dateTime", item["start"].get("date"))
                        end = item["end"].get("dateTime", item["end"].get("date"))
                        
                        # Clé de déduplication : (UID, début)
                        # Cela permet de garder les différentes occurrences d'une série récurrente
                        # tout en fusionnant les doublons parfaits entre plusieurs comptes/calendriers.
                        # On l'utilise aussi comme ID UNIQUE et STABLE pour NovaFlow.
                        
                        # NORMALISATION: On simplifie la date pour éviter les problèmes de timezone
                        # On garde juste YYYY-MM-DDTHH:MM:SS pour l'ID
                        
                        clean_start = start
                        # Si c'est une datetime (contient T), on convertit en UTC pour être certain
                        if "T" in start:
                            try:
                                # On essaie de parser proprement
                                # Gestion basique des formats ISO
                                dt = None
                                if start.endswith("Z"):
                                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                                else:
                                    dt = datetime.fromisoformat(start)
                                
                                # Convertir en UTC
                                dt_utc = dt.astimezone(datetime.timezone.utc)
                                clean_start = dt_utc.strftime("%Y-%m-%dT%H:%M:%S")
                            except Exception:
                                # Fallback au slice si erreur de parsing (très robuste)
                                # Mais on risque le bug si Google alterne. Espérons que non
                                clean_start = start[:19]
                        
                        dedup_key = f"{uid}_{clean_start}"
                        
                        if dedup_key in events_by_uid:
                            if email not in events_by_uid[dedup_key]["accounts"]:
                                events_by_uid[dedup_key]["accounts"].append(email)
                        else:
                            events_by_uid[dedup_key] = {
                                "id": dedup_key, # Stable ID
                                "uid": uid,
                                "google_id": f"{email}_{item['id']}", # Keep for reference if needed
                                "accounts": [email],
                                "calendar_name": cal.get("summary", "Inconnu"),
                                "title": item.get("summary", "Sans titre"),
                                "start": start,
                                "end": end,
                                "location": item.get("location", ""),
                                "description": item.get("description", ""),
                                "all_day": "date" in item["start"],
                                "link": item.get("htmlLink", ""),
                                "updated": item.get("updated", ""),
                            }
                except Exception as e:
                    print(f"Erreur Calendar {cal_id} pour {email}: {e}")
                    
        except Exception as e:
            print(f"Erreur liste calendriers pour {email}: {e}")
            
    # Convertir le dictionnaire en liste et trier par date de début
    all_events = list(events_by_uid.values())
    all_events.sort(key=lambda x: x["start"])
    return all_events


def get_today_events() -> List[Dict]:
    """Raccourci pour les événements d'aujourd'hui (tous comptes)."""
    return get_upcoming_events(days=1, max_results=50)
