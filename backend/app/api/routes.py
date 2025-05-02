from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from ..models.repository import Repository, RepositoryCreate
from ..models.conversation import Conversation, Message, MessageCreate
from ..services.github import github_service
from ..services.conversation import conversation_service
from . import auth
from pydantic import BaseModel

router = APIRouter()

# Include auth routes
router.include_router(auth.router, tags=["auth"])

@router.post("/setup/repository", response_model=Repository)
async def setup_repository(repo: RepositoryCreate):
    repository = await github_service.validate_repository_access(
        repo_url=repo.repository_url,
        access_token=repo.access_token
    )
    return repository

@router.post("/conversation/start", response_model=Conversation)
async def start_conversation(repo: RepositoryCreate):
    return await conversation_service.create_conversation(repo)

@router.get("/conversation/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: int):
    return await conversation_service.get_conversation(conversation_id)

@router.post("/conversation/{conversation_id}/message", response_model=Message)
async def add_message(conversation_id: int, message: MessageCreate):
    return await conversation_service.add_message(conversation_id, message)

@router.get("/conversation/{conversation_id}/messages", response_model=List[Message])
async def get_messages(conversation_id: int):
    return await conversation_service.get_messages(conversation_id) 