from typing import List, Optional, Dict
from datetime import datetime
from fastapi import HTTPException, status
from ..models.conversation import Conversation, Message, ConversationCreate, MessageCreate
from ..models.repository import Repository, RepositoryCreate

class ConversationService:
    def __init__(self):
        self.conversations: Dict[int, Conversation] = {}
        self.messages: Dict[int, List[Message]] = {}

    async def create_conversation(self, repo: RepositoryCreate) -> Conversation:
        conversation = Conversation(
            id=len(self.conversations) + 1,
            repository_id=repo.repository_url,
            created_at=datetime.utcnow()
        )
        self.conversations[conversation.id] = conversation
        self.messages[conversation.id] = []
        return conversation

    async def get_conversation(self, conversation_id: int) -> Conversation:
        if conversation_id not in self.conversations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return self.conversations[conversation_id]

    async def add_message(self, conversation_id: int, message: MessageCreate) -> Message:
        conversation = await self.get_conversation(conversation_id)
        
        new_message = Message(
            id=len(self.messages[conversation_id]) + 1,
            conversation_id=conversation_id,
            **message.dict()
        )
        
        self.messages[conversation_id].append(new_message)
        return new_message

    async def get_messages(self, conversation_id: int) -> List[Message]:
        if conversation_id not in self.messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        return self.messages[conversation_id]

conversation_service = ConversationService() 