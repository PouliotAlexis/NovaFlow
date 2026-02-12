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
  /docs (Documentation)
```
