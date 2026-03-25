import os
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

    # 4. Stockage
    embeddings = get_embeddings()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name="novaflow_v2"
    )
    
    return {
        "status": "success",
        "chunks": len(chunks),
        "doc_id": os.path.basename(file_path),
        "course_id": course_id
    }

def query_rag(query: str, n_results: int = 3, course_id: str = None):
    """
    Interroge le moteur RAG pour obtenir le contexte.
    """
    if course_id:
        print(f"[RAG] Recherche contextuelle filtrée pour le cours {course_id}")
        
    embeddings = get_embeddings()
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name="novaflow_v2"
    )
    
    # Gestion du filtrage par course_id
    search_kwargs = {"k": n_results}
    if course_id:
        search_kwargs["filter"] = {"course_id": str(course_id)}
        
    results = vectorstore.similarity_search(query, **search_kwargs)
    context = "\n\n".join([doc.page_content for doc in results])
    return context

def get_ingested_files(course_id: str):
    """
    Retourne la liste des noms de fichiers déjà ingérés pour un cours.
    """
    embeddings = get_embeddings()
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
        collection_name="novaflow_v2"
    )
    
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
