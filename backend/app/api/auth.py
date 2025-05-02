from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from ..core.config import settings
import httpx
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

class CallbackRequest(BaseModel):
    code: str

@router.get("/auth/github")
async def github_auth():
    """Redirect to GitHub OAuth page"""
    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?client_id={settings.GITHUB_CLIENT_ID}&scope=repo"
    )

@router.post("/auth/github/callback")
@router.get("/auth/github/callback")
async def github_callback(request: Request, code: Optional[str] = None):
    """Handle GitHub OAuth callback"""
    try:
        # Get code from either query params (GET) or request body (POST)
        if not code:
            body = await request.json()
            code = body.get("code")
        
        if not code:
            raise HTTPException(
                status_code=400,
                detail="No code provided"
            )
        
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                json={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code
                },
                headers={"Accept": "application/json"}
            )
            data = response.json()
            
            if "access_token" not in data:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to get access token from GitHub"
                )
            
            return {"access_token": data["access_token"]}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during GitHub authentication: {str(e)}"
        ) 