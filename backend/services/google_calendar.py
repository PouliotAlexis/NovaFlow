"""
NovaFlow - Service Google Calendar

Gère l'authentification OAuth2 et la récupération des événements Google Calendar.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# === Configuration ===

CREDENTIALS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "credentials",
)
CLIENT_SECRET_FILE = os.path.join(CREDENTIALS_DIR, "google_client_secret.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "google_token.json")

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


# === OAuth Flow ===

def get_auth_url() -> str:
    """
    Génère l'URL d'autorisation Google.
    L'utilisateur sera redirigé vers cette URL pour autoriser NovaFlow.
    
    Returns:
        L'URL d'authentification Google.
    """
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
    """
    Traite le callback OAuth et sauvegarde les tokens.
    
    Args:
        authorization_code: Le code d'autorisation retourné par Google.
    
    Returns:
        Un dict avec le statut de la connexion.
    """
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri="http://localhost:8000/api/auth/google/callback",
    )
    
    flow.fetch_token(code=authorization_code)
    credentials = flow.credentials
    
    # Sauvegarder les tokens
    token_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }
    
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2, default=str)
    
    return {"status": "connected", "message": "Google Calendar connecté avec succès !"}


def _get_credentials() -> Optional[Credentials]:
    """
    Charge les credentials sauvegardées.
    Retourne None si l'utilisateur n'est pas encore connecté.
    """
    if not os.path.exists(TOKEN_FILE):
        return None
    
    with open(TOKEN_FILE, "r") as f:
        token_data = json.load(f)
    
    credentials = Credentials(
        token=token_data["token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id"),
        client_secret=token_data.get("client_secret"),
        scopes=token_data.get("scopes"),
    )
    
    return credentials


def is_connected() -> bool:
    """Vérifie si l'utilisateur est connecté à Google Calendar."""
    return _get_credentials() is not None


def disconnect() -> bool:
    """Déconnecte Google Calendar en supprimant les tokens."""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        return True
    return False


# === Calendar API ===

def get_upcoming_events(days: int = 7, max_results: int = 20) -> list[dict]:
    """
    Récupère les événements des X prochains jours.
    
    Args:
        days: Nombre de jours à regarder (défaut: 7).
        max_results: Nombre max d'événements (défaut: 20).
    
    Returns:
        Liste d'événements formatés.
    """
    credentials = _get_credentials()
    if not credentials:
        return []
    
    try:
        service = build("calendar", "v3", credentials=credentials)
        
        now = datetime.utcnow()
        time_min = now.isoformat() + "Z"
        time_max = (now + timedelta(days=days)).isoformat() + "Z"
        
        events_result = service.events().list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        
        events = events_result.get("items", [])
        
        formatted_events = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            
            formatted_events.append({
                "id": event["id"],
                "title": event.get("summary", "Sans titre"),
                "start": start,
                "end": end,
                "location": event.get("location", ""),
                "description": event.get("description", ""),
                "all_day": "date" in event["start"],
                "link": event.get("htmlLink", ""),
            })
        
        return formatted_events
    
    except Exception as e:
        print(f"Erreur Google Calendar: {e}")
        return []


def get_today_events() -> list[dict]:
    """Raccourci pour les événements d'aujourd'hui."""
    return get_upcoming_events(days=1, max_results=10)
