from app.database import engine
from app.models import ChatConversation, ChatMessage


def ensure_chat_schema() -> None:
    ChatConversation.__table__.create(bind=engine, checkfirst=True)
    ChatMessage.__table__.create(bind=engine, checkfirst=True)
