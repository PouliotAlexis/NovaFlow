import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import urllib.parse

async def get_moodle_session_via_browserless(email: str, password: str):
    from app.core.config import settings
    
    ws_endpoint = settings.BROWSERLESS_URL
    # Si pas d'URL personnalisée mais une clé est présente, utiliser le cloud
    if not ws_endpoint and settings.BROWSERLESS_API_KEY:
        ws_endpoint = f"wss://production-sfo.browserless.io?token={settings.BROWSERLESS_API_KEY}"

    async with async_playwright() as p:
        browser = None
        try:
            if ws_endpoint:
                print(f"[BROWSERLESS] Connexion distante via {ws_endpoint}...", flush=True)
                browser = await p.chromium.connect_over_cdp(ws_endpoint)
            else:
                print("[BROWSERLESS] Pas de clé Browserless, lancement local en mode headless...", flush=True)
                browser = await p.chromium.launch(headless=True)

            context = await browser.new_context()
            page = await context.new_page()

            # L'objectif est de s'authentifier et récupérer le token SSO Moodle.
            print("[BROWSERLESS] Go to Moodle login...", flush=True)
            await page.goto("https://moodle.usherbrooke.ca/login/index.php")

            # Remplir l'email (Microsoft SSO)
            print("[BROWSERLESS] Fill email...", flush=True)
            await page.wait_for_selector('input[type="email"]', timeout=10000)
            await page.fill('input[type="email"]', email)
            await page.click('input[type="submit"]')

            # Attendre et remplir le mot de passe
            print("[BROWSERLESS] Fill password...", flush=True)
            await page.wait_for_selector('input[type="password"]', timeout=10000)
            await page.fill('input[type="password"]', password)
            await page.click('input[type="submit"]')

            # Gérer la demande "Rester connecté ?"
            try:
                await page.wait_for_selector('#idSIButton9', timeout=5000)
                await page.click('#idSIButton9')
            except PlaywrightTimeoutError:
                pass

            # Attendre le dashboard Moodle
            print("[BROWSERLESS] Wait for dashboard...", flush=True)
            await page.wait_for_url("**/my/**", timeout=15000)

            print("[BROWSERLESS] Authentifié! Récupération du jeton Moodle SSO...", flush=True)
            
            # Naviguer vers launch.php pour déclencher la génération du token Mobile
            launch_url = "https://moodle.usherbrooke.ca/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=12345&urlscheme=moodlemobile"
            
            token = None
            try:
                # Playwright interceptera la navigation vers le custom protocol et crashera,
                # on attrape l'erreur et on regarde l'URL pour y extraire le token.
                await page.goto(launch_url, timeout=10000)
            except Exception as e:
                # "net::ERR_UNKNOWN_URL_SCHEME at moodlemobile://token=BASE64"
                err_str = str(e)
                if "moodlemobile://token=" in err_str:
                    # Extraction du base64
                    base64_part = err_str.split("token=")[1].split("&")[0].split("'")[0].strip()
                    import base64
                    decoded = base64.b64decode(base64_part).decode('utf-8')
                    parsed = urllib.parse.parse_qs(decoded)
                    if "token" in parsed:
                        token = parsed["token"][0]
            
            # Autre approche si page.url a été mis à jour
            if not token:
                try:
                    url = page.url
                    if "moodlemobile://token=" in url:
                        base64_part = url.split("token=")[1].split("&")[0]
                        import base64
                        decoded = base64.b64decode(base64_part).decode('utf-8')
                        parsed = urllib.parse.parse_qs(decoded)
                        if "token" in parsed:
                            token = parsed["token"][0]
                except Exception:
                    pass

            cookies = await context.cookies()
            session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}

            await browser.close()
            
            if token:
                return {
                    "success": True, 
                    "token": token,
                    "session_cookies": session_cookies,
                }
            else:
                return {
                    "success": False,
                    "error": "Impossible d'extraire le token final après la connexion."
                }

        except PlaywrightTimeoutError as e:
            if browser: await browser.close()
            return {"success": False, "error": "Délai d'attente dépassé (MFA requis ou identifiants invalides)."}
        except Exception as e:
            if browser: await browser.close()
            return {"success": False, "error": str(e)}
