import os
import sys

# Ajouter le chemin du backend pour les imports
sys.path.append(os.path.join(os.getcwd(), "app"))
sys.path.append(os.getcwd())

from app.db.database import SessionLocal
from app.services.cloud_storage import CloudStorageService
from app.services.rag_engine.ingest import UPLOADS_DIR

def sync_existing_files():
    """Parcourt uploads/ et synchronise tout ce qui ne l'est pas encore."""
    # On utilise le dossier défini dans ingest.py
    from app.services.rag_engine.ingest import UPLOADS_DIR
    
    if not os.path.exists(UPLOADS_DIR):
        print(f"❌ Dossier {UPLOADS_DIR} non trouvé.")
        return

    print(f"📂 Scan des documents existants dans: {UPLOADS_DIR}")
    
    files = []
    for root, dirs, filenames in os.walk(UPLOADS_DIR):
        for f in filenames:
            # On ignore les fichiers systèmes ou cachés
            if not f.startswith('.'):
                files.append(os.path.join(root, f))

    if not files:
        print("Empty uploads directory.")
        return

    print(f"🔄 Synchronisation de {len(files)} fichiers vers Google Drive...")
    
    db = SessionLocal()
    success_count = 0
    try:
        for file_path in files:
            file_name = os.path.basename(file_path)
            print(f"📄 Synchro: {file_name}...")
            
            success = CloudStorageService.register_and_upload(file_path, db)
            if success:
                success_count += 1
                print(f"   ✅ OK")
            else:
                print(f"   ❌ Échec (Vérifie ta connexion Google Drive)")
                
    finally:
        db.close()

    print(f"\n✨ Terminé ! {success_count}/{len(files)} fichiers synchronisés.")
    if success_count < len(files):
        print("💡 Note: Assure-toi qu'un compte Google est bien connecté dans l'interface NovaFlow.")

if __name__ == "__main__":
    sync_existing_files()
