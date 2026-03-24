import sys
import os

# Ajouter le backend au path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from langchain_community.vectorstores import Chroma
from app.services.rag_engine.ingest import get_embeddings, CHROMA_DIR

def inspect_metadata():
    try:
        embeddings = get_embeddings()
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name="novaflow_v2"
        )
        
        data = vectorstore.get()
        if not data or not data["metadatas"]:
            print("Aucune métadonnée trouvée.")
            return
        
        # Analyser un échantillon de métadonnées
        keys_found = set()
        for meta in data["metadatas"][:50]: # Échantillon de 50 chunks
            keys_found.update(meta.keys())
        
        print(f"Clés de métadonnées trouvées : {list(keys_found)}")
        
        # Vérifier si 'course_id' ou similaire existe
        course_keys = [k for k in keys_found if "course" in k.lower() or "cid" in k.lower()]
        if course_keys:
            print(f"Clés liées aux cours détectées : {course_keys}")
        else:
            print("❌ AUCUNE clé liée aux cours (course_id, cid, etc.) n'a été trouvée dans les métadonnées.")

    except Exception as e:
        print(f"Erreur lors de l'inspection : {e}")

if __name__ == "__main__":
    inspect_metadata()
