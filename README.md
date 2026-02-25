<div align="center">

# 🚀 NovaFlow

**Votre système d'exploitation de vie ("Life OS") unifié.**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg?logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg?logo=react&logoColor=black)](https://reactjs.org/)
[![Ollama](https://img.shields.io/badge/AI-Ollama-white.svg?logo=ollama&logoColor=black)](https://ollama.ai/)
[![WakaTime](https://wakatime.com/badge/github/PouliotAlexis/AlexIs.svg?style=flat)](https://wakatime.com/badge/github/PouliotAlexis/AlexIs)
[![License](https://img.shields.io/badge/License-Privée-red.svg)]()

*« Intelligence Centrale, Confidentialité Totale. »*

[Fonctionnalités](#-fonctionnalités) •
[Architecture](#-architecture) •
[Installation](#-installation-et-lancement) •
[Configuration](#️-configuration) •
[Sécurité](#-confidentialité--sécurité)

</div>

---

## 🌟 Vue d'Ensemble

**NovaFlow** n'est pas qu'un simple calendrier ou gestionnaire de tâches. C'est un véritable **Life OS** proactif conçu pour centraliser intelligemment l'ensemble de vos informations académiques, professionnelles et personnelles. Grâce à une IA locale ultra-sécurisée, NovaFlow organise, priorise et anticipe votre journée à votre place.

---

## ✨ Fonctionnalités Principales

### 📊 Dashboard & Smart Feed
Le centre de commandement de votre journée.
- **Tableau de bord intelligent IA** : Priorisation proactive du flot de travail.
- **Résumé quotidien condensé** : Météo, événements imminents et ultra-priorités en un coup d'œil.
- **Mini-calendrier interactif** : Prise de pouls rapide de votre planning.
- **Analytiques & Tendances** : Suivi fin de votre productivité et de votre hygiène de travail.

### 📅 Calendrier Unifié (Google + Outlook)
La fin absolue de la fragmentation de vos emplois du temps.
- **Synchronisation Multi-Comptes & Multi-Sources** : Google Calendar et Microsoft Outlook dans une seule interface.
- **Déduplication Cross-Source Intelligente** : Un même événement détecté sur deux calendriers n'est affiché qu'une seule fois.
- **Polling Temps Réel** : Actualisation silencieuse (60s) pour ne jamais rater un changement.

### ✅ Gestion de Tâches Autopilotée
Oubliez la saisie manuelle.
- **Création Automatique IA** : Analyse sémantique des descriptions d'événements pour en extraire des livrables (Tasks).
- **Association Parent/Enfant** : Chaque tâche est raccordée à sa source (Événement → Devoirs).
- **Fusion Contextuelle** : L'IA regroupe les tâches similaires pour éviter les doublons inutiles (analyse sémantique, pas juste lettre par lettre).
- **Synchronisation Bidirectionnelle** : Toute modification dans *Task List* se répercute instantanément sur votre *Calendar*.

### 🎓 Intégration Universitaire (Moodle Booster)
Optimisé pour l'excellence académique.
- **Extension Chrome Automatisée** : Téléchargement et organisation silencieuse de tous vos fichiers Moodle.
- **Upload Google Drive Dynamique** : Sauvegarde et hiérarchisation automatique des cours sur le cloud. (Nouveau !)

### 📁 Drop Zone & Second Cerveau (RAG)
Votre assistant documentaire personnel.
- **Glisser-Déposer Universel** : Importez PDF, notes, URL... L'IA s'occupe de lire, comprendre et classer le contenu.
- **Pipeline RAG (ChromaDB)** : Posez des questions complexes sur vos documents, obtenez la réponse exacte avec la citation de la source.

### 🧠 Cerveau Hybride (Ollama + OpenAI)
- **Local First (Ollama)** : Mode 100% privé, exécution totale sur votre machine. Vos données personnelles restent chez vous.
- **Cloud Boosté (OpenAI)** : Puissance analytique maximale avec le système de *Reversible Redaction* qui masque vos données sensibles (noms, emails, prix) AVANT de taper l'API Cloud.
- **Chat IA Omniprésent** : Un co-pilote in-app toujours prêt à brainstormer.

### 🎯 Mode Focus & Alertes
- **Timer Pomodoro Connecté** : Directement greffé sur vos tâches actives pour garantir la *Deep Work*.
- **Alertes Chirurgicales** : Notifications prioritaires pour les examens et les deadlines critiques. Zéro spam.

---

## 🏗️ Architecture et Flux de Données

NovaFlow repose sur une architecture moderne de type micro-services : un Frontend réactif Next.js communiquant avec un moteur backend robuste en Python FastAPI.

```mermaid
graph TD;
    %% Frontend
    subgraph Frontend["Frontend (Next.js / React)"]
        UI[Interface Utilisateur]
        Dashboard[Dashboard & Feed]
        Calendar[Vue Calendrier]
        Tasks[Liste des Tâches]
    end

    %% Backend
    subgraph Backend["Backend (FastAPI / Python)"]
        API[API Endpoints]
        EventManager[Event Manager]
        TaskManager[Task Manager]
        AIEngine[Moteur IA Hybride]
        RAG[Pipeline Documentaire]
        CalendarAgg[Calendar Aggregator]
    end

    %% External & Storage
    subgraph Storage["Stockage Local"]
        DB[(ChromaDB / JSON)]
    end

    subgraph External["Services Externes"]
        Google[Google Calendar & Drive]
        Outlook[Microsoft Outlook]
        Moodle[Moodle (Extension)]
        OpenAI[API OpenAI Cloud]
        Ollama[Ollama Local]
    end

    %% Connections
    UI --> API
    Dashboard --> API
    Calendar --> API
    Tasks --> API

    API --> EventManager
    API --> TaskManager
    API --> AIEngine
    API --> RAG
    
    EventManager --> CalendarAgg
    CalendarAgg <-- Sync --> Google
    CalendarAgg <-- Sync --> Outlook
    
    AIEngine -.-> Ollama
    AIEngine -.-> OpenAI
    
    RAG <--> DB
    Moodle -. "Extension Chrome" .-> Storage
```

---

## 📂 Structure du Répertoire

```text
NovaFlow/
├── frontend/                  # Next.js (React 18 + TypeScript + Tailwind)
│   ├── src/components/        # Composants réutilisables
│   ├── src/pages/             # Navigation et Layouts
│   └── package.json           # Dépendances NPM
├── backend/                   # Python FastAPI ultra-performant
│   ├── main.py                # Point d'entrée de l'API
│   ├── core/                  # Configurations Pydantic
│   ├── services/              # Logique métier lourde :
│   │   ├── ai_engine.py       # Orchestrateur IA (Ollama/OpenAI)
│   │   ├── automation.py      # Tâches background récurrentes
│   │   ├── calendar_agg*.py   # Fusion de flux calendaires
│   │   ├── document_pro*.py   # Extracteur RAG multiformats
│   │   └── sanitizer.py       # Chiffrement et Anonymisation
│   └── requirements.txt       # Stack Python
├── moodle-extension/          # Extension Chrome ("Scraper & Downloader")
│   ├── manifest.json
│   └── background.js
└── docs/                      # Spécifications et Documentation Technique
```

---

## 🚀 Installation Globale & Déploiement Local

### 🛠 Prérequis Systèmes
- **Python** `3.10+`
- **Node.js** `18+`
- **Ollama** installé sur la machine hôte *(pour config 100% locale)*

### 1️⃣ Cloner le Cortex
```bash
git clone https://github.com/PouliotAlexis/NovaFlow.git
cd NovaFlow
```

### 2️⃣ Allumage du Backend (FastAPI)
```bash
# 1. Ouvrir le répertoire backend
cd backend

# 2. Créer l'environnement virtuel silencieux
python -m venv venv

# 3. L'activer :
# -> Sous Windows PowerShell :
.\venv\Scripts\activate.ps1
# -> Sous macOS/Linux :
source venv/bin/activate

# 4. Injecter les dépendances
pip install -r requirements.txt

# 5. Définir le contexte d'environnement
cp .env.example .env

# 6. Boot du serveur
python main.py
```
> 🌐 Connexion établie sur : `http://localhost:8000`

### 3️⃣ Allumage du Frontend (Next.js)
Dans un **second terminal**, à la racine du projet complet :
```bash
cd frontend
npm install
npm run dev
```
> 🖥️ Interface graphique disponible : `http://localhost:3000`

### 4️⃣ Activation IA Locale (Optionnel mais recommandé)
Si vous optez pour une confidentialité maximale :
```bash
ollama pull llama3    # Ou tout autre modèle configuré dans le .env
ollama run llama3
```

---

## ⚙️ Paramétrage Fin (.env)

Modifiez minutieusement le fichier `backend/.env` :

| Variable | Description | Requis |
|----------|-------------|:------:|
| `AI_MODE` | Sélecteur : `local` (Ollama DB) ou `cloud` (OpenAI). | ✅ |
| `OLLAMA_HOST` | URL de votre instance locale (souvent `http://localhost:11434`). | Si `local` |
| `OLLAMA_MODEL` | Modèle préchargé (ex: `llama3`, `mistral`, `phi3`). | Si `local` |
| `OPENAI_API_KEY` | Clé secrète OpenAI. | Si `cloud` |
| `OPENAI_MODEL` | Moteur Cloud demandé (ex: `gpt-4o-mini`). | Si `cloud` |
| `MICROSOFT_*`| Identifiants Microsoft Azure (`CLIENT_ID`, `CLIENT_SECRET`). | Pour Outlook |

### 🔑 Connexions Externes OAuth
* **Google (Calendar & Drive)** : Générez un `credentials.json` via Google Cloud Console et déposez-le dans `backend/credentials/`.
* **Microsoft Outlook** : Mettez en place une App Azure Active Directory.
  * Permissions : `User.Read`, `Calendars.ReadWrite`, `Tasks.ReadWrite`.
  * Redirection URI : `http://localhost:8000/api/auth/microsoft/callback`.

---

## 🛡️ Protocole de Confidentialité & Sécurité

L'architecture de NovaFlow est un coffre-fort de données par design :
1. **Zéro-Knowledge par Défaut** : Sur `AI_MODE=local`, aucune ligne de texte n'est envoyée à l'extérieur. L'IA tourne sur vos propres processeurs.
2. **Reversible Redaction** : En `AI_MODE=cloud`, NovaFlow intercepte le texte, supprime toute mention de personnes physiques, d'adresses ou de finances (Remplacement par tokens type `[NOM_1]`), requitte l'IA globale, puis re-traduit le texte reçu avant l'affichage.
3. **Cage OAuth** : Les tokens API des services interconnectés restent scellés dans le dossier `backend/credentials/tokens/`, non exposés.


<br/>
<br/>
<br/>

<div align="center">

**[ NovaFlow Core ]**
*Reprenez le contrôle total de l'espace et du temps.*
<br/><br/>
© Projet Privé — Développé et architecturé par Alexis Pouliot.

</div>
