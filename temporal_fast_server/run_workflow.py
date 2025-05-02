import asyncio
import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from temporalio.client import Client
from workflows import GitHubRepoAnalysisWorkflow
import google.generativeai as genai
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up Google Generative AI
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

app = FastAPI(title="GitHub Repository Analysis API")

# Add CORS middleware to allow requests from your React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    owner: str
    repo: str

class MarkdownResponse(BaseModel):
    markdown: str
    raw_data: dict

@app.post("/api/analyze-repo")
async def analyze_repo(request: RepoRequest):
    try:
        # Connect to the Temporal server
        client = await Client.connect("localhost:7233")
        
        # Execute the workflow
        result = await client.execute_workflow(
            GitHubRepoAnalysisWorkflow.run,
            args=[request.owner, request.repo],
            id=f"github-analysis-{request.owner}-{request.repo}",
            task_queue="github-task-queue"
        )
        
        # Generate a markdown report from the result
        prompt = f"""
        Generate a comprehensive markdown report for GitHub repository {request.owner}/{request.repo}.
        Here's the data to include:

        Repository Information:
        {json.dumps(result.get('repository', {}), indent=2)}

        README Content:
        {result.get('readme', {}).get('content', 'No README found')}

        Contributors ({len(result.get('contributors', []))} total):
        {json.dumps(result.get('contributors', [])[:10], indent=2)}

        Recent Commits ({len(result.get('commits', []))} fetched):
        {json.dumps(result.get('commits', [])[:5], indent=2)}

        Branches ({len(result.get('branches', []))} total):
        {json.dumps(result.get('branches', []), indent=2)}

        Issues ({len(result.get('issues', []))} total):
        {json.dumps(result.get('issues', [])[:5], indent=2)}

        Pull Requests ({len(result.get('pull_requests', []))} total):
        {json.dumps(result.get('pull_requests', [])[:5], indent=2)}

        PR Timeline:
        {json.dumps(result.get('pr_timeline', {}), indent=2)}

        Format this into a professional, well-structured markdown report with sections, tables, and highlighted insights.
        Make it visually appealing and easy to navigate.
        """
        
        # Generate the markdown content asynchronously
        response = await asyncio.to_thread(
            lambda: model.generate_content(prompt).text
        )
        
        # Return both the markdown and raw data
        return MarkdownResponse(
            markdown=response,
            raw_data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# For development
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)