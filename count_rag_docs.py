import sys
import os

# Ajouter le backend au path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from langchain_community.vectorstores import Chroma
from app.services.rag_engine.ingest import get_embeddings, CHROMA_DIR

def count_unique_docs():
    try:
        embeddings = get_embeddings()
        vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=embeddings,
            collection_name="novaflow_v2"
        )
        
        # Récupérer toutes les métadonnées pour extraire les noms de fichiers uniques
        # Note: get() peut être lourd si la base est enorme, mais 42Mo ça va.
        data = vectorstore.get()
        if not data or not data["metadatas"]:
            return 0, []
        
        # Dans langchain, les metadata sont stockées par chunk. 
        # On ne connaît pas forcement la clé, souvent c'est 'source' ou 'file_name'
        sources = set()
        for meta in data["metadatas"]:
            # On cherche une clé qui ressemble à une source de fichier
            source = meta.get("source") or meta.get("file_name") or meta.get("doc_id")
            if source:
                sources.add(os.path.basename(source))
        
        return len(sources), list(sources)
    except Exception as e:
        print(f"Erreur lors du comptage : {e}")
        return -1, []

if __name__ == "__main__":
    count, files = count_unique_docs()
    if count >= 0:
        print(f"NOMBRE_DOCUMENTS:{count}")
        print("LISTE_FICHIERS:")
        for f in sorted(files):
            print(f"- {f}")
    else:
        print("ERREUR_COMPTAGE")
