import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from workflows import GitHubRepoAnalysisWorkflow
from activities import (
    get_repo_info, get_contributors, get_commits,
    get_branches, get_issues, get_pull_requests, get_pr_timeline, get_readme
)

async def main():
    client = await Client.connect("localhost:7233")
    
    worker = Worker(
        client,
        task_queue="github-task-queue", # Task queue used in run_workflow.py
        workflows=[GitHubRepoAnalysisWorkflow],
        activities=[
            get_repo_info,
            get_contributors,
            get_commits,
            get_branches,
            get_issues,
            get_pull_requests,
            get_pr_timeline,
            get_readme
        ],
    )
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
