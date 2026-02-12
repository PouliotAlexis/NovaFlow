# Spécifications Fonctionnelles Détaillées : NovaFlow

Ce document détaille précisément ce que l'application peut faire et, surtout, ce que l'IA est capable d'analyser.

## 🧠 Capacités d'Analyse de l'IA (Le "Cerveau")

L'IA ne fait pas que "lire", elle **structure** l'information. Voici les cas d'usage précis :

### 1. Analyse Académique (Syllabus & Cours) 🎓
*   **Entrée** : PDF de plan de cours (Syllabus), Slides Powerpoint, Notes manuscrites (photo).
*   **Ce que l'IA extrait** :
    *   📅 **Dates Clés** : "Examen Intra : 24 Octobre".
    *   ⚖️ **Pondération** : "L'examen final vaut 40% de la note".
    *   📚 **Lectures Obligatoires** : Liste des chapitres à lire.
*   **Action Automatique** :
    *   Crée les événements dans le Calendrier.
    *   Crée des tâches "Lire Chapitre 3" 5 jours avant le cours.

### 2. Analyse Administrative & Financière 💰
*   **Entrée** : Factures (PDF), Relevés bancaires.
*   **Ce que l'IA extrait** :
    *   💸 **Montants & Échéances** : "Payer 175$ avant le 1er du mois".
    *   ⚠️ **Anomalies** : "Cette facture est plus élevée que la moyenne".
*   **Action Automatique** :
    *   Rappel de paiement.

### 3. Analyse des Communications (Email & Messages) 📧
*   **Entrée** : Emails (Gmail/Outlook).
*   **Ce que l'IA extrait** :
    *   🎯 **Action Items (Tâches)** : "Peux-tu m'envoyer le rapport pour mardi ?".
    *   🔥 **Urgence & Sentiment**.
*   **Modération** :
    *   "Brouillon automatique" : L'IA prépare une réponse neutre.

---

## 🛠️ Fonctionnalités de l'Application (L'Interface)

### 1. Le "Smart Feed" (Dashboard)
Résumé intelligent de la journée.

### 2. La "Drop Zone" Universelle
Une zone où tu glisses N'IMPORTE QUOI :
*   Un PDF ? -> Il est classé dans "Affaires" et analysé.
*   Un lien Youtube ? -> Il est résumé.

### 3. Le "Second Brain" (Chat RAG)
Tu peux poser des questions à tes propres données.

### 4. Le "Focus Mode"
L'IA bloque les distractions.
