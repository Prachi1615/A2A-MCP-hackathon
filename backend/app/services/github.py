import requests
import json
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from ..core.config import settings
from ..models.repository import Repository
from . import githubRepoInfo

class GitHubService:
    def __init__(self):
        self.base_url = settings.GITHUB_API_URL

    async def validate_repository_access(self, repo_url: str, access_token: Optional[str] = None) -> Repository:
        try:
            # Extract owner and repo name from URL
            parts = repo_url.strip('/').split('/')
            if len(parts) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid repository URL"
                )
            
            owner, repo = parts[-2], parts[-1]
            
            # Make request to GitHub API
            headers = {}
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
            
            response = requests.get(
                f"{self.base_url}/repos/{owner}/{repo}",
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not access repository"
                )
            
            repo_data = response.json()
            # analyser = githubRepoInfo.GitHubRepoInfo(access_token)
            # all_info = analyser.get_all_info(owner, repo)
            # repo_data = all_info['basic_info']

            
            return Repository(
                id=repo_data["id"],
                name=repo_data["name"],
                full_name=repo_data["full_name"],
                description=repo_data.get("description"),
                private=repo_data["private"],
                html_url=repo_data["html_url"],
                default_branch=repo_data["default_branch"],
                owner=repo_data["owner"]["login"],
                details=json.dumps(repo_data)
            )
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="GitHub API is currently unavailable"
            )

github_service = GitHubService() 