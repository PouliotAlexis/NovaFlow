# Plan d'implémentation v2 : Authentification Moodle SSO via Custom Protocol (100% Web)

## 🎯 Objectif
Utiliser l'API `navigator.registerProtocolHandler` du navigateur pour créer un schéma d'URL personnalisé (`web+novaflow`). Cela permet à Moodle de rediriger le popup d'authentification vers notre application web Next.js sans être bloqué par les règles CORS ou de validation d'URL, permettant une expérience 100% sans extension.

## 🏗️ Architecture du flux (Flow)
1. **Enregistrement (Frontend)** : Au clic sur "Connecter", l'app web demande au navigateur d'associer le protocole `web+novaflow` à notre route `/moodle-callback`. (Le navigateur demandera une autorisation à l'utilisateur lors de la première utilisation).
2. **Initiation (Frontend)** : Ouverture du popup vers Moodle avec `urlscheme=web+novaflow`.
3. **Authentification (Popup)** : L'utilisateur se connecte via le SSO de l'université.
4. **Redirection système (Popup)** : Moodle redirige vers `web+novaflow://token=BASE64`. Le navigateur intercepte ce protocole et ouvre notre URL de callback pré-enregistrée en lui passant l'URI complète en paramètre.
5. **Extraction & Transfert (Popup -> Frontend)** : La page callback extrait le token de l'URI, l'envoie à l'onglet principal via `postMessage`, puis se ferme.

---

## 💻 Étape 1 : Le déclencheur Frontend (Bouton et Handler)
**Fichier cible suggéré :** `frontend/src/components/MoodleConnectButton.tsx`

**Instructions pour l'agent :** Intégrer `navigator.registerProtocolHandler`. Attention : cette API doit être appelée lors d'une interaction utilisateur (clic). Le paramètre `%s` sera remplacé par le navigateur avec l'URL de redirection générée par Moodle.

```tsx
"use client";
import { useState } from "react";

export default function MoodleConnectButton() {
  const [isConnecting, setIsConnecting] = useState(false);
  const MOODLE_URL = "[https://moodle.usherbrooke.ca](https://moodle.usherbrooke.ca)"; // URL cible du Moodle

  const handleMoodleConnect = () => {
    setIsConnecting(true);
    const baseUrl = window.location.origin;

    // 1. Enregistrer le protocole personnalisé (déclenche une popup native du navigateur la 1ère fois)
    try {
      navigator.registerProtocolHandler(
        "web+novaflow", 
        `${baseUrl}/moodle-callback?uri=%s`
      );
    } catch (err) {
      console.error("Erreur lors de l'enregistrement du protocole:", err);
    }

    // 2. Générer un passport (jeton de sécurité temporaire)
    const passport = crypto.randomUUID().replace(/-/g, ''); 

    // 3. Lancer Moodle avec notre custom scheme (SANS :// ni http)
    const moodleLaunchUrl = `${MOODLE_URL}/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=${passport}&urlscheme=web+novaflow`;

    // 4. Ouvrir la mini-fenêtre centrée
    const width = 500;
    const height = 700;
    const left = window.screen.width / 2 - width / 2;
    const top = window.screen.height / 2 - height / 2;
    const popup = window.open(
      moodleLaunchUrl, 
      "Moodle SSO", 
      `width=${width},height=${height},top=${top},left=${left}`
    );

    // 5. Écouter le succès renvoyé par le popup
    const messageListener = async (event: MessageEvent) => {
      // Sécurité : on n'accepte que les messages venant de notre propre domaine
      if (event.origin !== window.location.origin) return;

      if (event.data?.type === "MOODLE_AUTH_SUCCESS") {
        const { token, privateToken } = event.data.payload;
        console.log("Token intercepté avec succès via custom protocol :", token);
        
        // TODO: Envoi au backend FastAPI
        // await api.post('/users/moodle-token', { token });

        setIsConnecting(false);
        window.removeEventListener("message", messageListener);
      }
    };

    window.addEventListener("message", messageListener);

    // Nettoyage si le popup est fermé manuellement par l'utilisateur
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
      {isConnecting ? "Configuration en cours..." : "Connecter Moodle"}
    </button>
  );
}
```

---

## 💻 Étape 2 : La route de Callback (Intercepteur)
**Fichier cible suggéré :** `frontend/src/app/moodle-callback/page.tsx`

**Instructions pour l'agent :** Moodle va rediriger vers `web+novaflow://token=BASE64`. Grâce au handler défini à l'étape 1, Next.js recevra cette requête sur la route `/moodle-callback?uri=web+novaflow://token=BASE64`. Il faut extraire la query `uri`, parser la chaîne base64, envoyer les tokens au parent via `postMessage`, et fermer la fenêtre.

```tsx
"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function CallbackLogic() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState("Interception du jeton...");

  useEffect(() => {
    // 1. Récupérer l'URI complète injectée par le navigateur
    // Exemple : web+novaflow://token=c2l0ZXVybD1od...
    const fullUri = searchParams.get("uri");

    if (!fullUri || !fullUri.includes("token=")) {
      setStatus("Aucun token détecté. Fermeture...");
      setTimeout(() => window.close(), 2000);
      return;
    }

    try {
      // 2. Extraire la partie Base64 après "token="
      const base64Payload = fullUri.split("token=")[1];

      // 3. Décoder le Base64
      const decodedPayload = atob(base64Payload);

      // 4. Parser la query string décodée
      // Le payload décodé ressemble à : siteurl=...&token=...&private_token=...
      const params = new URLSearchParams(decodedPayload);
      const token = params.get("token");
      const privateToken = params.get("private_token");

      if (token && window.opener) {
        // 5. Envoyer le token à l'onglet principal de NovaFlow
        window.opener.postMessage({
          type: "MOODLE_AUTH_SUCCESS",
          payload: { token, privateToken }
        }, window.location.origin);

        setStatus("Authentification réussie ! Redirection...");
        window.close();
      } else {
        setStatus("Données de token invalides.");
      }
    } catch (error) {
      console.error("Erreur de parsing :", error);
      setStatus("Erreur technique. Fermeture...");
      setTimeout(() => window.close(), 2000);
    }
  }, [searchParams]);

  return <p className="text-lg animate-pulse">{status}</p>;
}

export default function MoodleCallbackPage() {
  return (
    <div className="flex items-center justify-center h-screen bg-gray-900 text-white font-sans">
      {/* Suspense est requis dans Next.js lors de l'utilisation de useSearchParams */}
      <Suspense fallback={<p>Chargement de l'intercepteur...</p>}>
        <CallbackLogic />
      </Suspense>
    </div>
  );
}
```