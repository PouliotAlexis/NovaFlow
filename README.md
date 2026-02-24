# NovaFlow 🚀

**NovaFlow** est votre système d'exploitation de vie ("Life OS") unifié, conçu pour centraliser intelligemment vos informations académiques, professionnelles et personnelles.

> "Intelligence Centrale, Confidentialité Totale."

---

## 🌟 Fonctionnalités

### 📊 Dashboard & Smart Feed
- Tableau de bord intelligent qui priorise proactivement votre journée
- Résumé quotidien avec météo, événements à venir et tâches prioritaires
- Mini-calendrier interactif avec aperçu rapide
- Tendances de productivité

### 📅 Calendrier Unifié (Google + Outlook)
- Synchronisation multi-comptes **Google Calendar** et **Microsoft Outlook**
- Déduplication cross-source automatique (un même événement dans les deux calendriers = un seul affichage)
- Analyse IA automatique des descriptions d'événements pour extraire des tâches
- Fusion intelligente des tâches similaires entre sources (similarité contextuelle, pas lettre par lettre)
- Polling automatique (60s) pour capter les modifications en temps réel

### ✅ Gestion de Tâches
- Création automatique à partir des événements calendrier
- Association parent/enfant (event → tâches)
- Priorités (high/medium/low) et suivi d'avancement
- Synchronisation bidirectionnelle entre les vues Calendar et TaskList

### 📁 Drop Zone & Documents
- Glissez n'importe quel fichier (PDF, notes, liens) — l'IA le comprend et le classe
- Extraction de texte et analyse automatique
- Pipeline RAG pour contexte intelligent (ChromaDB, optionnel)

### 🧠 IA Hybride
- **Mode Local** (Ollama) : 100% privé, tout tourne sur votre machine
- **Mode Cloud** (OpenAI) : plus puissant, avec rédaction réversible des données sensibles
- Chat IA contextuel intégré

### 🔔 Notifications Intelligentes
- Alertes automatiques pour les échéances importantes (examens, deadlines)
- Panneau de notifications en temps réel

### 🎯 Mode Focus
- Timer Pomodoro intégré
- Sessions de concentration avec suivi

### 🔗 Connexions
- **Google** : Calendar (multi-comptes)
- **Microsoft** : Outlook Calendar (multi-comptes)
- **Moodle** : Courses, devoirs, notes (à venir)

---

## 🏗️ Architecture

```
NovaFlow/
├── frontend/          # Next.js (React + TypeScript)
│   └── src/
│       └── components/
│           ├── CalendarView.tsx      # Calendrier unifié
│           ├── TaskList.tsx          # Liste de tâches
│           ├── SmartFeed.tsx         # Dashboard principal
│           ├── ChatPanel.tsx         # Chat IA
│           ├── DropZone.tsx          # Upload de documents
│           ├── FocusMode.tsx         # Timer Pomodoro
│           ├── SettingsPanel.tsx     # Paramètres & connexions
│           └── ...
├── backend/           # Python (FastAPI)
│   ├── main.py                      # API endpoints
│   ├── core/config.py               # Configuration Pydantic
│   └── services/
│       ├── ai_engine.py             # Moteur IA (Ollama/OpenAI)
│       ├── automation.py            # Jobs d'analyse automatique
│       ├── calendar_aggregator.py   # Fusion Google + Outlook + dédup
│       ├── event_manager.py         # Gestion NovaFlowEvent (source of truth)
│       ├── task_manager.py          # Gestion des tâches
│       ├── google_service.py        # Google OAuth + Calendar API
│       ├── microsoft_auth.py        # Microsoft OAuth (MSAL)
│       ├── microsoft_calendar.py    # Microsoft Graph API (Calendar)
│       ├── document_processor.py    # Extraction & RAG pipeline
│       ├── notification_manager.py  # Notifications
│       ├── sanitizer.py             # Rédaction réversible
│       └── ...
└── docs/              # Documentation fonctionnelle
```

---

## 🚀 Installation & Lancement

### Prérequis
- **Python** 3.10+
- **Node.js** 18+
- **Ollama** (optionnel, pour le mode IA local)

### 1. Cloner le repo

```bash
git clone https://github.com/PouliotAlexis/NovaFlow.git
cd NovaFlow
```

### 2. Backend (FastAPI)

```bash
# Créer et activer l'environnement virtuel (depuis la racine du projet)
python -m venv backend/venv

# Windows PowerShell :
.\backend\venv\Scripts\activate.ps1
# macOS/Linux :
source backend/venv/bin/activate

# Installer les dépendances Python
pip install -r backend/requirements.txt

# Configurer les variables d'environnement
cp backend/.env.example backend/.env
# Éditer backend/.env avec vos clés (voir section Configuration ci-dessous)

# Lancer le serveur backend (port 8000)
python backend/main.py
```

Le backend sera disponible sur `http://localhost:8000`.

### 3. Frontend (Next.js)

```bash
# Dans un nouveau terminal
cd frontend
npm install
npm run dev
```

Le frontend sera disponible sur `http://localhost:3000`.

### 4. Ollama (optionnel)

Si vous utilisez le mode IA local :

```bash
# Installer Ollama depuis https://ollama.ai
ollama pull llama3
```

---

## ⚙️ Configuration

Copiez `backend/.env.example` en `backend/.env` et remplissez les valeurs :

| Variable | Description | Requis |
|----------|-------------|--------|
| `AI_MODE` | `local` (Ollama) ou `cloud` (OpenAI) | ✅ |
| `OLLAMA_HOST` | URL du serveur Ollama | Si mode local |
| `OLLAMA_MODEL` | Modèle Ollama à utiliser | Si mode local |
| `OPENAI_API_KEY` | Clé API OpenAI | Si mode cloud |
| `OPENAI_MODEL` | Modèle OpenAI (ex: `gpt-4o-mini`) | Si mode cloud |
| `MICROSOFT_CLIENT_ID` | Azure App Client ID | Pour Outlook |
| `MICROSOFT_CLIENT_SECRET` | Azure App Secret Value | Pour Outlook |
| `MICROSOFT_TENANT_ID` | Azure Tenant (`common` par défaut) | Pour Outlook |
| `MICROSOFT_REDIRECT_URI` | URI de callback Microsoft | Pour Outlook |

### Configuration Google Calendar
Placez votre fichier `credentials.json` (OAuth 2.0 Google Cloud Console) dans `backend/credentials/`.

### Configuration Microsoft Outlook
1. Créez une application dans le [portail Azure](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps)
2. Ajoutez les permissions : `User.Read`, `Calendars.ReadWrite`, `Tasks.ReadWrite`
3. Configurez l'URI de redirection : `http://localhost:8000/api/auth/microsoft/callback`
4. Copiez le Client ID et le **Secret Value** (pas le Secret ID) dans `.env`

---

## 🛡️ Confidentialité & Sécurité
- **Local First** : Par défaut, tout tourne sur votre machine via Ollama
- **Reversible Redaction** : En mode Cloud, les données sensibles (noms, emails, montants) sont anonymisées AVANT de quitter votre PC
- **Tokens sécurisés** : Les tokens OAuth sont stockés localement dans `backend/credentials/tokens/`

---

## 📄 Licence

Projet privé — © Alexis Pouliot
