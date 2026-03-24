import sys
import os

# Ajouter le backend au path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.rag_engine.ingest import ingest_document
from app.core.config import settings

# Créer un fichier de test
test_file = "test_rag_v2.txt"
with open(test_file, "w") as f:
    f.write("NovaFlow est un Life OS intelligent. Ceci est un test d'ingestion RAG v2.")

try:
    print(f"Tentative d'ingestion de {test_file}...")
    result = ingest_document(os.path.abspath(test_file))
    print(f"Résultat : {result}")
except Exception as e:
    print(f"Erreur d'ingestion : {e}")
finally:
    if os.path.exists(test_file):
        os.remove(test_file)
