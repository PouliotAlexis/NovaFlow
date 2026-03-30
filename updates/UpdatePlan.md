# Plan d'implémentation : Authentification Moodle SSO via Popup (Sans Playwright)

## 🎯 Objectif
Remplacer le système de scraping Moodle (Playwright/Extension Chrome) par une authentification SSO native utilisant l'API Moodle Mobile. L'objectif est de récupérer le `token` d'accès de l'utilisateur de manière 100% frontend via une fenêtre contextuelle (popup), puis d'envoyer ce token au backend pour la synchronisation des données.

## 🏗️ Architecture du flux (Flow)
1. **Initiation (Frontend)** : L'utilisateur clique sur "Connecter Moodle". Le frontend génère un `passport` (une chaîne aléatoire) et ouvre un popup pointant vers le `launch.php` de Moodle.
2. **Authentification (Popup)** : L'utilisateur se connecte via le SSO de l'université dans le popup.
3. **Redirection & Interception (Popup)** : Moodle redirige vers notre `urlscheme` (avec l'astuce du `#`). Le popup charge notre route locale `/moodle-callback`.
4. **Extraction (Popup -> Frontend)** : La route callback extrait le payload Base64 de l'URL, le décode, extrait le token exact, l'envoie à la fenêtre parente via `postMessage`, puis se ferme.
5. **Sauvegarde (Frontend -> Backend)** : La fenêtre principale reçoit le token et l'envoie au backend (FastAPI) pour l'enregistrer dans la base de données.

---

## 💻 Étape 1 : Le déclencheur Frontend (Bouton de connexion)
**Fichier cible suggéré :** `frontend/src/components/MoodleConnectButton.tsx` (ou l'endroit où se trouve ton bouton actuel).

**Instructions pour l'agent :** Créer un composant qui gère l'ouverture du popup et écoute les messages entrants. Utiliser `crypto.randomUUID()` pour le passport.

```tsx
"use client";
import { useState, useEffect } from "react";

export default function MoodleConnectButton() {
  const [isConnecting, setIsConnecting] = useState(false);
  // Remplace par l'URL exacte du Moodle de ton école
  const MOODLE_URL = "[https://moodle.usherbrooke.ca](https://moodle.usherbrooke.ca)"; 

  const handleMoodleConnect = () => {
    setIsConnecting(true);

    // 1. Générer un passport aléatoire (sécurité CSRF)
    const passport = crypto.randomUUID().replace(/-/g, ''); 

    // 2. Préparer l'URL de callback avec l'astuce du hashtag
    const baseUrl = window.location.origin; 
    const callbackScheme = encodeURIComponent(`${baseUrl}/moodle-callback#`);

    // 3. Construire l'URL de lancement Moodle Mobile
    const moodleLaunchUrl = `${MOODLE_URL}/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=${passport}&urlscheme=${callbackScheme}`;

    // 4. Ouvrir le popup centré
    const width = 500;
    const height = 700;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;
    const popup = window.open(
      moodleLaunchUrl, 
      "Moodle SSO", 
      `width=${width},height=${height},top=${top},left=${left}`
    );

    // 5. Écouter la réponse du popup
    const messageListener = async (event: MessageEvent) => {
      // Vérification de sécurité de l'origine
      if (event.origin !== window.location.origin) return;

      if (event.data?.type === "MOODLE_AUTH_SUCCESS") {
        const { token, privateToken } = event.data.payload;
        
        console.log("Token Moodle récupéré :", token);
        
        // TODO: Envoyer le token au backend FastAPI ici pour le sauvegarder
        // await api.post('/users/moodle-token', { token });

        setIsConnecting(false);
        window.removeEventListener("message", messageListener);
      }
      
      if (event.data?.type === "MOODLE_AUTH_ERROR") {
        console.error("Erreur d'authentification Moodle");
        setIsConnecting(false);
        window.removeEventListener("message", messageListener);
      }
    };

    window.addEventListener("message", messageListener);

    // Gérer la fermeture manuelle du popup par l'utilisateur
    const checkPopupInterval = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkPopupInterval);
        setIsConnecting(false);
        window.removeEventListener("message", messageListener);
      }
    }, 1000);
  };

  return (
    <button 
      onClick={handleMoodleConnect} 
      disabled={isConnecting}
      className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
    >
      {isConnecting ? "Connexion en cours..." : "Connecter Moodle"}
    </button>
  );
}
```

---

## 💻 Étape 2 : La route de Callback (Le "Capteur" dans le popup)
**Fichier cible suggéré :** `frontend/src/app/moodle-callback/page.tsx` (Si Next.js App Router).

**Instructions pour l'agent :** Créer une page minimaliste. Au montage (`useEffect`), elle doit lire le `window.location.hash`, extraire la partie base64 après `token=`, la décoder via `atob()`, parser les paramètres avec `URLSearchParams`, envoyer les tokens au `window.opener` via `postMessage`, et fermer la fenêtre avec `window.close()`.

```tsx
"use client";
import { useEffect, useState } from "react";

export default function MoodleCallbackPage() {
  const [status, setStatus] = useState("Traitement de la connexion...");

  useEffect(() => {
    try {
      // L'URL ressemblera à : http://localhost:3000/moodle-callback#://token=BASE64_STRING
      const hash = window.location.hash;

      if (!hash || !hash.includes("token=")) {
        setStatus("Aucun token trouvé dans l'URL. Fermeture...");
        setTimeout(() => window.close(), 2000);
        return;
      }

      // 1. Extraire la chaîne en Base64
      const base64Payload = hash.split("token=")[1];

      // 2. Décoder le Base64
      // Moodle encode la réponse en base64. Une fois décodé, c'est une query string.
      // Exemple : "siteurl=[https://moodle.ecole.ca](https://moodle.ecole.ca)&token=12345abc&private_token=67890def"
      const decodedPayload = atob(base64Payload);

      // 3. Parser la query string pour récupérer les valeurs exactes
      const params = new URLSearchParams(decodedPayload);
      const token = params.get("token");
      const privateToken = params.get("private_token");

      if (token && window.opener) {
        // 4. Envoyer les données à la fenêtre principale
        window.opener.postMessage({
          type: "MOODLE_AUTH_SUCCESS",
          payload: { token, privateToken }
        }, window.location.origin);

        setStatus("Connexion réussie ! Fermeture de la fenêtre...");
        window.close();
      } else {
        setStatus("Échec de la lecture du token Moodle.");
      }
    } catch (error) {
      console.error("Erreur lors du traitement du token Moodle:", error);
      setStatus("Erreur lors du traitement. Fermeture...");
      if (window.opener) {
        window.opener.postMessage({ type: "MOODLE_AUTH_ERROR" }, window.location.origin);
      }
      setTimeout(() => window.close(), 2000);
    }
  }, []);

  return (
    <div className="flex items-center justify-center h-screen bg-gray-900 text-white font-sans">
      <p className="text-lg animate-pulse">{status}</p>
    </div>
  );
}
```