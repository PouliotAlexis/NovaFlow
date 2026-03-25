# 🧩 Context for AI: NovaFlow Cloud Migration (v1.2.0)

## 📖 1. Project Overview & Identity
**NovaFlow** is a privacy-first personal assistant designed for students and professionals.
* **Current State:** Local-first architecture (Ollama for LLM, SQLite for metadata, ChromaDB for RAG, local JSON files for configurations).
* **Target State:** Cloud-Hybrid architecture. High availability, multi-device sync, and scalable processing.
* **Core Constraint:** Strict "Privacy-First" approach. No PII (Personally Identifiable Information) should ever reach the cloud LLMs without being redacted by the local Sanitizer layer.

---

## 🏗️ 2. Technical Stack Evolution
| Component          | Current (Local)            | Target (Cloud/Hybrid)                   |
| :----------------- | :------------------------- | :-------------------------------------- |
| **Backend** | FastAPI (Python 3.11+)     | FastAPI (Containerized/Docker)          |
| **Database** | SQLite / Local JSON        | PostgreSQL (Supabase or AWS RDS)        |
| **Vector Store** | ChromaDB (Local)           | Pinecone or MongoDB Atlas Vector Search |
| **LLM Engine** | Ollama (Llama 3)           | OpenAI (GPT-4o) / Azure OpenAI          |
| **Privacy Layer** | Local processing           | `services/sanitizer.py` (Redaction)     |
| **Authentication** | None / Local               | OAuth2 (Google/GitHub via Supabase)     |

---

## 📂 3. Repository Structure & Key Files
* `backend/app.py`: FastAPI entry point.
* `backend/services/ai_engine.py`: Handles LLM logic (Target for Cloud API refactor).
* `backend/services/rag_manager.py`: Manages embeddings and context retrieval.
* `backend/services/sanitizer.py`: Logic for anonymizing/de-anonymizing data.
* `backend/models/`: SQL Alchemy/Pydantic models (Needs migration to PG schema).
* `scripts/`: Utilities for data ingestion.

---

## 🛠️ 4. Detailed Migration Roadmap

### Phase 1: Database & Persistence
* **Objective:** Replace SQLite with a robust PostgreSQL schema.
* **Task:** Create a `migrate_db.py` script to map existing JSON/SQLite records to a new SQL schema.
* **Feature:** Add a `sync_status` column to track records successfully pushed to the cloud.

### Phase 2: Cloud RAG Integration
* **Objective:** Move from local ChromaDB to a cloud Vector DB.
* **Task:** Refactor `rag_manager.py` to support remote providers.
* **Constraint:** If the embedding model changes (e.g., from `all-MiniLM-L6-v2` to `text-embedding-3-small`), provide a script to re-index all documents.

### Phase 3: The "Sanitizer" Wrapper
* **Objective:** Ensure zero data leaks to OpenAI/Azure.
* **Logic Flow:**
    1.  User Query -> `sanitizer.redact(query)` -> Replaces "Alexis" with "[USER_1]".
    2.  Redacted Query -> Cloud LLM -> Response.
    3.  Response -> `sanitizer.restore(response)` -> Replaces "[USER_1]" with "Alexis".
* **Task:** Refactor `ai_engine.py` to make this flow mandatory for all cloud calls.

### Phase 4: Hybrid Mode & Fallback
* **Objective:** Keep the "Local" soul of NovaFlow alive.
* **Task:** Implement a `toggle_mode()` in the backend. If `CLOUD_API_KEY` is missing or the server is offline, the system must automatically fallback to the local `Ollama` instance.

---

## ⚠️ 5. Constraints & Edge Cases
1.  **Token Limits:** Cloud LLMs have context windows. Implement smart trimming in the RAG pipeline.
2.  **SSE Streaming:** All cloud responses must use Server-Sent Events (streaming) to ensure a high-quality UX.
3.  **Data Sovereignty:** Users must be able to choose which "collections" stay 100% local and which go to the cloud.

---

## 🤖 AI Instructions for Implementation
1.  **Analyze** the current `backend/` files to map existing functions.
2.  **Refactor** code iteratively: Start with the Database, then the AI Engine, then the RAG.
3.  **Maintain Type Safety:** Use Pydantic models for all data transfers.
4.  **Error Handling:** Implement robust retry logic for Cloud API timeouts (429/500 errors).

---
*Status: Ready for Migration v1.2.0*