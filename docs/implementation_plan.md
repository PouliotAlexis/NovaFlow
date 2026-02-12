# Plan d'Implémentation Technique : NovaFlow (Life OS)

## 1. Vue d'Ensemble & Objectifs
Créer un assistant personnel unifié capbable de gérer des données académiques, professionnelles et personnelles.
**Contrainte Critique** : Confidentialité absolue des données via une architecture hybride (Local First ou Cloud Censuré).

## 2. Architecture du Système

### 🏗️ Stack Technique
-   **Frontend (Interface)** : Next.js 14 (React)
    -   *Pourquoi ?* : Interface réactive, gestion facile du SSR, énorme écosystème de composants UI.
-   **Backend (Cerveau)** : Python (FastAPI)
    -   *Pourquoi ?* : Langage roi de l'IA, manipule les données (PDF, Calendrier) mieux que JS.
-   **Base de Données** : PostgreSQL + Vector DB
    -   *Pourquoi ?* : Stockage relationnel pour les tâches/calendrier, Vectoriel pour la recherche (RAG).
-   **AI Engine** :
    -   **Local** : Ollama (Llama 3 / Mistral) via API locale.
    -   **Cloud (Fallback)** : OpenAI / Anthropic (via Proxy de Censure).

### 🔄 Flux de Données (Data Flow)
1.  **Ingestion** : L'utilisateur upload un fichier ou connecte un calendrier.
2.  **Traitement (Python)** :
    -   Extraction du texte (OCR/Parsing).
    -   **Sanitization (Si Cloud)** : Remplacement des entités sensibles (Noms, Emails) par des tokens.
3.  **Intelligence (IA)** :
    -   Analyse du contenu.
    -   Extraction d'actions.
4.  **Stockage** : Sauvegarde dans la DB locale.
5.  **Affichage** : Le Frontend récupère les données propres et affiche le Dashboard.

## 3. Structure du Projet (Mono-Repo)

```
/NovaFlow
  /frontend (Next.js)
  /backend (FastAPI)
  /NovaFlow
  /frontend (Next.js)
  /backend (FastAPI)
  /docs (Documentation)

## 4. Automation Features (New)

### Background Task Analysis
- **Goal**: Analyze documents and calendar events without blocking the user.
- **Implementation**: use FastAPI `BackgroundTasks`.

### Document to Tasks
- **Trigger**: `/api/upload`
- **Action**: 
    1. Ingest document.
    2. Trigger `analyze_doc_for_tasks(doc_id)`.
    3. AI prompts: "Extract all action items from this text as tasks."
    4. Call `task_manager.add_task` for each item.

### Calendar to Tasks
- **Trigger**: `/api/calendar/events` (or periodic background job)
- **Action**:
    1. Fetch events.
    2. Filter events not in `processed_events.json`.
    3. Triger `analyze_event_for_tasks(event)`.
    4. AI prompts: "Does this event require preparation? If yes, create a task."
    5. Save event ID to `processed_events.json`.
```
