import os
from typing import List, Optional
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, UnstructuredMarkdownLoader, 
    Docx2txtLoader, UnstructuredPowerPointLoader, UnstructuredExcelLoader, CSVLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from langchain_postgres import PGVector
from langchain_community.vectorstores import Chroma
from app.core.config import settings
import unicodedata
import psycopg

def normalize_text(text: str) -> str:
    """Normalise le texte en NFC pour éviter les problèmes d'accents."""
    if not text:
        return ""
    return unicodedata.normalize('NFC', text)

# Configuration
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chromadb_v3") # On change de dossier pour éviter les conflits si fallback

def get_embeddings():
    """Retourne le modèle d'embeddings selon la configuration (Hybrid: Cloud/Ollama)."""
    # Si mode cloud et clé OpenAI présente -> OpenAI (plus performant pour le cloud)
    if settings.AI_MODE == "cloud" and os.getenv("OPENAI_API_KEY"):
        return OpenAIEmbeddings(model="text-embedding-3-small")
    # Sinon -> Ollama (Local/Gratuit/Privé)
    else:
        return OllamaEmbeddings(base_url=settings.OLLAMA_HOST, model=settings.OLLAMA_MODEL)

_vectorstore = None

def get_vectorstore():
    """Initialise et retourne le vectorstore (Supabase PGVector ou Chroma fallback)."""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    # On vérifie si on a une URL de DB PostgreSQL (Supabase)
    db_url = settings.DATABASE_URL
    
    # Langchain-postgres a besoin d'un format postgresql:// (pas sqlite)
    if db_url and db_url.startswith("postgresql"):
        print(f"[RAG] Initialisation du vectorstore Cloud (Supabase PGVector)")
        try:
            # S'assurer que le format est compatible avec psycopg
            # Supabase donne souvent postgresql://...
            custom_url = db_url.replace("postgres://", "postgresql://")
            
            # Note: langchain-postgres gère la création de la table automatiquement.
            _vectorstore = PGVector(
                embeddings=get_embeddings(),
                collection_name="novaflow_docs",
                connection=custom_url,
                use_jsonb=True, # Plus performant pour les métadonnées
            )
            return _vectorstore
        except Exception as e:
            print(f"[RAG] Erreur lors de l'initialisation PGVector: {e}. Fallback sur Chroma.")

    # Fallback sur ChromaDB Local
    print(f"[RAG] Initialisation du vectorstore Local (Chroma) à {CHROMA_DIR}")
    _vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=get_embeddings(),
        collection_name="novaflow_v3"
    )
    return _vectorstore

