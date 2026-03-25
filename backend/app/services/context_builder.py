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
            # Filtrer les événements futurs (prochains 14 jours)
            future_events = []
            for e in events:
                try:
                    start_dt = datetime.datetime.fromisoformat(e.start.replace('Z', '+00:00'))
                    if now <= start_dt <= now + datetime.timedelta(days=14):
                        future_events.append(e)
                except:
                    # Si format date bizarre, on l'inclut quand même si c'est récent
                    future_events.append(e)
            
            if future_events:
                # Trier par date
                try:
                    future_events.sort(key=lambda x: x.start)
                except: pass
                
                cal_ctx = "## Mon Calendrier (14 prochains jours)\n"
                for e in future_events[:15]: # Max 15 événements pour pas saturer
                    cal_ctx += f"- {e.title} (Date: {e.start}, Source: {e.source})\n"
                context_parts.append(cal_ctx)

        return "\n\n".join(context_parts)

    @staticmethod
    def build_course_context(course_id: str, user_query: str, filenames: Optional[List[str]] = None) -> str:
        """Construit le contexte spécifique pour un cours (Second Brain)."""
        context_parts = []
        
        # 1. RAG (Documents du cours)
        rag_context = query_rag(user_query, n_results=5, course_id=course_id, filenames=filenames)
        if rag_context:
            context_parts.append(f"## Extraits des documents du cours\n{rag_context}")
        else:
            context_parts.append("## Documents\nAucun extrait pertinent trouvé dans les documents sélectionnés pour ce cours.")

        # 2. Tâches liées au cours
        tasks = TaskManager.instance().get_all_tasks()
        course_tasks = [t for t in tasks if str(t.get("course_id")) == str(course_id) and not t.get("done")]
        if course_tasks:
            task_ctx = "## Tâches liées à ce cours\n"
            for t in course_tasks:
                task_ctx += f"- {t['title']} (Échéance: {t.get('due_date', 'N/A')})\n"
            context_parts.append(task_ctx)

        # 3. Événements liés au cours
        events = EventManager.instance().get_all_events()
        course_events = [e for e in events if str(getattr(e, 'course_id', '')) == str(course_id) or course_id in e.external_id]
        if course_events:
            cal_ctx = "## Événements liés à ce cours\n"
            for e in course_events[:10]:
                cal_ctx += f"- {e.title} (Date: {e.start})\n"
            context_parts.append(cal_ctx)

        return "\n\n".join(context_parts)
