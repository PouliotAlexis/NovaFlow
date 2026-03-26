import os
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import CloudFile
from app.services.calendar_sync.google import (
    upload_file_to_drive, 
    list_connected_accounts,
    _get_credentials_for_email
)
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

def calculate_file_hash(file_path: str) -> str:
    """Calcule le hash SHA-256 d'un fichier."""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

class CloudStorageService:
    @staticmethod
    def register_and_upload(file_path: str, db: Session):
        """Enregistre un fichier en base et lance l'upload vers Drive."""
        file_name = os.path.basename(file_path)
        file_hash = calculate_file_hash(file_path)
        
        # Vérifier si déjà en base
        cloud_file = db.query(CloudFile).filter(CloudFile.id == file_name).first()
        if not cloud_file:
            cloud_file = CloudFile(
                id=file_name,
                file_name=file_name,
                local_path=file_path,
                file_hash=file_hash,
                status="local"
            )
            db.add(cloud_file)
            db.commit()
            db.refresh(cloud_file)
        
        # Lancer l'upload (pour simplifier on appelle le service google.py existant)
        # On définit un chemin relatif sur Drive
        drive_rel_path = f"NovaFlow_Documents/{file_name}"
        
        try:
            # Note: upload_file_to_drive dans google.py gère déjà la logique Drive
            # On pourrait l'améliorer pour retourner le drive_id
            upload_file_to_drive(file_path, drive_rel_path)
            
            # Mise à jour du statut (on suppose succès pour l'instant)
            # Idéalement il faudrait que google.py retourne l'ID
            cloud_file.status = "synced"
            cloud_file.last_sync = datetime.now()
            db.commit()
            return True
        except Exception as e:
            print(f"❌ CloudStorage Error: {e}")
            return False

    @staticmethod
    def ensure_local_copy(file_name: str, local_dest_path: str, db: Session):
        """Vérifie si le fichier existe localement. Sinon, le télécharge depuis Drive."""
        if os.path.exists(local_dest_path):
            return True
            
        cloud_file = db.query(CloudFile).filter(CloudFile.id == file_name).first()
        if not cloud_file or not cloud_file.status in ["synced", "cloud_only"]:
            print(f"⚠️ Aucun backup cloud pour {file_name}")
            return False
            
        # Téléchargement depuis Drive
        return CloudStorageService.download_from_drive(file_name, local_dest_path)

    @staticmethod
    def download_from_drive(file_name: str, local_dest_path: str):
        """Télécharge un fichier depuis Google Drive."""
        emails = list_connected_accounts()
        if not emails:
            return False
            
        email = emails[0]
        creds = _get_credentials_for_email(email)
        if not creds:
            return False
            
        try:
            service = build("drive", "v3", credentials=creds)
            
            # 1. Trouver le fichier par son nom dans NovaFlow_Documents
            query = f"name = '{file_name}' and trashed = false"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get('files', [])
            
            if not files:
                print(f"❌ Fichier {file_name} non trouvé sur Drive.")
                return False
                
            file_id = files[0]['id']
            
            # 2. Télécharger
            print(f"📥 Cloud Storage: Téléchargement de {file_name} depuis Drive...")
            request = service.files().get_media(fileId=file_id)
            fh = io.FileIO(local_dest_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"   Progression: {int(status.progress() * 100)}%")
                
            print(f"✅ Téléchargement terminé: {local_dest_path}")
            return True
        except Exception as e:
            print(f"❌ Erreur download Drive: {e}")
            return False
