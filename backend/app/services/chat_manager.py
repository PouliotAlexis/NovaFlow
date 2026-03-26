from typing import List, Dict
from datetime import datetime
from app.db.database import SessionLocal
from app.db.models import ChatMessage as DBChatMessage

def load_chat_history(user_id: str = None) -> List[Dict]:
    """Charge l'historique de l'utilisateur depuis la base de données."""
    with SessionLocal() as db:
        query = db.query(DBChatMessage)
        if user_id:
            query = query.filter(DBChatMessage.user_id == user_id)
        else:
            query = query.filter(DBChatMessage.user_id == None)
        
        messages = query.order_by(DBChatMessage.timestamp.asc()).all()
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None
            }
            for m in messages
        ]

def save_chat_message(role: str, content: str, user_id: str = None):
    """Ajoute un message à l'historique (Base de données)."""
    with SessionLocal() as db:
        new_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        db_message = DBChatMessage(
            id=new_id,
            role=role,
            content=content,
            user_id=user_id
        )
        db.add(db_message)
        
        # Limiter l'historique de l'utilisateur aux 50 derniers messages
        query = db.query(DBChatMessage)
        if user_id:
            query = query.filter(DBChatMessage.user_id == user_id)
        else:
            query = query.filter(DBChatMessage.user_id == None)
        
        history_count = query.count()
        if history_count >= 50:
            # Supprimer les plus vieux de cet utilisateur
            oldest = query.order_by(DBChatMessage.timestamp.asc()).limit(history_count - 49).all()
            for old in oldest:
                db.delete(old)
        
        db.commit()

def clear_chat_history(user_id: str = None):
    """Efface l'historique de l'utilisateur en base de données."""
    with SessionLocal() as db:
        # Logique de suppression atomique
        query = db.query(DBChatMessage)
        if user_id:
            query = query.filter(DBChatMessage.user_id == user_id)
        else:
            query = query.filter(DBChatMessage.user_id == None)
        
        deleted_count = query.delete(synchronize_session='fetch')
        db.commit()
        
        # Audit log pour diagnostic Supabase
        log_path = r"C:\Users\alexi\GIT\NovaFlow\backend\db_audit.log"
        from datetime import datetime
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now()}] DELETE_ACTION: user_id={user_id}, deleted_count={deleted_count}\n")
        except:
            pass
        
        # Libérer l'espace disque si on utilise SQLite
        try:
            if db.get_bind().dialect.name == 'sqlite':
                db.execute("VACUUM")
                print("[DB DEBUG] clear_chat_history: VACUUM executed successfully.")
        except Exception as e:
            print(f"[DB DEBUG] clear_chat_history: VACUUM check/execution failed: {e}")

        print(f"[DB DEBUG] clear_chat_history: Deleted {deleted_count} messages for user_id={user_id}")
        return deleted_count
