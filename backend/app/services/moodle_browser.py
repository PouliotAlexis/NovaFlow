import asyncio
import base64
import re
import threading

CAPTURE_TIMEOUT = 300.0  # 5 minutes

# Script injecté dans la page launch.php pour intercepter les redirects JS
# vers moodlemobile:// avant que le browser affiche "protocole inconnu".
_INTERCEPT_SCRIPT = """
(function() {
    const RE = /moodle(?:mobile)?:\\/\\//i;
    function capture(url) {
        if (url && RE.test(url)) {
            window.__novaflowDeepLink = url;
        }
    }
    // Intercepte location.replace / location.assign
    const origReplace = location.replace.bind(location);
    location.replace = function(u) { capture(u); if (!RE.test(u || '')) origReplace(u); };
    const origAssign  = location.assign.bind(location);
    location.assign  = function(u) { capture(u); if (!RE.test(u || '')) origAssign(u); };
    // Intercepte window.open (certains Moodle ouvrent dans un popup)
    const origOpen = window.open.bind(window);
    window.open = function(u, ...a) { capture(u); if (RE.test(u || '')) return null; return origOpen(u, ...a); };
    // Intercepte le setter location.href via Object.defineProperty
    try {
        const proto = Object.getPrototypeOf(location);
        const desc  = Object.getOwnPropertyDescriptor(proto, 'href');
        if (desc && desc.set) {
            Object.defineProperty(proto, 'href', {
                ...desc,
                set(v) { capture(v); if (!RE.test(v || '')) desc.set.call(this, v); }
            });
        }
    } catch(e) {}
})();
"""

# Simple token in URL query string (e.g. ?token=abc123)
_TOKEN_RE = re.compile(r"[?&]token=([a-zA-Z0-9]+)")

# Deep link: moodle(mobile)://token=<base64 or hex>
_DEEP_LINK_RE = re.compile(
    r'moodle(?:mobile)?://token=([A-Za-z0-9+/=_-]+)',
    re.IGNORECASE,
)


def _decode_moodle_token(raw: str) -> str:
    """
    Tente de décoder un token Moodle Mobile au format base64.
    Format deep link : PASSPORT:::TOKEN:::PRIVATETOKEN → on extrait TOKEN (index 1).
    Si ce n'est pas du base64 valide, retourne raw tel quel.
    """
    try:
        padded = raw + "=="
        decoded = base64.b64decode(padded).decode("utf-8")
        parts = decoded.split(":::")
        if len(parts) >= 2 and parts[1]:
            return parts[1]
    except Exception:
        pass
    return raw


def _extract_token(url: str) -> str | None:
    """Extrait le token depuis une URL query string (?token=...)."""
    match = _TOKEN_RE.search(url)
    return match.group(1) if match else None


def _extract_token_from_deep_link(url: str) -> str | None:
    """Extrait et décode le token depuis un deep link moodle(mobile)://token=..."""
    match = _DEEP_LINK_RE.search(url)
    if match:
        return _decode_moodle_token(match.group(1))
    return None


def _extract_token_from_html(html: str) -> str | None:
    """Scanne le HTML de la page pour trouver un deep link Moodle Mobile."""
    match = _DEEP_LINK_RE.search(html)
    if match:
        return _decode_moodle_token(match.group(1))
    return None


