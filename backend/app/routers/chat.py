from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import ClinicalStaff
from app.models import ChatConversation, ChatMessage, User
from app.schemas import (
    ChatConversationCreate,
    ChatConversationRead,
    ChatConversationRename,
    ChatConversationSummary,
    ChatMessageSend,
    ChatSendResponse,
)
from app.services.chat_assistant import ChatAssistantService


router = APIRouter()
assistant = ChatAssistantService()


def _conversation_or_404(db: Session, conversation_id: int, user: User) -> ChatConversation:
    conversation = db.scalar(
        select(ChatConversation)
        .where(ChatConversation.id == conversation_id, ChatConversation.user_id == user.id)
        .options(selectinload(ChatConversation.messages))
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


def _default_title(message: str) -> str:
    compact = " ".join(message.split())
    return compact[:70] or "New conversation"


@router.post("/conversations", response_model=ChatConversationRead)
def create_conversation(payload: ChatConversationCreate, db: Session = Depends(get_db), user: User = ClinicalStaff) -> ChatConversation:
    conversation = ChatConversation(user_id=user.id, role=user.role, title=payload.title or "New conversation")
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[ChatConversationSummary])
def list_conversations(q: str | None = None, db: Session = Depends(get_db), user: User = ClinicalStaff) -> list[ChatConversationSummary]:
    stmt = select(ChatConversation).where(ChatConversation.user_id == user.id).order_by(ChatConversation.updated_at.desc())
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                ChatConversation.title.ilike(like),
                ChatConversation.messages.any(ChatMessage.content.ilike(like)),
            )
        )
    conversations = db.scalars(stmt.limit(50)).all()
    summaries: list[ChatConversationSummary] = []
    for conversation in conversations:
        last_message = db.scalar(
            select(ChatMessage.content)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        summaries.append(
            ChatConversationSummary(
                id=conversation.id,
                title=conversation.title,
                role=conversation.role,
                updated_at=conversation.updated_at,
                last_message=last_message,
            )
        )
    return summaries


@router.get("/conversations/{conversation_id}", response_model=ChatConversationRead)
def get_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = ClinicalStaff) -> ChatConversation:
    return _conversation_or_404(db, conversation_id, user)


@router.patch("/conversations/{conversation_id}", response_model=ChatConversationRead)
def rename_conversation(
    conversation_id: int,
    payload: ChatConversationRename,
    db: Session = Depends(get_db),
    user: User = ClinicalStaff,
) -> ChatConversation:
    conversation = _conversation_or_404(db, conversation_id, user)
    conversation.title = payload.title
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: int, db: Session = Depends(get_db), user: User = ClinicalStaff) -> None:
    conversation = _conversation_or_404(db, conversation_id, user)
    db.delete(conversation)
    db.commit()


@router.post("/messages", response_model=ChatSendResponse)
def send_message(payload: ChatMessageSend, db: Session = Depends(get_db), user: User = ClinicalStaff) -> ChatSendResponse:
    if payload.conversation_id:
        conversation = _conversation_or_404(db, payload.conversation_id, user)
    else:
        conversation = ChatConversation(user_id=user.id, role=user.role, title=_default_title(payload.message))
        db.add(conversation)
        db.flush()

    if conversation.title == "New conversation":
        conversation.title = _default_title(payload.message)

    user_message = ChatMessage(conversation_id=conversation.id, user_id=user.id, role="user", content=payload.message)
    db.add(user_message)
    answer, data_source = assistant.answer(db, user, payload.message)
    assistant_message = ChatMessage(
        conversation_id=conversation.id,
        user_id=user.id,
        role="assistant",
        content=answer,
        data_source=data_source,
    )
    db.add(assistant_message)
    db.commit()
    conversation = _conversation_or_404(db, conversation.id, user)
    return ChatSendResponse(conversation=conversation, answer=assistant_message)
