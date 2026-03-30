"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function CallbackLogic() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState("Interception du jeton...");

  useEffect(() => {
    // 1. Récupérer l'URI complète injectée par le navigateur
    // Exemple : uri=web+novaflow://token=c2l0ZXVybD1od...
    const fullUri = searchParams.get("uri");

    if (!fullUri) {
       // Si pas de paramètre "uri", on vérifie peut-être le hash au cas où
       const hash = window.location.hash;
       if (hash && hash.includes("token=")) {
          processToken(hash);
          return;
       }
       setStatus("En attente de redirection...");
       return;
    }

    if (!fullUri.includes("token=")) {
      setStatus("Aucun token détecté. Fermeture...");
      setTimeout(() => window.close(), 2000);
      return;
    }

    processToken(fullUri);
  }, [searchParams]);

  const processToken = (input: string) => {
    try {
      // 2. Extraire la partie Base64 après "token="
      let base64Payload = input.split("token=")[1];
      if (base64Payload.includes("&")) {
         base64Payload = base64Payload.split("&")[0];
      }

      // 3. Décoder le Base64
      const decodedPayload = atob(base64Payload);

      // 4. Parser la query string décodée
      const params = new URLSearchParams(decodedPayload);
      const token = params.get("token");
      const privateToken = params.get("private_token");

      if (token && window.opener) {
        // 5. Envoyer le token à l'onglet principal
        window.opener.postMessage({
          type: "MOODLE_AUTH_SUCCESS",
          payload: { token, privateToken }
        }, window.location.origin);

        setStatus("Authentification réussie ! Fermeture...");
        window.close();
      } else {
        setStatus("Données de token invalides.");
      }
    } catch (error) {
      console.error("Erreur de parsing :", error);
      setStatus("Erreur technique. Fermeture...");
      setTimeout(() => window.close(), 2000);
    }
  };

  return <p style={{ fontSize: '1.125rem', animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}>{status}</p>;
}

export default function MoodleCallbackPage() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#111827', color: 'white', fontFamily: 'sans-serif' }}>
      <Suspense fallback={<p>Chargement de l'intercepteur...</p>}>
        <CallbackLogic />
      </Suspense>
    </div>
  );
}
