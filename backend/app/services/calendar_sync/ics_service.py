import httpx
from ics import Calendar
from typing import List, Dict, Any
from datetime import datetime, timezone

class ICSService:
    @staticmethod
    async def fetch_events(url: str) -> List[Dict[str, Any]]:
        """Télécharge un flux ICS et retourne les événements formatés."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code != 200:
                raise Exception(f"Erreur téléchargement ICS ({response.status_code})")
            
            calendar = Calendar(response.text)
            events = []
            for event in calendar.events:
                events.append({
                    "id": event.uid,
                    "title": event.name,
                    "start": event.begin.isoformat(),
                    "end": event.end.isoformat() if event.end else None,
                    "description": event.description,
                    "location": event.location,
                    "source": "ics"
                })
            return events
