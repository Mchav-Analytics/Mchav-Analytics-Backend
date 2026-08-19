# app/api/v1/controllers/ai_controller.py
# Controlador HTTP para la interacción conversacional en tiempo real con la IA de Google Gemini

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
import app.models as models
from app.services.gemini_service import chat_with_gemini

router = APIRouter(dependencies=[Depends(get_current_user)])


class ChatMessageRequest(BaseModel):
    message: str
    project_id: Optional[str] = "PROJ-01"
    history: Optional[List[Dict[str, str]]] = []


@router.post("/chat")
def chat_with_ai(
    payload: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    POST /api/v1/ai/chat
    Recibe un mensaje del usuario y responde utilizando el motor conversacional de Google Gemini API (gemini-2.5-flash).
    """
    user_name = current_user.nombre if current_user and current_user.nombre else (current_user.email if current_user else "Usuario")
    
    context_info = {
        "id_proyecto": payload.project_id or "PROJ-01",
        "user_name": user_name,
        "health_score": 88,
        "cycle_time": 2.4,
        "wip": 2
    }

    reply_text = chat_with_gemini(
        user_message=payload.message,
        context_info=context_info,
        conversation_history=payload.history
    )

    return {
        "reply": reply_text,
        "status": "success"
    }


@router.get("/prompts")
def get_suggested_prompts():
    """
    GET /api/v1/ai/prompts
    Retorna preguntas sugeridas para el chat con la IA.
    """
    return [
        {"id": 1, "text": "¿Cuál es la salud actual de nuestro sprint?", "category": "Rendimiento"},
        {"id": 2, "text": "¿Cómo podemos reducir el Cycle Time en el equipo?", "category": "Agilidad"},
        {"id": 3, "text": "¿Qué cuellos de botella tenemos activos en QA o Review?", "category": "Bloqueos"},
        {"id": 4, "text": "¿Qué recomendaciones tienes para el próximo sprint?", "category": "Estrategia"}
    ]