def ingest_document(file_path: str, course_id: str = None, user_id: str = None):
    """
    Ingère un document dans le Vector Store (Supabase ou Chroma).
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    print(f"[RAG] Ingestion: {file_path} (ext={ext})", flush=True)
    try:
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
        elif ext == ".md":
            loader = UnstructuredMarkdownLoader(file_path)
        elif ext in [".docx", ".doc"]:
            loader = Docx2txtLoader(file_path)
        elif ext in [".pptx", ".ppt"]:
            loader = UnstructuredPowerPointLoader(file_path)
        elif ext in [".xlsx", ".xls"]:
            loader = UnstructuredExcelLoader(file_path)
        elif ext == ".csv":
            loader = CSVLoader(file_path, encoding="utf-8")
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".svg"]:
            return {"status": "skipped", "reason": "image_not_indexed"}
        else:
            raise ValueError(f"Format non supporté : {ext}")

        documents = loader.load()
    except Exception as e:
        print(f"[RAG] Erreur chargement {file_path}: {e}")
        return {"status": "error", "message": str(e)}

    # 2. Découpage
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)

    # 3. Enrichissement
    for chunk in chunks:
        if course_id:
            chunk.metadata["course_id"] = str(course_id)
        if user_id:
            chunk.metadata["user_id"] = str(user_id)
        chunk.metadata["filename"] = normalize_text(os.path.basename(file_path))
        chunk.metadata["source"] = normalize_text(file_path)

    # 4. Stockage
    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    
    return {
        "status": "success",
        "chunks": len(chunks),
        "file_name": os.path.basename(file_path),
        "course_id": course_id,
        "mode": "cloud" if isinstance(vectorstore, PGVector) else "local",
        "doc_id": os.path.basename(file_path) # Pour la compatibilité avec l'automation
    }

def query_rag(query: str, n_results: int = 5, course_id: str = None, filenames: List[str] = None, user_id: str = None):
    """
    Recherche sémantique avec filtres (Compatible PGVector & Chroma).
    """
    vectorstore = get_vectorstore()
    
    # Construction du filtre
    filter_dict = {}
    if course_id:
        filter_dict["course_id"] = str(course_id)
    if user_id:
        filter_dict["user_id"] = str(user_id)
    
    # Note: PGVector et Chroma ont des syntaxes de filtres légèrement différentes via Langchain
    # mais Langchain unifie souvent via un dict simple ou un objet metadata.
    
    results = []
    
    # Tentative avec filtre filenames si présent
    if filenames:
        norm_filenames = [normalize_text(f) for f in filenames]
        # Dans Langchain, bcp de vectorstores supportent $in
        filter_with_files = {**filter_dict, "filename": {"$in": norm_filenames}}
        try:
            results = vectorstore.similarity_search(query, k=n_results, filter=filter_with_files)
        except:
            # Fallback simple si $in n'est pas supporté par l'implémentation
            results = vectorstore.similarity_search(query, k=n_results, filter=filter_dict)
            # Filtrage manuel
            results = [doc for doc in results if doc.metadata.get("filename") in norm_filenames]
    else:
        results = vectorstore.similarity_search(query, k=n_results, filter=filter_dict)

    print(f"[RAG] Query: {query} | Results: {len(results)}")
    
    context = "\n\n".join([doc.page_content for doc in results])
    return context

def extract_text(file_path: str) -> list[dict]:
    """
    Extrait le texte d'un fichier (page par page si possible).
    Retourne une liste de dicts {'page': int, 'text': str}.
    """
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext == ".txt":
            loader = TextLoader(file_path, encoding="utf-8")
        elif ext == ".md":
            loader = UnstructuredMarkdownLoader(file_path)
        else:
            return []
            
        docs = loader.load()
        return [{"page": i+1, "text": d.page_content} for i, d in enumerate(docs)]
    except Exception as e:
        print(f"[RAG] Erreur extract_text: {e}")
        return []

UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

def list_documents() -> list[dict]:
    """Liste tous les documents ingérés (Compatible Chroma/PGVector)."""
    vectorstore = get_vectorstore()
    try:
        # Pour Chroma
        if isinstance(vectorstore, Chroma):
            all_data = vectorstore.get(include=["metadatas"])
            docs = {}
            for metadata in all_data["metadatas"]:
                doc_id = metadata.get("doc_id") or metadata.get("filename")
                if not doc_id: continue
                if doc_id not in docs:
                    docs[doc_id] = {
                        "doc_id": doc_id,
                        "file_name": metadata.get("filename") or metadata.get("file_name", "Inconnu"),
                        "file_ext": metadata.get("file_ext", ""),
                        "chunks": 0,
                    }
                docs[doc_id]["chunks"] += 1
            return list(docs.values())
        
        # Pour PGVector (langchain-postgres)
        # On peut essayer de récupérer les métadonnées via une recherche vide ou un get si implémenté
        # Comme l'API est limitée, on se base sur ce qui est stocké.
        return [] # À améliorer si besoin d'une liste exhaustive sur Cloud
    except Exception as e:
        print(f"[RAG] Erreur list_documents: {e}")
        return []

def delete_document(doc_id: str) -> bool:
    """Supprime un document (via filename ou doc_id)."""
    vectorstore = get_vectorstore()
    try:
        # Tenter par filename si c'est ce qu'on stocke comme doc_id
        if isinstance(vectorstore, Chroma):
            # Chroma permet de filter
            existing = vectorstore.get(where={"filename": doc_id})
            if existing and existing["ids"]:
                vectorstore.delete(ids=existing["ids"])
                return True
        else:
            # PGVector
            # Suppression via filtre
            # langchain-postgres supporte vectorstore.delete(ids=...)
            # Mais on doit trouver les IDs d'abord.
            pass
        return False
    except Exception as e:
        print(f"[RAG] Erreur delete_document: {e}")
        return False

def get_ingested_files(course_id: str = None, user_id: str = None) -> List[str]:
    """
    Retourne la liste des noms de fichiers déjà présents dans le vectorstore pour un cours/utilisateur donné.
    """
    vectorstore = get_vectorstore()
    try:
        filter_dict = {}
        if course_id:
            filter_dict["course_id"] = str(course_id)
        if user_id:
            filter_dict["user_id"] = str(user_id)

        if isinstance(vectorstore, Chroma):
            # Pour Chroma, on peut récupérer les métadonnées filtrées
            results = vectorstore.get(where=filter_dict, include=["metadatas"])
            filenames = set()
            for meta in results["metadatas"]:
                if "filename" in meta:
                    filenames.add(meta["filename"])
            return list(filenames)
        
        # Pour PGVector, on fait une recherche ou on utilise le client direct si besoin
        # Fallback simple pour l'instant: recherche sémantique factice ou retour vide
        return []
    except Exception as e:
        print(f"[RAG] Erreur get_ingested_files: {e}")
        return []
