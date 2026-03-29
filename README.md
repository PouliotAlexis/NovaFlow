<div align="center">

# 🚀 NovaFlow

**Votre système d'exploitation de vie ("Life OS") unifié.**

[![Version](https://img.shields.io/badge/Version-1.2.0--Equinox-blueviolet.svg?style=for-the-badge)]()
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg?logo=python&logoColor=white&style=for-the-badge)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white&style=for-the-badge)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg?logo=next.js&logoColor=white&style=for-the-badge)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg?logo=react&logoColor=black&style=for-the-badge)](https://reactjs.org/)
[![Ollama](https://img.shields.io/badge/AI-Ollama-white.svg?logo=ollama&logoColor=black&style=for-the-badge)](https://ollama.ai/)
[![Database](https://img.shields.io/badge/DB-PostgreSQL-336791.svg?logo=postgresql&logoColor=white&style=for-the-badge)]()

*« Intelligence Centrale, Confidentialité Totale. »*

[Fonctionnalités](#-fonctionnalités) •
[Architecture](#-architecture) •
[Installation](#-installation-et-lancement) •
[Configuration](#️-configuration) •
[Base de Données](#-accès-base-de-données) •
[Sécurité](#-confidentialité--sécurité)

</div>

---

## 🌟 Vue d'Ensemble

**NovaFlow** est un **Life OS** proactif et privé (v1.2.0 "Equinox"). Conçu pour les étudiants et les professionnels exigeants, il centralise vos flux académiques, professionnels et personnels dans une interface unique et intelligente. Grâce à une architecture **Cloud-Hybrid**, bénéficiez de la puissance des derniers modèles d'IA tout en garantissant une confidentialité absolue grâce à notre couche de sanitisation locale.

---

## ✨ Fonctionnalités Principales

### 🧠 Cerveau Hybride & Privacy Layer (Nouveau !)
- **Hybrid AI Engine** : Bascule dynamique entre **Ollama** (local), **OpenAI** (cloud) et **Groq** pour un équilibre parfait entre performance et latence.
- **Reversible Redaction (Sanitizer)** : Technologie exclusive qui anonymise vos données sensibles (noms, emails, prix) *localement* avant tout envoi au cloud, puis restaure l'information originale dans la réponse reçue.
- **ContextBuilder Intelligence** : L'IA ne répond plus "dans le noir". Elle agrège dynamiquement vos tâches, vos événements calendriers et vos documents RAG pour fournir des réponses ultra-contextualisées.

### 🎓 Intégration Moodle Profonde
- **Chrome Extension "Auto-Sync"** : Capture automatique des dates d'échéance et des supports de cours directement depuis votre navigateur.
- **Moodle RSS Ingestion** : Synchronisation persistante des nouvelles annonces et changements d'horaires.
- **Cloud Document Sync** : Téléchargement automatique des fichiers Moodle et synchronisation bidirectionnelle avec **Google Drive** pour un accès multi-appareils.

### 📅 Calendrier & Tâches Unifiés
- **Fusion Multi-Sources** : Google Calendar, Microsoft Outlook et Microsoft To Do réunis dans une vue homogène.
- **Auto-Tasking IA** : L'IA analyse vos descriptions d'événements et crée automatiquement des sous-tâches actionnables avec priorisation intelligente.
- **Déduplication Sémantique** : Identification intelligente des doublons entre vos calendriers personnels et professionnels.

### 📁 Second Cerveau RAG v2
- **Drop Zone Universelle** : Glisser-déposer PDF, Markdown et CSV pour une indexation instantanée.
- **Vector Search (ChromaDB)** : Recherche sémantique haute performance avec citations directes des sources.
- **Analyse Automatisée** : Dés qu'un document est ajouté, l'IA l'analyse pour en extraire des tâches ou des rappels importants.

### 📊 Dashboard & Focus
- **Glassmorphism UI** : Interface premium basée sur Next.js 14 (App Router) avec un design moderne et réactif.
- **Productivity Trends** : Visualisation claire de votre engagement et de votre hygiène de travail.
- **Mode Deep Work** : Timer Pomodoro intégré et notifications priorisées pour éliminer les distractions.

---

## 🏗️ Architecture et Flux de Données

NovaFlow repose sur une architecture micro-services moderne, optimisée pour la performance et la confidentialité.

```mermaid
graph TD;
    %% Frontend
    subgraph Frontend["Frontend (Next.js 14 / Tailwind / Lucide)"]
        UI[App Router / Glassmorphism]
        Dashboard[Smart Dashboard]
        ChatUI[Interactive Chat Streaming]
    end

    %% Backend
    subgraph Backend["Backend (FastAPI / Python 3.11)"]
        API[API Endpoints v2]
        Context[ContextBuilder]
        Sanitizer[Local Sanitizer / Privacy]
        ManagerTasks[Task & Alert Manager]
        SyncMoodle[Moodle Sync Service]
        RAG[RAG v2 Engine]
    end

    %% Storage
    subgraph Storage["Persistance & Indexation"]
        DB[(PostgreSQL / SQLite)]
        VectorDB[(ChromaDB)]
        GDrive[Google Drive Sync]
    end

    %% Intelligence
    subgraph AI["Intelligence Stratifiée"]
        Ollama[Ollama (Local First)]
        CloudAI[OpenAI / Groq (Cloud Boost)]
    end

    %% Connections
    UI --> API
    API --> Sanitizer
    Sanitizer <--> CloudAI
    API --> Ollama
    
    API --> Context
    Context --> ManagerTasks
    Context --> RAG
    
    RAG <--> VectorDB
    API <--> DB
    SyncMoodle <--> GDrive
```

---

## 📂 Structure du Répertoire

```text
NovaFlow/
├── frontend/                  # Next.js (App Router + React 18 + Tailwind)
│   ├── src/app/               # Pages, Layouts et Routage
│   ├── src/components/        # UI haut de gamme (Glassmorphism)
│   └── package.json
├── backend/                   # FastAPI robustifié
│   ├── app/                   # Code source principal
│   │   ├── api/               # Router API (v1/v2)
│   │   ├── services/          # Logique métier (AI, Sync, RAG)
│   │   ├── db/                # Modèles SQLAlchemy et migrations
│   │   └── core/              # Config Pydantic Settings
│   ├── main.py                # Point d'entrée
│   └── requirements.txt
├── moodle-extension/          # Extension Chrome (Payload Sync)
└── docs/                      # Spécifications v1.2.0
```

---

## 🚀 Installation et Lancement

### 🛠 Prérequis Systèmes
- **Python** `3.11+`
- **Node.js** `18+` (Next.js 14+)
- **Ollama** (pour l'IA locale)

### 1️⃣ Cloner le Projet
```bash
git clone https://github.com/PouliotAlexis/NovaFlow.git
cd NovaFlow
```

### 2️⃣ Backend (FastAPI)
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate  # Windows
# ou source venv/bin/activate # Linux/Mac

pip install -r requirements.txt
cp .env.example .env     # Configurez vos clés ici
python main.py
```

### 3️⃣ Frontend (Next.js)
```bash
cd ../frontend
npm install
npm run dev
```

---

## ⚙️ Configuration (.env)

| Variable | Description | Requis |
|----------|-------------|:------:|
| `AI_MODE` | `local` (Ollama), `openai`, ou `groq`. | ✅ |
| `DATABASE_URL` | URL PostgreSQL ou SQLite (`sqlite:///./novaflow.db`). | ✅ |
| `OPENAI_API_KEY` | Clé pour GPT-4o-mini / GPT-4o. | Optionnel |
| `GROQ_API_KEY` | Clé pour Llama-3 (Haute performance gratuite). | Optionnel |
| `GOOGLE_*` | Identifiants OAuth pour Calendar & Drive. | ✅ |
| `MICROSOFT_*` | Identifiants Azure pour Outlook & To Do. | ✅ |

---

## 🗄️ Accès Base de Données

Pour faciliter le développement et la maintenance, voici les points d'accès directs aux couches de données :

### 🔙 Backend (Core Data)
- **Logique de Connexion** : [database.py](file:///c:/Users/alexi/GIT/NovaFlow/backend/app/db/database.py) (Gestion des sessions SQLAlchemy)
- **Modèles & Schéma** : [models.py](file:///c:/Users/alexi/GIT/NovaFlow/backend/app/db/models.py) (Définition des tables PostgreSQL/SQLite)
- **Vecteurs (AI Context)** : [ingest.py](file:///c:/Users/alexi/GIT/NovaFlow/backend/app/services/rag_engine/ingest.py) (Interface avec ChromaDB)

### 🔜 Frontend (State & Bridge)
- **Service API** : [api.ts](file:///c:/Users/alexi/GIT/NovaFlow/frontend/src/services/api.ts) (Lien direct vers la base backend)
- **Stockage Local** : Utilisation du `localStorage` pour la persistence des sessions (`nf_token`, `nf_user`).

---

## 🛡️ Confidentialité & Sécurité : Le Système "Sanitizer"

L'innovation majeure de NovaFlow v1.2.0 est son **Sanitizer réversible** :

1. **Interception** : Avant qu'une requête ne quitte votre machine vers un Cloud (OpenAI/Groq), le Sanitizer analyse le texte.
2. **Anonymisation** : Les entités sensibles (ex: "RDV avec Jean Dupont à 14h") sont remplacées par des tokens (ex: "RDV avec [USER_1] à 14h").
3. **Traitement Cloud** : L'IA Cloud traite la version anonymisée. Elle ne sait jamais à qui elle parle.
4. **Restauration** : À la réception, NovaFlow remplace les tokens par vos vraies données avant de vous afficher la réponse.

**Vos données restent privées, même en utilisant l'IA la plus puissante du monde.**

<br/>

<div align="center">

**[ NovaFlow Core v1.2.0 ]**  
*L'équilibre parfait entre puissance et vie privée.*

© Projet Privé — Architecturé par Alexis Pouliot.

</div>
