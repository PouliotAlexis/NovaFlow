# Plan d'implémentation : Scraping Moodle SSO via FastAPI et Browserless.io

## 🎯 Objectif
Créer un endpoint backend sur FastAPI qui prend les identifiants de l'utilisateur, se connecte à un navigateur distant via Browserless.io en utilisant Playwright, navigue à travers le SSO de l'Université de Sherbrooke (Microsoft ADFS), et récupère le jeton de session (ou token) Moodle, le tout sans faire crasher le serveur hébergeant (ex: Render) à cause du manque de RAM.

## 🏗️ Architecture du flux (Flow)
1. **Frontend** : Envoie le courriel et le mot de passe de l'étudiant via une requête `POST` sécurisée au backend.
2. **Backend (FastAPI)** : Initie une connexion WebSocket vers Browserless.io.
3. **Browserless (Cloud)** : Ouvre une instance Chrome Headless.
4. **Playwright (Contrôleur)** : 
   - Navigue sur la page de connexion Moodle de l'UdeS.
   - Remplit le formulaire Microsoft SSO (Email -> Suivant -> Mot de passe -> Connexion).
   - Attend la redirection finale vers le tableau de bord Moodle.
   - Extrait les cookies de session ou le token d'accès.
5. **Backend** : Ferme la connexion Browserless et renvoie les données d'authentification au frontend.

---

## ⚙️ Prérequis et Configuration
**Instructions pour l'agent :**
1. S'assurer que les packages suivants sont dans le `requirements.txt` :
   - `fastapi`
   - `playwright`
   - `pydantic`
   - `python-dotenv`
2. Ajouter la clé API Browserless dans le fichier `.env` du backend :
   ```env
   BROWSERLESS_API_KEY=ta_cle_api_ici
   ```

---

## 💻 Étape 1 : Le Modèle de Données (Pydantic)
**Fichier cible suggéré :** `backend/schemas.py` ou `backend/models/moodle.py`

**Instructions :** Créer le schéma pour recevoir les identifiants en toute sécurité.

```python
from pydantic import BaseModel, EmailStr

class MoodleLoginRequest(BaseModel):
    email: EmailStr
    password: str

class MoodleLoginResponse(BaseModel):
    success: bool
    session_cookies: dict | None = None
    token: str | None = None
    error: str | None = None
```

---

## 💻 Étape 2 : Le Service Playwright (La logique métier)
**Fichier cible suggéré :** `backend/services/moodle_scraper.py`

**Instructions pour l'agent :** Créer une fonction asynchrone qui gère la connexion à Browserless via `connect_over_cdp` et exécute le flux de connexion Microsoft SSO. Adapter les sélecteurs CSS (comme `#i0116` et `#i0118`) qui sont les standards de la page de connexion Microsoft.

```python
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def get_moodle_session_via_browserless(email: str, password: str):
    browserless_key = os.getenv("BROWSERLESS_API_KEY")
    if not browserless_key:
        raise ValueError("BROWSERLESS_API_KEY manquante dans l'environnement.")

    # URL WebSocket pour se connecter à Browserless v2
    ws_endpoint = f"wss://production-sfo.browserless.io?token={browserless_key}"

    async with async_playwright() as p:
        try:
            # 1. Connexion au navigateur distant (au lieu de launch() local)
            browser = await p.chromium.connect_over_cdp(ws_endpoint)
            context = await browser.new_context()
            page = await context.new_page()

            # 2. Navigation vers le Moodle de l'UdeS
            await page.goto("[https://moodle.usherbrooke.ca/login/index.php](https://moodle.usherbrooke.ca/login/index.php)")

            # 3. Flux SSO Microsoft
            # Remplir l'email
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            await page.fill('input[type="email"]', email)
            await page.click('input[type="submit"]') # Bouton "Suivant"

            # Attendre l'animation Microsoft et remplir le mot de passe
            await page.wait_for_selector('input[type="password"]', timeout=10000)
            await page.fill('input[type="password"]', password)
            
            # Cliquer sur "Se connecter"
            await page.click('input[type="submit"]')

            # Gérer la demande "Rester connecté ?" (Optionnel mais fréquent chez Microsoft)
            try:
                await page.wait_for_selector('#idSIButton9', timeout=5000) # Bouton "Oui" ou "Non"
                await page.click('#idSIButton9')
            except PlaywrightTimeoutError:
                pass # Si la page n'apparaît pas, on continue

            # 4. Attendre le retour sur Moodle
            await page.wait_for_url("**/my/**", timeout=15000) # URL typique du dashboard Moodle

            # 5. Récupération des cookies de session (MoodleSession)
            cookies = await context.cookies()
            session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}

            # TODO: Si le but est d'avoir le token mobile, on peut naviguer vers le endpoint token.php ici
            # pendant que la session est active.

            await browser.close()
            
            return {
                "success": True, 
                "session_cookies": session_cookies,
            }

        except PlaywrightTimeoutError as e:
            if browser: await browser.close()
            return {"success": False, "error": "Délai d'attente dépassé (MFA requis ou erreur réseau)."}
        except Exception as e:
            if browser: await browser.close()
            return {"success": False, "error": str(e)}
```

---

## 💻 Étape 3 : L'Endpoint FastAPI (Le contrôleur)
**Fichier cible suggéré :** `backend/main.py` ou `backend/routers/moodle.py`

**Instructions pour l'agent :** Exposer la route POST qui sera appelée par le frontend de NovaFlow.

```python
from fastapi import APIRouter, HTTPException
from schemas import MoodleLoginRequest, MoodleLoginResponse
from services.moodle_scraper import get_moodle_session_via_browserless

router = APIRouter()

@router.post("/api/moodle/login", response_model=MoodleLoginResponse)
async def moodle_login(credentials: MoodleLoginRequest):
    result = await get_moodle_session_via_browserless(credentials.email, credentials.password)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result
```