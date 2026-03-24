import os
import sys

# Ajouter le chemin du backend pour importer les modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from googleapiclient.discovery import build
from services.google_service import _get_credentials_for_email, list_connected_accounts

def test_keep_api():
    accounts = list_connected_accounts()
    if not accounts:
        print("Aucun compte Google connecté.")
        return

    email = accounts[0]
    print(f"Test de l'API Keep avec le compte: {email}")
    creds = _get_credentials_for_email(email)
    
    if not creds:
        print("Erreur: Impossible de charger les credentials.")
        return
        
    try:
        # Essayer de construire le service Keep
        service = build('keep', 'v1', credentials=creds)
        print("Service Keep construit avec succès.")
        
        # Essayer de lister les notes (devrait échouer si compte non-Workspace)
        print("Tentative de listing des notes...")
        results = service.notes().list().execute()
        notes = results.get('notes', [])
        print(f"Succès! {len(notes)} notes trouvées.")
        for note in notes[:2]:
            print(f"- {note.get('title', 'Sans titre')}")
            
    except Exception as e:
        print(f"\nERREUR: L'appel à l'API a échoué.")
        print(f"Détail de l'erreur: {e}")
        
if __name__ == "__main__":
    test_keep_api()
