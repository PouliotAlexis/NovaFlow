"""
NovaFlow - Service Context Builder

Aggrège les informations de différentes sources (Tâches, Calendrier, RAG) 
pour construire un contexte riche à envoyer à l'IA.
"""

import datetime
from typing import List, Optional, Dict, Any
from app.services.task_manager import TaskManager
from app.services.event_manager import EventManager
from app.services.rag_engine.ingest import query_rag

class ContextBuilder:
    @staticmethod
    def build_global_context(user_query: str, include_tasks: bool = True, include_calendar: bool = True, include_rag: bool = True) -> str:
        """Construit le contexte pour le Chat Global."""
        context_parts = []
        
        # 1. Tâches
        if include_tasks:
            tasks = TaskManager.instance().get_all_tasks()
            # Filtrer les tâches non terminées
            pending_tasks = [t for t in tasks if not t.get("done", False)]
            if pending_tasks:
                task_ctx = "## Mes Tâches en cours\n"
                for t in pending_tasks:
                    priority = t.get("priority", "normale")
                    due = t.get("due_date", "Pas de date")
                    course = t.get("course_id", "Général")
                    task_ctx += f"- {t['title']} (Priorité: {priority}, Échéance: {due}, Cours: {course})\n"
                context_parts.append(task_ctx)

        # 2. Événements (via EventManager aggrégé)
        if include_calendar:
            events = EventManager.instance().get_all_events()
            now = datetime.datetime.now()
            future_events = []
            for e in events:
                try:
                    # Gestion robuste de la date (isoformat ou autre)
                    start_str = e.start if isinstance(e.start, str) else str(e.start)
                    start_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00').split('.')[0])
                    if now - datetime.timedelta(hours=24) <= start_dt <= now + datetime.timedelta(days=14):
                        future_events.append(e)
                except Exception as ex:
                    # En cas d'erreur de parsing date, on l'ignore silencieusement pour ne pas bloquer
                    continue
            
            if future_events:
                try:
                    future_events.sort(key=lambda x: x.start)
                except: pass
                
                cal_ctx = "## Mon Calendrier (14 prochains jours)\n"
                for e in future_events[:10]: # Réduit à 10 pour le global
                    cal_ctx += f"- {e.title} (Date: {e.start})\n"
                context_parts.append(cal_ctx)

        # Limite de sécurité globale (environ 3000 mots max pour le contexte global)
        final_context = "\n\n".join(context_parts)
        if len(final_context) > 8000:
            final_context = final_context[:8000] + "\n... [Contexte tronqué pour performance]"
            
        return final_context

    @staticmethod
    def build_course_context(course_id: Optional[str], user_query: str, filenames: Optional[List[str]] = None) -> str:
        """Construit le contexte spécifique pour un cours (Second Brain)."""
        context_parts = []
        
        # 1. RAG (Documents du cours) - On repasse à 5 pour la précision
        rag_context = query_rag(user_query, n_results=5, course_id=course_id, filenames=filenames)
        if rag_context:
            context_parts.append(f"## Extraits des documents du cours\n{rag_context}")
        else:
            context_parts.append("## Documents\nAucun extrait pertinent trouvé dans les documents sélectionnés pour ce cours.")

        if not course_id:
            return "\n\n".join(context_parts)

        # 2. Tâches liées au cours
        try:
            tasks = TaskManager.instance().get_all_tasks()
            course_tasks = [t for t in tasks if str(t.get("course_id", "")) == str(course_id) and not t.get("done")]
            if course_tasks:
                task_ctx = "## Tâches liées à ce cours\n"
                # On limite le nombre de tâches pour économiser du contexte si nécessaire
                for t in course_tasks[:8]: 
                    task_ctx += f"- {t['title']} (Échéance: {t.get('due_date', 'N/A')})\n"
                context_parts.append(task_ctx)
        except Exception: pass

        # 3. Événements liés au cours
        try:
            events = EventManager.instance().get_all_events()
            course_events = [e for e in events if str(getattr(e, 'course_id', '')) == str(course_id) or (course_id and course_id in e.external_id)]
            if course_events:
                cal_ctx = "## Événements liés à ce cours\n"
                for e in course_events[:5]:
                    cal_ctx += f"- {e.title} (Date: {e.start})\n"
                context_parts.append(cal_ctx)
        except Exception: pass

        # Budget intelligent (priorité au RAG qui est en début de liste)
        # 8000 chars est une limite sûre pour Ollama (Llama3/Mistral) avec une fenêtre de 4k tokens
        final_context = "\n\n".join(context_parts)
        if len(final_context) > 7500:
            # Si on dépasse, on tronque mais on garde les extraits RAG prioritaires
            # On coupe à la fin (là où se trouvent les tâches/événements moins critiques pour le Second Brain)
            final_context = final_context[:7500] + "\n... [Contexte tronqué pour limiter la charge]"
            
        return final_context
