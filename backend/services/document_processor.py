"""
NovaFlow - Service de Traitement de Documents

Pipeline RAG : extraction texte → découpage en chunks → stockage vectoriel (ChromaDB).
Permet ensuite de retrouver le contexte pertinent pour chaque question de l'utilisateur.
"""

import os
import hashlib
from datetime import datetime
from typing import Optional

import chromadb
from PyPDF2 import PdfReader


# === Configuration ChromaDB ===

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chromadb")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

# Créer les dossiers s'ils n'existent pas
os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Client ChromaDB persistant (stocké sur disque)
chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

# Collection principale pour les documents
collection = chroma_client.get_or_create_collection(
    name="novaflow_documents",
    metadata={"hnsw:space": "cosine"},
)


# === Extraction de texte ===

def extract_text_from_pdf(file_path: str) -> list[dict]:
    """
    Extrait le texte page par page d'un fichier PDF.
    
    Returns:
        Liste de dicts {page: int, text: str}
    """
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append({"page": i + 1, "text": text.strip()})
    return pages


def extract_text(file_path: str) -> list[dict]:
    """
    Extrait le texte d'un fichier selon son extension.
    
    Returns:
        Liste de dicts {page: int, text: str}
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".txt", ".md", ".csv"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [{"page": 1, "text": content}]
    else:
        return []


# === Découpage en Chunks ===

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Découpe un texte en morceaux (chunks) de taille approximative.
    
    Args:
        text: Le texte source.
        chunk_size: Nombre de caractères par chunk (~100 tokens).
        overlap: Nombre de caractères de chevauchement entre chunks.
    
    Returns:
        Liste de chunks.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # Essayer de couper à la fin d'une phrase
        if end < len(text):
            # Chercher un point, retour à la ligne, ou autre séparateur
            for sep in [". ", ".\n", "\n\n", "\n", "; ", ", "]:
                last_sep = text[start:end].rfind(sep)
                if last_sep > chunk_size * 0.3:  # Au moins 30% du chunk
                    end = start + last_sep + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
    
    return chunks


# === Ingestion complète ===

def generate_doc_id(file_name: str) -> str:
    """Génère un ID unique pour un document basé sur son nom."""
    return hashlib.md5(file_name.encode()).hexdigest()[:12]


def _get_file_size_str(file_path: str) -> str:
    """Retourne la taille du fichier en format lisible."""
    try:
        size = os.path.getsize(file_path)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    except Exception:
        return "—"


def ingest_document(file_path: str, file_name: str) -> dict:
    """
    Pipeline complet d'ingestion d'un document.
    
    1. Extraire le texte
    2. Découper en chunks
    3. Stocker dans ChromaDB
    
    Args:
        file_path: Chemin vers le fichier.
        file_name: Nom original du fichier.
    
    Returns:
        Métadonnées de l'ingestion {doc_id, file_name, pages, chunks, status}
    """
    doc_id = generate_doc_id(file_name)
    file_ext = os.path.splitext(file_name)[1].lower().lstrip(".")
    file_size = _get_file_size_str(file_path)
    
    # 1. Extraction
    pages = extract_text(file_path)
    
    if not pages:
        return {
            "doc_id": doc_id,
            "file_name": file_name,
            "pages": 0,
            "chunks": 0,
            "status": "error",
            "message": "Impossible d'extraire le texte de ce fichier.",
        }
    
    # Compter les caractères totaux
    total_text = " ".join([p["text"] for p in pages])
    total_chars = len(total_text)
    
    # 2. Découpage en chunks
    all_chunks = []
    all_metadatas = []
    all_ids = []
    
    for page_data in pages:
        chunks = chunk_text(page_data["text"])
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_p{page_data['page']}_c{i}"
            all_chunks.append(chunk)
            all_metadatas.append({
                "doc_id": doc_id,
                "file_name": file_name,
                "file_ext": file_ext,
                "file_size": file_size,
                "total_pages": len(pages),
                "total_chars": total_chars,
                "page": page_data["page"],
                "chunk_index": i,
                "ingested_at": datetime.now().isoformat(),
            })
            all_ids.append(chunk_id)
    
    # 3. Supprimer l'ancien document s'il existe
    try:
        existing = collection.get(where={"doc_id": doc_id})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass
    
    # 4. Stocker dans ChromaDB
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        collection.add(
            documents=all_chunks[i:i + batch_size],
            metadatas=all_metadatas[i:i + batch_size],
            ids=all_ids[i:i + batch_size],
        )
    
    # 5. Générer un résumé rapide
    preview = total_text[:300] + "..." if len(total_text) > 300 else total_text
    
    return {
        "doc_id": doc_id,
        "file_name": file_name,
        "file_ext": file_ext,
        "file_size": file_size,
        "pages": len(pages),
        "chunks": len(all_chunks),
        "total_chars": total_chars,
        "status": "analyzed",
        "preview": preview,
        "message": f"Document ingéré : {len(pages)} pages, {len(all_chunks)} chunks.",
    }


# === Recherche contextuelle ===

def get_relevant_context(query: str, n_results: int = 5) -> str:
    """
    Recherche les passages les plus pertinents pour une question donnée.
    
    Args:
        query: La question de l'utilisateur.
        n_results: Nombre de résultats à retourner.
    
    Returns:
        Contexte formaté prêt à être injecté dans le prompt AI.
    """
    try:
        # Vérifier s'il y a des documents
        if collection.count() == 0:
            return ""
        
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count()),
        )
        
        if not results["documents"] or not results["documents"][0]:
            return ""
        
        # Formater le contexte
        context_parts = []
        for i, (doc, metadata) in enumerate(
            zip(results["documents"][0], results["metadatas"][0])
        ):
            source = metadata.get("file_name", "Inconnu")
            page = metadata.get("page", "?")
            context_parts.append(
                f"[Source: {source}, Page {page}]\n{doc}"
            )
        
        context = "\n\n---\n\n".join(context_parts)
        return context
    
    except Exception:
        return ""


def list_documents() -> list[dict]:
    """
    Liste tous les documents ingérés dans la base.
    
    Returns:
        Liste de documents avec métadonnées enrichies.
    """
    try:
        if collection.count() == 0:
            return []
        
        all_data = collection.get(include=["metadatas"])
        
        # Regrouper par doc_id
        docs = {}
        for metadata in all_data["metadatas"]:
            doc_id = metadata["doc_id"]
            if doc_id not in docs:
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "file_name": metadata["file_name"],
                    "file_ext": metadata.get("file_ext", ""),
                    "file_size": metadata.get("file_size", "—"),
                    "total_pages": metadata.get("total_pages", 0),
                    "total_chars": metadata.get("total_chars", 0),
                    "chunks": 0,
                    "ingested_at": metadata.get("ingested_at", ""),
                }
            docs[doc_id]["chunks"] += 1
        
        return list(docs.values())
    
    except Exception:
        return []


def delete_document(doc_id: str) -> bool:
    """Supprime un document de la base vectorielle."""
    try:
        existing = collection.get(where={"doc_id": doc_id})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
            return True
        return False
    except Exception:
        return False
