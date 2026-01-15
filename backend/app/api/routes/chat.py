"""
Rotas da API para chat com o Gemini AI.

Este módulo expõe endpoints para criar sessões de chat,
enviar mensagens e consultar histórico.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from app.api.dependencies import get_db
from app.models.chat_session import ChatSession
from app.models.message import Message
from app.models.municipality import Municipality
from app.schemas.request_schemas import (
    ChatRequest,
    GeminiResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    MessageResponse,
)
from app.services.gemini_orchestrator import get_gemini_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


# ========== Dependências ==========

def get_orchestrator():
    """Dependência para obter o orquestrador Gemini."""
    return get_gemini_orchestrator()


# ========== Endpoints de Sessões ==========

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    session_data: ChatSessionCreate,
    db: Session = Depends(get_db)
):
    """
    Cria uma nova sessão de chat.

    - **municipality_id**: ID do município para contexto
    - **title**: Título opcional da sessão
    """
    try:
        # Verificar se município existe
        municipality = db.query(Municipality).filter(
            Municipality.id == session_data.municipality_id
        ).first()

        if not municipality:
            raise HTTPException(
                status_code=404,
                detail=f"Município com ID {session_data.municipality_id} não encontrado"
            )

        # Criar sessão
        chat_session = ChatSession(
            municipality_id=session_data.municipality_id,
            title=session_data.title or f"Chat - {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}",
            created_at=datetime.utcnow()
        )

        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)

        logger.info(f"Sessão de chat criada: {chat_session.id} para município {municipality.name}")

        return ChatSessionResponse(
            id=chat_session.id,
            municipality_id=chat_session.municipality_id,
            title=chat_session.title,
            created_at=chat_session.created_at,
            message_count=0
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao criar sessão de chat: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao criar sessão de chat: {str(e)}"
        )


@router.get("/sessions", response_model=List[ChatSessionResponse])
def list_chat_sessions(
    municipality_id: int = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Lista sessões de chat.

    - **municipality_id**: Filtrar por município (opcional)
    - **limit**: Número máximo de resultados
    - **offset**: Offset para paginação
    """
    try:
        query = db.query(ChatSession)

        if municipality_id:
            query = query.filter(ChatSession.municipality_id == municipality_id)

        query = query.order_by(ChatSession.created_at.desc())
        sessions = query.offset(offset).limit(limit).all()

        return [
            ChatSessionResponse(
                id=session.id,
                municipality_id=session.municipality_id,
                title=session.title,
                created_at=session.created_at,
                message_count=len(session.messages)
            )
            for session in sessions
        ]

    except Exception as e:
        logger.error(f"Erro ao listar sessões: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao listar sessões: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtém detalhes de uma sessão de chat.

    - **session_id**: ID da sessão (UUID)
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Sessão {session_id} não encontrada"
        )

    return ChatSessionResponse(
        id=session.id,
        municipality_id=session.municipality_id,
        title=session.title,
        created_at=session.created_at,
        message_count=len(session.messages)
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Deleta uma sessão de chat e todas as suas mensagens.

    - **session_id**: ID da sessão (UUID)
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Sessão {session_id} não encontrada"
        )

    # Deletar mensagens primeiro
    db.query(Message).filter(Message.session_id == session_id).delete()

    # Deletar sessão
    db.delete(session)
    db.commit()

    logger.info(f"Sessão {session_id} deletada")


# ========== Endpoints de Mensagens ==========

@router.post("/sessions/{session_id}/messages", response_model=GeminiResponse)
async def send_message(
    session_id: str,
    request: ChatRequest,
    db: Session = Depends(get_db),
    orchestrator = Depends(get_orchestrator)
):
    """
    Envia uma mensagem e recebe resposta do Gemini.

    - **session_id**: ID da sessão de chat (UUID)
    - **question**: Pergunta do usuário
    """
    try:
        # Verificar se sessão existe
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Sessão {session_id} não encontrada"
            )

        # Obter dados do município
        municipality = db.query(Municipality).filter(
            Municipality.id == session.municipality_id
        ).first()

        if not municipality:
            raise HTTPException(
                status_code=404,
                detail=f"Município {session.municipality_id} não encontrado"
            )

        municipality_data = {
            "id": municipality.id,
            "name": municipality.name,
            "state": municipality.state,
            "year": municipality.year
        }

        # Salvar mensagem do usuário
        user_message = Message(
            session_id=session_id,
            role="user",
            content=request.question,
            timestamp=datetime.utcnow()
        )
        db.add(user_message)
        db.commit()

        logger.info(f"Processando pergunta na sessão {session_id}: {request.question[:100]}")

        # Buscar histórico de mensagens (últimas 10)
        history_messages = db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.timestamp.asc()).limit(10).all()
        
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_messages
        ]

        # Processar pergunta com o orquestrador
        # 🚀 FASE 3: Query Planning + Hybrid Search + Explainable AI
        response = await orchestrator.process_question(
            question=request.question,
            session_id=str(session_id),
            municipality_data=municipality_data,
            chat_history=chat_history,
            db=db,  # Necessário para fase 3
            use_function_calling=False,  # Desabilitar function calling (usar Fase 3)
            use_phase3=True,  # 🚀 HABILITAR FASE 3
            message_id=str(user_message.id)  # Para lineage tracking
        )

        # Salvar resposta do assistente
        assistant_message = Message(
            session_id=session_id,
            role="assistant",
            content=response.model_dump_json(),  # Salvar JSON completo
            timestamp=datetime.utcnow()
        )
        db.add(assistant_message)
        db.commit()

        logger.info(f"Resposta gerada com sucesso para sessão {session_id}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
def get_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Obtém histórico de mensagens de uma sessão.

    - **session_id**: ID da sessão (UUID)
    - **limit**: Número máximo de mensagens
    - **offset**: Offset para paginação
    """
    # Verificar se sessão existe
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Sessão {session_id} não encontrada"
        )

    # Buscar mensagens
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(
        Message.timestamp.asc()
    ).offset(offset).limit(limit).all()

    return [
        MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp
        )
        for msg in messages
    ]


# ========== Endpoints Utilitários ==========

@router.get("/sessions/{session_id}/summary")
def get_session_summary(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtém resumo de uma sessão de chat.

    - **session_id**: ID da sessão (UUID)
    """
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Sessão {session_id} não encontrada"
        )

    messages = db.query(Message).filter(Message.session_id == session_id).all()

    user_messages = [m for m in messages if m.role == "user"]
    assistant_messages = [m for m in messages if m.role == "assistant"]

    return {
        "session_id": session.id,
        "title": session.title,
        "created_at": session.created_at,
        "total_messages": len(messages),
        "user_messages": len(user_messages),
        "assistant_messages": len(assistant_messages),
        "last_message": messages[-1].timestamp if messages else None
    }

