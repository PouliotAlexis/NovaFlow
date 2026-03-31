import os
import msal
import json
import threading
import requests
from dotenv import load_dotenv
from app.core.config import settings

load_dotenv()

# Define storage paths similar to Google Service
# Utilisation d'un chemin absolu direct pour Windows (MS)
CREDENTIALS_DIR = r"C:\Users\alexi\GIT\NovaFlow\backend\credentials"
TOKENS_DIR = os.path.join(CREDENTIALS_DIR, "tokens")

# Verrou global pour protéger les opérations de lecture/écriture token concurrentes
_token_locks: dict[str, threading.Lock] = {}
_locks_lock = threading.Lock()

def _get_token_lock(email: str) -> threading.Lock:
    """Retourne un verrou dédié pour un compte email donné."""
    with _locks_lock:
        if email not in _token_locks:
            _token_locks[email] = threading.Lock()
        return _token_locks[email]

class MicrosoftAuthService:
    def __init__(self):
        self.client_id = settings.MICROSOFT_CLIENT_ID or os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = settings.MICROSOFT_CLIENT_SECRET or os.getenv("MICROSOFT_CLIENT_SECRET")
        self.tenant_id = settings.MICROSOFT_TENANT_ID or os.getenv("MICROSOFT_TENANT_ID", "common")
        
        # Ensure redirect URI matches Azure portal (Using standardized settings)
        self.redirect_uri = settings.MICROSOFT_REDIRECT_URI or os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8000/api/auth/microsoft/callback")
        
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scopes = ["User.Read", "Calendars.ReadWrite", "Tasks.ReadWrite"]

        self.app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret,
        )

    def get_auth_url(self):
        auth_url = self.app.get_authorization_request_url(
            self.scopes,
            redirect_uri=self.redirect_uri
        )
        print(f"DEBUG: Microsoft Redirect URI: {self.redirect_uri}")
        print(f"DEBUG: Microsoft Auth URL: {auth_url}")
        return auth_url

    def acquire_token_by_code(self, code: str):
        result = self.app.acquire_token_by_authorization_code(
            code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        if "error" in result:
            return result
            
        # Token acquired successfully, now get user profile to identify account
        return self._process_successful_login(result)

    def _process_successful_login(self, token_result):
        """Fetches user profile and saves token."""
        access_token = token_result.get("access_token")
        if not access_token:
            return {"error": "No access token found"}
            
        # Fetch user profile
        headers = {'Authorization': 'Bearer ' + access_token}
        graph_data = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers
        ).json()
        
        email = graph_data.get("userPrincipalName") or graph_data.get("mail")
        if not email:
            return {"error": "Could not retrieve user email"}
            
        # Add email to result
        token_result["email"] = email
        
        # Save token
        self._save_token(email, token_result)
        
        return {
            "status": "connected",
            "email": email,
            "message": f"Successfully connected Microsoft account: {email}"
        }

    def _save_token(self, email, token_data):
        """Saves token data to a file."""
        os.makedirs(TOKENS_DIR, exist_ok=True)
        # Use a prefix to distinguish from Google tokens
        token_file = os.path.join(TOKENS_DIR, f"microsoft_{email}.json")
        
        temp_file = token_file + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(token_data, f, indent=2)
        os.replace(temp_file, token_file)

    def get_token_for_email(self, email):
        """
        Retrieves and refreshes token if needed.
        Returns a dict with 'access_token' if successful.
        Thread-safe: utilise un verrou par email pour éviter les écritures concurrentes.
        """
        token_file = os.path.join(TOKENS_DIR, f"microsoft_{email}.json")
        if not os.path.exists(token_file):
            return None
        
        lock = _get_token_lock(email)
        with lock:
            with open(token_file, "r") as f:
                token_cache = json.load(f)
            
            # Check if we have a refresh token to ensure fresh access token
            refresh_token = token_cache.get("refresh_token")
            if refresh_token:
                result = self.app.acquire_token_by_refresh_token(
                    refresh_token,
                    scopes=self.scopes
                )
                
                if "access_token" in result:
                    result["email"] = email
                    self._save_token(email, result)
                    return result
                else:
                    print(f"⚠️ Failed to refresh token for {email}: {result.get('error')}")
                    return token_cache
            
            return token_cache

    @staticmethod
    def list_connected_accounts():
        """Liste les emails des comptes Microsoft connectés."""
        if not os.path.exists(TOKENS_DIR):
            return []
        accounts = []
        for filename in os.listdir(TOKENS_DIR):
            if filename.startswith("microsoft_") and filename.endswith(".json"):
                email = filename.replace("microsoft_", "").replace(".json", "")
                accounts.append(email)
        return accounts

    @staticmethod
    def disconnect_account(email: str) -> bool:
        """Déconnecte un compte Microsoft spécifique."""
        token_file = os.path.join(TOKENS_DIR, f"microsoft_{email}.json")
        if os.path.exists(token_file):
            os.remove(token_file)
            return True
        return False

    @staticmethod
    def is_any_connected() -> bool:
        """Vérifie si au moins un compte Microsoft est connecté."""
        return len(MicrosoftAuthService.list_connected_accounts()) > 0
