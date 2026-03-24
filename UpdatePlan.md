# ⚡ Master Plan de Migration : NovaFlow Cloud-Hybrid

Ce plan guide la migration complète de NovaFlow : du stockage local (JSON/Local Files) vers une architecture Cloud (Supabase/Drive) + IA Locale (Ollama).

---

## 🛠️ BLOC 1 : Migration de la Persistance (SQL)
**Objectif :** Créer le nouveau système de stockage qui remplacera les fichiers `.json` locaux.

**Prompt pour l'IA :**
> "Je migre NovaFlow d'un stockage JSON local vers Supabase. Génère un script SQL pour configurer la base de données :
> 1. Active `pgvector`.
> 2. Crée `profiles` (id, user_id, ollama_url, model_name).
> 3. Crée `tasks` (id, user_id, title, status, due_date) - cela remplacera `tasks.json`.
> 4. Crée `documents` (id, user_id, google_drive_id, file_name, summary, embedding vector(768)).
> 5. Active le RLS : `auth.uid() = user_id` sur toutes les tables pour isoler les données des utilisateurs.
> 6. Crée un trigger pour initialiser un profil par défaut lors d'un nouvel 'Auth Signup'."

---

## 🐍 BLOC 2 : Refactoring Backend - Suppression du Local
**Objectif :** Remplacer toute la logique de lecture/écriture de fichiers par des appels API Supabase.

**Prompt pour l'IA :**
> "Analyse mon `database_service.py` actuel qui utilise des fichiers JSON. Réécris-le entièrement pour utiliser `supabase-py`. 
> 1. Supprime toute logique liée aux fichiers `.json` ou dossiers `/data`.
> 2. Implémente un middleware FastAPI qui valide le JWT de l'utilisateur (Bearer Token) envoyé par le frontend.
> 3. Toutes les fonctions (get_tasks, add_task, etc.) doivent désormais utiliser le client Supabase et filtrer par `user_id` récupéré via le token."

---

## 📂 BLOC 3 : Refactoring RAG - Adieu ChromaDB & Local PDFs
**Objectif :** Basculer la recherche vectorielle vers Supabase (pgvector) et le stockage vers Google Drive.

**Prompt pour l'IA :**
> "Je veux supprimer la dépendance à ChromaDB et au stockage local des PDF. Modifie le pipeline RAG :
> 1. Crée un `google_drive_service.py` pour lire les PDF via l'API Google (avec `access_token`).
> 2. Modifie le script d'ingestion : au lieu de sauvegarder dans un dossier local, upload le PDF sur Google Drive, extrait le texte, génère les embeddings et sauvegarde-les dans la table `documents` de Supabase (pgvector).
> 3. La fonction de recherche doit maintenant faire un appel SQL `match_documents` sur Supabase au lieu de requêter ChromaDB."

---

## 🌐 BLOC 4 : Frontend - Système d'Auth & Profil Cloud
**Objectif :** Gérer l'identité utilisateur et ses préférences cloud.

**Prompt pour l'IA :**
> "Installe `@supabase/auth-helpers-nextjs` et modifie le frontend :
> 1. Remplace la logique d'accès 'invité' par un vrai Login/Register Supabase (Email ou Google).
> 2. Crée une page 'Paramètres' pour sauvegarder l'URL locale de l'IA (ex: http://localhost:11434) dans la table `profiles` de Supabase.
> 3. À la connexion, charge ces préférences dans un store global (Zustand/Context) pour que l'app sache où trouver Ollama."

---

## 🧠 BLOC 5 : Frontend - Le Connecteur IA Hybride
**Objectif :** Finaliser la boucle : données du Cloud ➡️ Intelligence Locale.

**Prompt pour l'IA :**
> "Modifie le composant `Chat.tsx` pour l'architecture hybride :
> 1. Le frontend appelle le backend pour récupérer le contexte (les chunks de Supabase).
> 2. Une fois le contexte reçu, le frontend fait un `fetch` DIRECT vers l'instance locale Ollama (`profile.ollama_url`).
> 3. Le prompt envoyé à Ollama doit inclure : [Contexte Supabase] + [Question User].
> 4. Gère les erreurs de connexion (CORS) avec un message pédagogique sur `OLLAMA_ORIGINS`."

---

## 🚀 BLOC 6 : Déploiement Cloud (Production)
**Objectif :** Préparer les fichiers pour Vercel (Front) et Render (Back).

**Prompt pour l'IA :**
> "Prépare le déploiement :
> 1. Génère un `Dockerfile` pour le backend FastAPI sans aucune dépendance à SQLite ou ChromaDB.
> 2. Crée un `vercel.json` pour le frontend.
> 3. Rédige un `README_DEPLOY.md` listant toutes les variables d'environnement nécessaires (SUPABASE_URL, GOOGLE_CLIENT_ID, etc.) et explique comment configurer les CORS sur le backend pour autoriser le domaine de production."