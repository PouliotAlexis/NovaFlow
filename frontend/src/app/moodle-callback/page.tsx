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
      let base64Payload = hash.split("token=")[1];
      if (base64Payload.includes("&")) {
         base64Payload = base64Payload.split("&")[0];
      }

      // 2. Décoder le Base64
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
        setTimeout(() => window.close(), 2000);
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
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', backgroundColor: '#111827', color: 'white', fontFamily: 'sans-serif' }}>
      <p style={{ fontSize: '1.125rem', animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite' }}>{status}</p>
    </div>
  );
}
