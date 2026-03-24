import sys
import os
import glob

# Ajouter le backend au path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.rag_engine.ingest import ingest_document
from app.core.config import settings

def migrate_existing_index():
    target_dir = settings.MOODLE_DOWNLOADS_DESTINATION
    print(f"📂 Recherche de documents dans : {target_dir}")
    
    if not os.path.exists(target_dir):
        print("❌ Répertoire de destination introuvable.")
        return

    # scanner les sous-dossiers (qui sont les course_id)
    files_processed = 0
    for cid in os.listdir(target_dir):
        course_path = os.path.join(target_dir, cid)
        if os.path.isdir(course_path):
            print(f"📖 Traitement du cours ID : {cid}")
            
            # Trouver tous les fichiers supportés dans ce dossier
            for ext in ["pdf", "txt", "md"]:
                for file_path in glob.glob(os.path.join(course_path, f"*.{ext}")):
                    try:
                        print(f"  -> Ingestion : {os.path.basename(file_path)}")
                        ingest_document(file_path, course_id=str(cid))
                        files_processed += 1
                    except Exception as e:
                        print(f"  ❌ Erreur pour {file_path} : {e}")

    print(f"\n✅ Migration terminée. {files_processed} fichiers ont été ré-indexés avec leur course_id.")

if __name__ == "__main__":
    migrate_existing_index()
