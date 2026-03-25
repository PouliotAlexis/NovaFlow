import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from app.core.config import settings

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
            chunk.metadata["filename"] = os.path.basename(file_path)

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
    
    # Gestion du filtrage complexe
    search_kwargs = {"k": n_results}
    
    filters = []
    if course_id:
        filters.append({"course_id": str(course_id)})
    
    if filenames and len(filenames) > 0:
        # On filtre par le champ 'filename' qu'on vient d'ajouter
        # Pour les anciens docs, on peut aussi essayer de matcher 'source' 
        # mais le plus propre est d'utiliser 'filename'
        if len(filenames) == 1:
            filters.append({"filename": filenames[0]})
        else:
            filters.append({"filename": {"$in": filenames}})
            
    if len(filters) == 1:
        search_kwargs["filter"] = filters[0]
    elif len(filters) > 1:
        search_kwargs["filter"] = {"$and": filters}
        
    results = vectorstore.similarity_search(query, **search_kwargs)
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
            
        # Extraire les noms de fichiers uniques de la métadonnée 'source'
        ingested_sources = set()
        for meta in data["metadatas"]:
            source_path = meta.get("source")
            if source_path:
                # On ne garde que le nom du fichier pour la comparaison
                ingested_sources.add(os.path.basename(source_path))
        
        return ingested_sources
    except Exception as e:
        print(f"[RAG] Erreur get_ingested_files: {e}")
        return set()
