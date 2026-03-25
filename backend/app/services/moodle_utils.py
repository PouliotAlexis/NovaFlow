from urllib.parse import urlparse, urlunparse

def normalize_moodle_url(url: str) -> str:
    """
    Extrait la base URL d'un lien Moodle (qu'il s'agisse de la racine, du login, 
    d'un cours ou d'un flux calendrier).
    Exemple: https://moodle.usherbrooke.ca/calendar/export_execute.php?userid=...
    Devient: https://moodle.usherbrooke.ca
    """
    if not url:
        return ""
    
    parsed = urlparse(url)
    # On ne garde que le scheme et le netloc (ex: https://moodle.usherbrooke.ca)
    base = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    return base.rstrip("/")
