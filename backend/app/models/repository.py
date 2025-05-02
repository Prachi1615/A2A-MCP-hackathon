from pydantic import BaseModel, HttpUrl
from typing import Optional

class RepositoryBase(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool
    html_url: HttpUrl
    default_branch: str
    details: Optional[str] = None

class RepositoryCreate(BaseModel):
    repository_url: str
    access_token: Optional[str] = None

class Repository(RepositoryBase):
    id: int
    owner: str

    class Config:
        from_attributes = True 