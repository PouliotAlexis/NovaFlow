import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from app.core.config import settings
import unicodedata

def normalize_text(text: str) -> str:
    """Normalise le texte en NFC pour éviter les problèmes d'accents (NFD vs NFC)."""
    if not text:
        return ""
    return unicodedata.normalize('NFC', text)

# Configuration des dossiers
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chromadb_v2")

def get_embeddings():
    """Retourne le modèle d'embeddings selon la configuration."""
    if settings.AI_MODE == "cloud" and settings.OPENAI_API_KEY:
        return OpenAIEmbeddings(openai_api_key=settings.OPENAI_API_KEY)
    else:
        return OllamaEmbeddings(base_url=settings.OLLAMA_HOST, model=settings.OLLAMA_MODEL)

_vectorstore = None

def get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        print(f"[RAG] Initialisation du vectorstore Chroma à {CHROMA_DIR}")
        _vectorstore = Chroma(
            persist_directory=CHROMA_DIR,
            embedding_function=get_embeddings(),
            collection_name="novaflow_v2"
        )
    return _vectorstore

def ingest_document(file_path: str, course_id: str = None):
    """
    Ingère un document (PDF, TXT, MD) dans ChromaDB.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. Chargement
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
    elif ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
    elif ext == ".md":
        loader = UnstructuredMarkdownLoader(file_path)
    else:
        raise ValueError(f"Format de fichier non supporté : {ext}")

    documents = loader.load()

    # 2. Découpage
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)

    # 3. Enrichissement des métadonnées
    if course_id:
        for chunk in chunks:
            chunk.metadata["course_id"] = str(course_id)
            chunk.metadata["filename"] = normalize_text(os.path.basename(file_path))

    # 4. Stockage
    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    
    # On reset le singleton pour forcer une recharge si nécessaire (optionnel selon implementation Chroma)
    # Mais add_documents s'en occupe généralement.
    
    return {
        "status": "success",
        "chunks": len(chunks),
        "doc_id": os.path.basename(file_path),
        "course_id": course_id
    }

def query_rag(query: str, n_results: int = 3, course_id: str = None, filenames: List[str] = None):
    """
    Interroge le moteur RAG pour obtenir le contexte, avec filtrage optionnel par cours et fichiers.
    """
    if course_id:
        print(f"[RAG] Recherche contextuelle filtrée pour le cours {course_id}")
    if filenames:
        print(f"[RAG] Filtre par fichiers : {filenames}")
        
    vectorstore = get_vectorstore()
    
    # 1. Préparation des filtres
    filters = []
    if course_id:
        filters.append({"course_id": str(course_id)})
    
    # Normalisation des noms de fichiers demandés
    norm_filenames = [normalize_text(f) for f in (filenames or [])]

    # --- Stratégie de recherche en 3 passes ---
    # Chroma ne supporte pas $or ni $regex, on fait donc des tentatives séquentielles.
    
    def _build_filter(course_filter, file_field, file_values):
        """Construit un filtre Chroma compatible."""
        parts = []
        if course_filter:
            parts.append({"course_id": str(course_filter)})
        if file_values:
            if len(file_values) == 1:
                parts.append({file_field: file_values[0]})
            else:
                parts.append({file_field: {"$in": file_values}})
        if len(parts) == 1:
            return parts[0]
        elif len(parts) > 1:
            return {"$and": parts}
        return None

    results = []
    
    # Passe 1 : Chercher par champ 'filename' (le plus propre)
    if norm_filenames:
        filt = _build_filter(course_id, "filename", norm_filenames)
        if filt:
            results = vectorstore.similarity_search(query, k=n_results, filter=filt)
            if results:
                print(f"[RAG] Passe 1 (filename) : {len(results)} résultats.")
    
    # Passe 2 : Pour les docs sans champ 'filename' (ingérés avant la migration)
    # On utilise .get() pour récupérer TOUS les chunks du cours, puis on filtre manuellement par basename du source
    if not results and norm_filenames and course_id:
        print(f"[RAG] Passe 1 échouée. Tentative Passe 2 (get + basename filter)...")
        try:
            # Récupérer TOUS les chunks du cours avec leurs métadonnées et leur contenu
            all_data = vectorstore.get(
                where={"course_id": str(course_id)},
                include=["metadatas", "documents"]
            )
            
            if all_data and all_data.get("documents"):
                # Filtrer manuellement par basename du source
                matching_docs = []
                for i, meta in enumerate(all_data["metadatas"]):
                    source = meta.get("source", "")
                    # Normaliser les séparateurs de chemin mixtes Windows
                    basename = normalize_text(os.path.basename(source.replace("\\", "/")))
                    if basename in norm_filenames:
                        matching_docs.append(all_data["documents"][i])
                
                if matching_docs:
                    # On a trouvé des chunks correspondants — on les retourne directement
                    # (pas de re-ranking par similarité, mais au moins on a les bons docs)
                    from langchain.schema import Document as LCDocument
                    results = [LCDocument(page_content=doc) for doc in matching_docs[:n_results]]
                    print(f"[RAG] Passe 2 (get + basename) : {len(results)} résultats sur {len(matching_docs)} chunks totaux.")
        except Exception as e:
            print(f"[RAG] Erreur Passe 2: {e}")

    # Passe 3 : Fallback - tout le cours sans filtre fichier
    if not results and course_id:
        print(f"[RAG] Aucun résultat ciblé. Fallback sur tout le cours {course_id}...")
        results = vectorstore.similarity_search(query, k=n_results, filter={"course_id": str(course_id)})
    
    # Passe 4 : Recherche globale (dernier recours)
    if not results:
        print(f"[RAG] Aucun résultat même au niveau cours. Recherche globale...")
        results = vectorstore.similarity_search(query, k=n_results)

    # Log de debug
    print(f"[RAG] Requete: '{query}' ({'filtré par cours' if course_id else 'global'})")
    print(f"[RAG] {len(results)} résultats trouvés.")
    
    # ...
    for i, doc in enumerate(results):
        filename = doc.metadata.get('filename') or os.path.basename(doc.metadata.get('source', 'Inconnu'))
        print(f"  [{i+1}] {filename} -> {doc.page_content[:80]}...")
        
    context = "\n\n".join([doc.page_content for doc in results])
    return context

def get_ingested_files(course_id: str):
    """
    Retourne la liste des noms de fichiers déjà ingérés pour un cours.
    """
    vectorstore = get_vectorstore()
    
    # On récupère tous les documents filtrés par course_id
    # Chroma ne permet pas facilement de récupérer uniquement les métadonnées sans les documents
    # Mais on peut utiliser .get() avec un filtre
    try:
        data = vectorstore.get(
            where={"course_id": str(course_id)},
            include=["metadatas"]
        )
        
        if not data or not data["metadatas"]:
            return set()
            
        # Extraire les noms de fichiers uniques
        ingested_sources = set()
        for meta in data["metadatas"]:
            # On stocke les noms normalisés pour que le frontend envoie des noms qui matchent
            source_path = meta.get("source", "")
            filename = meta.get("filename", "")
            
            if filename:
                ingested_sources.add(normalize_text(filename))
            elif source_path:
                # Normaliser les séparateurs de chemin mixtes (Windows)
                ingested_sources.add(normalize_text(os.path.basename(source_path.replace("\\", "/"))))
        
        return ingested_sources
    except Exception as e:
        print(f"[RAG] Erreur get_ingested_files: {e}")
        return set()