def _capture_sync(base_url: str) -> str | None:
    """
    Stratégie en 2 étapes pour les instances Moodle avec Microsoft SSO :

    Étape 1 — Ouvre la page de login Moodle normale (index.php).
              L'utilisateur se connecte via Microsoft SSO comme dans un navigateur ordinaire.
              On attend que la connexion soit établie (détection de la session active).

    Étape 2 — Une fois connecté, navigue vers launch.php pour générer le token mobile.
              On intercepte le deep link moodlemobile://token=... et extrait le token.

    Tourne dans un thread séparé (sync_playwright) pour éviter les conflits avec
    l'event loop uvicorn/asyncio sur Windows.
    """
    import os, time as _time

    _log_path = os.path.join(os.path.dirname(__file__), "..", "..", "moodle_capture.log")
    _log_path = os.path.abspath(_log_path)

    def _log(msg: str) -> None:
        line = f"[MOODLE DEBUG] {msg}"
        print(line, flush=True)
        with open(_log_path, "a", encoding="utf-8") as _f:
            _f.write(line + "\n")

    _log(f"=== _capture_sync START base_url={base_url} ===")

    try:
        from playwright.sync_api import sync_playwright, Page, Frame, Request, Response, Route
        from playwright.sync_api import Error as PlaywrightError
    except ImportError as e:
        raise RuntimeError(
            "Playwright n'est pas disponible. "
            "Installez-le avec : pip install playwright && playwright install chromium. "
            f"Détail : {e}"
        ) from e

    base = base_url.rstrip("/")
    login_url = f"{base}/login/index.php"
    launch_url = f"{base}/admin/tool/mobile/launch.php?service=moodle_mobile_app&passport=1"

    token: str | None = None
    done = threading.Event()
    logged_in = threading.Event()

    def _check_and_set(found: str | None) -> None:
        nonlocal token
        if found and not done.is_set():
            token = found
            done.set()

    def scan_page_html(page_obj: Page) -> None:
        try:
            content = page_obj.content()
            _check_and_set(_extract_token_from_html(content))
        except Exception:
            pass

    def on_frame_navigated(frame: Frame) -> None:
        url = frame.url
        _log(f"frame navigated → {url}")

        # Détection token dans URL (launch.php redirect avec ?token=)
        _check_and_set(_extract_token(url))
        _check_and_set(_extract_token_from_deep_link(url))

        # Note: logged_in est maintenant détecté uniquement via window.M.cfg.sesskey
        # dans la boucle de polling, pour éviter de déclencher step 2 trop tôt
        # (ex: /login/oauth2/callback.php se charge avant que la session soit établie).

        # Scan HTML si pas encore de token
        if not done.is_set():
            try:
                scan_page_html(frame.page)
            except Exception:
                pass

    def on_request(request: Request) -> None:
        url = request.url
        if url.lower().startswith(("moodle://", "moodlemobile://")):
            _log(f"deep link request intercepté: {url}")
            _check_and_set(_extract_token_from_deep_link(url))

    def on_response(response: Response) -> None:
        """Intercepte les redirects HTTP 302 → moodlemobile:// dans le header Location."""
        if done.is_set():
            return
        if response.status in (301, 302, 303, 307, 308):
            try:
                location = response.headers.get("location", "")
                if location:
                    _log(f"redirect {response.status} → {location}")
                _check_and_set(_extract_token_from_deep_link(location))
            except Exception:
                pass

    def on_load(page_obj: Page) -> None:
        if not done.is_set():
            scan_page_html(page_obj)

    def on_page_close() -> None:
        done.set()
        logged_in.set()  # débloquer si fermé pendant l'attente login

    def handle_new_page(new_page: Page) -> None:
        """Gère les popups (ex: fenêtre de login Microsoft)."""
        new_page.on("framenavigated", on_frame_navigated)
        new_page.on("request", on_request)
        new_page.on("response", on_response)
        new_page.on("close", lambda: on_page_close())
        new_page.on("load", lambda: on_load(new_page))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        # Injecter le script sur TOUTES les pages du contexte dès maintenant.
        context.add_init_script(script=_INTERCEPT_SCRIPT)
        context.on("page", handle_new_page)

        page = context.new_page()
        page.on("framenavigated", on_frame_navigated)
        page.on("request", on_request)
        page.on("response", on_response)
        page.on("close", lambda: on_page_close())
        page.on("load", lambda: on_load(page))

        try:
            # === Étape 1 : Login via la page standard ===
            try:
                page.goto(login_url, wait_until="domcontentloaded")
            except PlaywrightError:
                pass

            # Attendre que l'utilisateur soit connecté (max 5 min)
            # Stratégie : polling sur window.M.cfg.sesskey sur TOUTES les pages du contexte
            _log(f"En attente de connexion sur {login_url} ...")
            deadline = _time.time() + CAPTURE_TIMEOUT
            while not logged_in.is_set() and not done.is_set():
                if _time.time() > deadline:
                    break
                for pg in context.pages:
                    try:
                        sesskey = pg.evaluate("() => window?.M?.cfg?.sesskey || null")
                        if sesskey:
                            _log(f"window.M.cfg.sesskey détecté sur {pg.url} → logged_in SET")
                            logged_in.set()
                            break
                    except Exception:
                        pass
                if not logged_in.is_set():
                    _time.sleep(1.5)
            _log(f"logged_in={logged_in.is_set()}, done={done.is_set()}")

            if done.is_set():
                _log(f"Token déjà capturé avant étape 2: {token}")
                return token

            # === Étape 2 : Générer le token mobile ===
            if not done.is_set():
                _log(f"Navigation vers launch.php: {launch_url}")
                try:
                    page.goto(launch_url, wait_until="domcontentloaded")
                except PlaywrightError as e:
                    _log(f"PlaywrightError (attendue) sur launch.php: {e}")

                if not done.is_set():
                    try:
                        page.wait_for_function(
                            "() => !!window.__novaflowDeepLink",
                            timeout=10_000,
                        )
                    except Exception as e:
                        _log(f"wait_for_function timeout: {e}")
                    try:
                        deep_link = page.evaluate("() => window.__novaflowDeepLink || null")
                        _log(f"__novaflowDeepLink = {deep_link}")
                        if deep_link:
                            _check_and_set(_extract_token_from_deep_link(deep_link))
                    except Exception as e:
                        _log(f"evaluate error: {e}")

            # Dernier recours : scanner le HTML de la page finale
            if not done.is_set():
                _log("Dernier recours: scan HTML")
                try:
                    html_snippet = page.content()[:500]
                    _log(f"HTML (500 chars): {html_snippet}")
                except Exception:
                    pass
                scan_page_html(page)

            done.wait(timeout=5.0)
            _log(f"Résultat final token={token}")

        finally:
            try:
                browser.close()
            except PlaywrightError:
                pass

    return token


async def capture_moodle_token(base_url: str) -> str | None:
    """
    Ouvre un navigateur Chromium (headed) pour que l'utilisateur se connecte à Moodle
    via SSO (y compris Microsoft SSO), puis capture le jeton automatiquement.

    Tourne dans un thread séparé (sync_playwright) pour éviter les conflits
    avec l'event loop uvicorn/asyncio sur Windows.
    Retourne le token (str) ou None si timeout ou fenêtre fermée.
    """
    return await asyncio.to_thread(_capture_sync, base_url)
