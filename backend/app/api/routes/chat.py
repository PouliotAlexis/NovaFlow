from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import re
from app.services.rag_engine.ingest import query_rag
from app.services.ai_engine import chat_stream
from app.core.config import settings
from app.services.task_manager import task_manager

router = APIRouter()

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
                for task_title in tasks_to_create:
                    print(f"✨ SecondBrain AI Stream Action: Creating task '{task_title}'")
                    task_manager.add_task(title=task_title, priority="medium", meta="AI Generated (Course Chat)")
                
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
