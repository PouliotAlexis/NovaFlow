import sys
import os

# Ajouter le backend au path
sys.path.append(os.path.join(os.getcwd(), "backend"))

import chromadb
from app.core.config import settings

def check_progress():
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIRECTORY)
    collection = client.get_collection(name=settings.CHROMA_COLLECTION_NAME)
    
    # Récupérer tous les documents qui ont un course_id
    results = collection.get(
        where={"course_id": {"$exists": True}}
    )
    
    # Nombre de segments (chunks)
    num_chunks = len(results['ids'])
    
    # Nombre de fichiers uniques (basé sur le source ou course_id)
    unique_files = set()
    unique_courses = set()
    
    if num_chunks > 0:
        for metadata in results['metadatas']:
            if 'source' in metadata:
                unique_files.add(metadata['source'])
            if 'course_id' in metadata:
                unique_courses.add(metadata['course_id'])
                
    print(f"Chunks indexés avec course_id: {num_chunks}")
    print(f"Fichiers uniques traités: {len(unique_files)}")
    print(f"Cours uniques traités: {len(unique_courses)}")
    if unique_courses:
        print(f"IDs des cours: {sorted(list(unique_courses))}")

if __name__ == "__main__":
    check_progress()
