# 📄 Plan d'Implémentation : Moodle Sync Native v2 (NovaFlow)

Ce document détaille la stratégie technique pour intégrer le scraping profond de Moodle directement dans le backend de NovaFlow, remplaçant l'extension Chrome par un service autonome capable de traiter tous les types de fichiers et d'automatiser la synchronisation.

## 🎯 1. Objectifs Principaux

* **Scraping Profond :** Extraire les fichiers des sections de cours ET des modules "Devoirs" (Assignments).
* **Multi-Format :** Supporter `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.zip`.
* **Organisation Granulaire :** Classer automatiquement par `Cours > Section > Type`.
* **Automatisation :** Exécution périodique en arrière-plan tant que la session est valide.
* **Intelligence RAG :** Extraire le texte de chaque format pour l'injection IA.

## 🛠 2. Phase Technique 1 : Infrastructure du Scraper (Playwright)

Le backend doit simuler une navigation humaine pour accéder aux zones protégées de Moodle.

### 2.1 Configuration de l'environnement (Approche Locale & SSO)

* **Outil :** Playwright (Python).
* **Gestion du SSO Microsoft (Capture de Session) :**
  * *Liaison au Profil Chrome :* Playwright utilise le **"User Data Directory"** du navigateur par défaut (ex: AppData local).
  * *Avantage :* Récupération instantanée des cookies de session actifs. Si tu es connecté dans Chrome, NovaFlow l'est aussi.
* **Gestion des Identifiants :** Stockage dans le `.env` pour les paramètres de base.

### 2.2 Routine de Validation & État de Connexion (Critique)

* **Détection d'état :** Avant chaque tentative de sync, le script vérifie l'existence d'un cookie valide.
* **Comportement "Non Connecté" :** Si Moodle n'est pas détecté comme "Connecté", le processus de synchronisation est **immédiatement avorté** pour éviter les erreurs. Un état `MOODLE_DISCONNECTED` est enregistré.

## 🔍 3. Phase Technique 2 : Logique de Scraping "Deep Dive"

### 3.1 Découverte des Ressources

1. **Mes cours (My Courses) :** Accéder à la page de vue d'ensemble des cours pour récupérer la liste des IDs de cours actifs (plutôt que le dashboard).
2. **Scan de Section :** Identifier les blocs "Section" (Semaines/Thèmes) pour garder le contexte.
3. **Identification des Types :** Scraper les ressources (`mod/resource`) et entrer dans les devoirs (`mod/assign`) pour lister les documents joints par le prof.

### 3.2 Gestion du Téléchargement

* Interception des flux de téléchargement.
* Renommage intelligent basé sur le nom du fichier original et le contexte du cours.

## 📂 4. Phase Technique 3 : Organisation & Dispatcher

### 4.1 Structure du Système de Fichiers

`data/moodle/[Nom_Cours]/[Nom_Section]/[Fichiers_ou_Devoirs]/`

### 4.2 Dispatcher Multi-Format (Extraction)

* Utilisation de bibliothèques natives (`python-docx`, `python-pptx`, `PyMuPDF`) pour extraire le texte.
* Normalisation en **Markdown** pour garantir une structure propre lors de l'injection dans la base vectorielle.

## ⏱ 5. Phase Technique 4 : Automatisation & Background Jobs

### 5.1 Planification (Scheduler)

* **Garde-fou :** Le Scheduler appelle `check_session_validity()` en premier.
* **Si déconnecté :** Le job s'arrête silencieusement et attend le prochain cycle.
* **Fréquence :** Configurable (ex: toutes les 4 heures).

## 🖥 6. Phase Technique 5 : Intégration UI (Dashboard & Paramètres)

L'interface guide l'utilisateur en cas de déconnexion.

* **État "Déconnecté" :** Le dashboard affiche un badge "Moodle : Non synchronisé".
* **Lien de Redirection :** Un lien direct redirige vers `Settings > Integrations > Moodle`.
* **Action dans les Paramètres :** Un bouton "Ouvrir Moodle & Connecter" permet à l'utilisateur de s'authentifier dans son navigateur habituel pour rafraîchir la session.

## 📋 7. Étapes de Développement (Roadmap)

1. **Semaine 1 :** Script de capture de session via Profil Chrome et détection d'état (Fail-Safe).
2. **Semaine 2 :** Scraping profond (navigation dans les sections et les devoirs).
3. **Semaine 3 :** Dispatcher de texte multi-format et organisation automatisée des dossiers.
4. **Semaine 4 :** UI de statut, redirection vers les paramètres et tests finaux en local.

## ⚠️ Risques & Solutions

* **MFA Microsoft :** Géré par l'utilisateur via son navigateur habituel. NovaFlow utilise simplement le profil persistant.
* **Conflit de Profil :** S'assurer que Chrome n'est pas "verrouillé" lors de l'accès par Playwright (utiliser un profil cloné si nécessaire).