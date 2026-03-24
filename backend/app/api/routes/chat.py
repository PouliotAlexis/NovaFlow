from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import re
import os
from app.services.rag_engine.ingest import query_rag
from app.services.ai_engine import chat_stream
from app.core.config import settings
from app.services.task_manager import TaskManager
from app.services.event_manager import EventManager

router = APIRouter()

def get_or_create_course_event(course_id: str) -> Optional[str]:
    """Trouve ou crée un événement pivot pour associer les tâches d'un cours."""
    if not course_id:
        return None
    
    em = EventManager.instance()
    ext_id = f"moodle_course_{course_id}"
    
    # 1. Vérifier si l'événement existe déjà (on check les deux sources possibles pour la transition)
    existing = em.get_event_by_external_id(ext_id, "moodle_ai") or em.get_event_by_external_id(ext_id, "moodle")
    if existing:
        return existing.id
    
    # 2. Sinon, essayer de trouver le nom du cours
    course_name = f"Cours {course_id}"
    try:
        # Tenter de lire le dossier de téléchargement Moodle
        moodle_dir = os.path.join(settings.MOODLE_DOWNLOADS_DESTINATION, course_id)
        info_path = os.path.join(moodle_dir, "course_info.json")
        if os.path.exists(info_path):
            with open(info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
                course_name = info.get("fullname") or info.get("name") or course_name
    except Exception as e:
        print(f"⚠️ Erreur récupération nom du cours {course_id}: {e}")

    # 3. Créer l'événement pivot
    from datetime import datetime
    now_iso = datetime.now().isoformat()
    new_event = em.create_event(
        external_id=ext_id,
        source="moodle_ai", # Source spécifique pour ne pas être filtré par l'aggregator (qui exclut "moodle" pur)
        title=course_name,
        start=now_iso,
        updated=now_iso,
        desc_hash="ai_pivot_event"
    )
    # On ajoute une catégorie pour le filtrage frontend
    em.update_event(new_event.id, {"category": course_name})
    
    # Debug log pour confirmer la création
    print(f"📌 Pivot event created: {new_event.id} ({course_name}) with source 'moodle_ai'")
    
    return new_event.id

class ChatMessage(BaseModel):
    role: str
    content: str

class CourseChatRequest(BaseModel):
    messages: List[ChatMessage]
    course_id: Optional[str] = None
    use_rag: Optional[bool] = True

@router.post("/chat")
async def chat_endpoint(request: CourseChatRequest):
    """
    Endpoint de chat compatible avec Vercel AI SDK (Streaming).
    """
    try:
        # Le SDK Vercel AI envoie une liste 'messages'
        user_message = request.messages[-1].content if request.messages else ""
        
        context = ""
        if request.use_rag and user_message:
            # Recherche RAG avec filtre par cours
            context = query_rag(user_message, course_id=request.course_id)
        
        async def generate():
            full_response = ""
            try:
                async for token in chat_stream(
                    prompt=user_message,
                    context=context,
                    mode=settings.AI_MODE
                ):
                    full_response += token
                    # Data Stream Protocol : channel 0 pour le texte
                    yield f"0:{json.dumps(token)}\n"
                
                # Post-processing for tasks
                task_pattern = r"\[TASK:\s*(.*?)\]"
                tasks_to_create = re.findall(task_pattern, full_response, re.IGNORECASE)
                
                # Récupérer l'événement parent pour le cours
                parent_id = None
                if request.course_id:
                    parent_id = get_or_create_course_event(request.course_id)

                for task_title in tasks_to_create:
                    print(f"✨ SecondBrain AI Stream Action: Creating task '{task_title}' associated with course {request.course_id}")
                    TaskManager.instance().add_task(
                        title=task_title, 
                        priority="medium", 
                        meta=f"AI Generated ({request.course_id})",
                        parent_event_id=parent_id
                    )
                
                # On pourrait envoyer un message spécial "done" ou une annotation si le protocole le permet
                # Pour l'instant on se contente de l'action côté serveur et l'utilisateur verra la confirmation au prochain refresh ou via un message final
            except Exception as e:
                yield f'3:{json.dumps({"message": str(e)})}\n' # channel 3 pour les erreurs

        return StreamingResponse(
            generate(),
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
