import sys
import os

# Ajouter le backend au path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.rag_engine.ingest import ingest_document, query_rag

# Fichiers de test
file_a = "doc_a.txt"
file_b = "doc_b.txt"

with open(file_a, "w") as f: f.write("Le secret du cours A est la Pomme.")
with open(file_b, "w") as f: f.write("Le secret du cours B est la Banane.")

try:
    print("--- Phase 1 : Ingestion avec IDs ---")
    ingest_document(os.path.abspath(file_a), course_id="101")
    ingest_document(os.path.abspath(file_b), course_id="202")
    
    print("\n--- Phase 2 : Recherche filtrée (Cours 101) ---")
    ctx_a = query_rag("Quel est le secret ?", course_id="101")
    print(f"Contexte trouvé pour 101 : {ctx_a}")
    
    print("\n--- Phase 3 : Recherche filtrée (Cours 202) ---")
    ctx_b = query_rag("Quel est le secret ?", course_id="202")
    print(f"Contexte trouvé pour 202 : {ctx_b}")
    
    print("\n--- Phase 4 : Recherche globale (Sans filtre) ---")
    ctx_all = query_rag("Quels sont les secrets ?")
    print(f"Contexte global : {ctx_all}")
    
    # Validation
    assert "Pomme" in ctx_a and "Banane" not in ctx_a, "Erreur de filtrage pour 101"
    assert "Banane" in ctx_b and "Pomme" not in ctx_b, "Erreur de filtrage pour 202"
    print("\n✅ TEST RÉUSSI : Le filtrage par course_id fonctionne parfaitement.")

except Exception as e:
    print(f"\n❌ TEST ÉCHOUÉ : {e}")
finally:
    for f in [file_a, file_b]:
        if os.path.exists(f): os.remove(f)
