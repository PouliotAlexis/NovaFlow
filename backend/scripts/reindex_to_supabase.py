import os
import sys

# Ajouter le chemin du backend pour les imports
sys.path.append(os.path.join(os.getcwd(), "app"))
sys.path.append(os.getcwd())

from app.services.rag_engine.ingest import ingest_document, get_vectorstore
from app.core.config import settings
import psycopg

def initialize_supabase_rag():
    """Vérifie et prépare Supabase pour le RAG (pgvector)."""
    db_url = settings.DATABASE_URL
    if not db_url or not db_url.startswith("postgresql"):
        print("❌ DATABASE_URL n'est pas une URL PostgreSQL (Supabase manquant?).")
        return False
    
    print(f"🔗 Connexion à {db_url.split('@')[-1]}...")
    try:
        # Tenter d'activer l'extension pgvector
        with psycopg.connect(db_url.replace("postgres://", "postgresql://")) as conn:
            with conn.cursor() as cur:
                print("🛠️ Tentative d'activation de l'extension pgvector...")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
                print("✅ Extension pgvector activée ou déjà présente.")
        return True
    except Exception as e:
        print(f"⚠️ Erreur lors de l'activation de l'extension: {e}")
        print("💡 Assure-toi d'activer 'vector' manuellement dans le dashboard Supabase (Database -> Extensions).")
        return False

def reindex_all():
    """Scanne le dossier uploads et ré-indexe tous les fichiers."""
    if not initialize_supabase_rag():
        print("🚫 Abandon de la ré-indexation Cloud. Utilisation du mode local par défaut.")
    
    # On utilise le dossier défini dans ingest.py pour être certain
    from app.services.rag_engine.ingest import UPLOADS_DIR
    
    if not os.path.exists(UPLOADS_DIR):
        print(f"❌ Dossier {UPLOADS_DIR} non trouvé.")
        return

    print(f"📂 Scan du dossier: {UPLOADS_DIR}")
    files = []
    for root, dirs, filenames in os.walk(UPLOADS_DIR):
        for f in filenames:
            if f.lower().endswith(('.pdf', '.txt', '.md', '.docx', '.pptx', '.csv')):
                files.append(os.path.join(root, f))

    if not files:
        print("Empty uploads directory. Nothing to reindex.")
        return

    print(f"🔄 Ré-indexation de {len(files)} fichiers vers le Vector Store Cloud...")
    
    success_count = 0
    for file_path in files:
        print(f"📄 Traitement de {os.path.basename(file_path)}...")
        # On essaie d'extraire le course_id du dossier parent si possible
        # Structure attendue: uploads/{course_id}/{filename}
        parent = os.path.basename(os.path.dirname(file_path))
        course_id = parent if parent != "uploads" else None
        
        result = ingest_document(file_path, course_id=course_id)
        if result.get("status") == "success":
            success_count += 1
            print(f"   ✅ OK ({result.get('chunks')} chunks)")
        else:
            print(f"   ❌ Erreur: {result.get('message')}")

    print(f"\n✨ Terminé ! {success_count}/{len(files)} fichiers indexés avec succès.")

if __name__ == "__main__":
    reindex_all()
