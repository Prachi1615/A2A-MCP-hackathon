from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MessageBase(BaseModel):
    text: str
    role: str
    timestamp: datetime

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    conversation_id: int

    class Config:
        from_attributes = True

class ConversationBase(BaseModel):
    repository_id: str

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: int
    created_at: datetime
    messages: List[Message] = []

    class Config:
        from_attributes = True 