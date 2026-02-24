import requests
import feedparser
from icalendar import Calendar
from datetime import datetime, timedelta, timezone
from dateutil import parser as date_parser
from bs4 import BeautifulSoup
import os

def get_moodle_events(url: str, days: int = 30) -> list:
    """
    Fetch and parse Moodle events from an RSS or iCal URL.
    Returns a list of dicts formatted for NovaFlow calendar aggregation.
    """
    if not url:
        return []
    
    # If the user only pasted the token instead of the full URL (e.g., from the RSS Keys page)
    # We try to construct a standard Moodle URL if they didn't provide domain.
    # However, since we need the domain, if it's JUST a hex token without a domain, 
    # we might need to guess or ask them to provide the full URL.
    # We will assume a default format if they only pasted the token from poly or similar.
    # But ideally they should paste the full URL. If it doesn't start with http, let's log it.
    
    if not url.startswith("http"):
        print(f"Warning: Le lien Moodle fourni ne commence pas par HTTP(S). C'est peut-être juste un token: {url}")
        # As a fallback, we try to construct a generic URL but it's risky without the base domain.
        # Let's assume polytechnique montreal for now as fallback, or return empty.
        # For better UX, we'll try to use a default domain OR just fail gracefully.
        url = f"https://moodle.polymtl.ca/calendar/export_execute.php?userid=1&authtoken={url}&preset_what=all&preset_time=recentupcoming"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NovaFlow/1.0"
        }
        response = requests.get(url, timeout=15, allow_redirects=True, headers=headers)
        
        if response.status_code != 200:
            print(f"⚠️ Moodle: HTTP {response.status_code} (attendu 200). L'URL est peut-être incorrecte.")
            print(f"   Conseil: Utilisez le lien direct .ics depuis Moodle > Calendrier > Exporter.")
            return []
        
        content = response.text
        
        if not content or len(content.strip()) < 10:
            print(f"⚠️ Moodle: Réponse vide. Le serveur n'a pas retourné de données.")
            print(f"   Conseil: Vérifiez que le token d'authentification est encore valide.")
            return []
        
        events = []
        now = datetime.now(timezone.utc)
        max_date = now + timedelta(days=days)

        if "BEGIN:VCALENDAR" in content:
            # Format: iCalendar (.ics)
            cal = Calendar.from_ical(content)
            for component in cal.walk():
                if component.name == "VEVENT":
                    start_dt = component.get('dtstart')
                    if not start_dt:
                        continue
                        
                    start = start_dt.dt
                    is_all_day = not isinstance(start, datetime)
                    
                    if is_all_day:
                        start = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
                    elif start.tzinfo is None:
                        start = start.replace(tzinfo=timezone.utc)
                        
                    # Filter limit
                    if start > max_date or start < now - timedelta(days=7):
                        continue

                    end_dt = component.get('dtend')
                    end_str = None
                    if end_dt:
                        end = end_dt.dt
                        if not isinstance(end, datetime):
                            end = datetime(end.year, end.month, end.day, tzinfo=timezone.utc)
                        elif end.tzinfo is None:
                            end = end.replace(tzinfo=timezone.utc)
                        end_str = end.isoformat()

                    title = str(component.get('summary', 'Sans titre'))
                    description = str(component.get('description', ''))
                    location = str(component.get('location', ''))
                    link = str(component.get('url', ''))
                    uid = str(component.get('uid', f"moodle_{start.timestamp()}"))
                    
                    # Parse CATEGORIES — returns vCategory object, extract text
                    raw_cats = component.get('categories')
                    category = ""
                    if raw_cats:
                        try:
                            cats_list = raw_cats.to_ical().decode('utf-8')
                            category = cats_list
                        except Exception:
                            category = str(raw_cats)

                    events.append({
                        "id": uid,
                        "title": title,
                        "start": start.isoformat(),
                        "end": end_str,
                        "description": description,
                        "location": location,
                        "all_day": is_all_day,
                        "link": link,
                        "category": category,
                        "accounts": ["Moodle"],
                        "source": "moodle"
                    })
        else:
            # Format: RSS
            feed = feedparser.parse(content)
            for entry in feed.entries:
                published = entry.get('published', entry.get('updated', ''))
                try:
                    start = date_parser.parse(published)
                    if start.tzinfo is None:
                        start = start.replace(tzinfo=timezone.utc)
                except:
                    continue
                
                if start > max_date or start < now - timedelta(days=7):
                    continue

                raw_desc = entry.get('description', '')
                soup = BeautifulSoup(raw_desc, 'html.parser')
                description = soup.get_text(separator='\n').strip()
                
                uid = entry.get('id', entry.get('link', f"moodle_{start.timestamp()}"))

                events.append({
                    "id": uid,
                    "title": entry.get('title', 'Sans titre'),
                    "start": start.isoformat(),
                    "end": None,
                    "description": description,
                    "location": "",
                    "all_day": False,
                    "link": entry.get('link', ''),
                    "category": "",
                    "accounts": ["Moodle"],
                    "source": "moodle"
                })
                
        return events

    except Exception as e:
        print(f"Erreur lors de la récupération du flux Moodle : {e}")
        return []
