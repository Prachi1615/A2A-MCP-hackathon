from datetime import timedelta
from temporalio import workflow
from typing import Dict, List, Any, Optional

# Import the activities within the workflow's sandbox context
with workflow.unsafe.imports_passed_through():
    from activities import (
        get_repo_info, get_contributors, get_commits,
        get_branches, get_issues, get_pull_requests, get_pr_timeline, get_readme
    )

@workflow.defn
class GitHubRepoAnalysisWorkflow:
    @workflow.run
    async def run(self, owner: str, repo: str) -> Dict[str, Any]:
        """Analyze a GitHub repository and return comprehensive information."""
        # Get basic repository information
        repo_info = await workflow.execute_activity(
            get_repo_info,
            args=[owner, repo],
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Get repository contributors
        contributors = await workflow.execute_activity(
            get_contributors,
            args=[owner, repo, 10],  # max_contributors=10
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Get recent commits
        commits = await workflow.execute_activity(
            get_commits,
            args=[owner, repo, {"per_page": 10}, 10],  # params and max_commits
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Get repository branches
        branches = await workflow.execute_activity(
            get_branches,
            args=[owner, repo],
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Get repository issues
        issues = await workflow.execute_activity(
            get_issues,
            args=[owner, repo, "all", 3, None],  # state, max_issues, params
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Get repository pull requests
        pull_requests = await workflow.execute_activity(
            get_pull_requests,
            args=[owner, repo, "all", 3, None],  # state, max_prs, params
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Get PR timeline metrics
        pr_timeline = await workflow.execute_activity(
            get_pr_timeline,
            args=[owner, repo, 3],  # days_back=10 (analyzing last 10 days)
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        # Get README content
        readme = await workflow.execute_activity(
            get_readme,
            args=[owner, repo],
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Compile all information into a single comprehensive result
        result = {
            "repository": repo_info,
            "contributors": contributors,
            "commits": commits,
            "branches": branches,
            "issues": issues,
            "pull_requests": pull_requests,
            "pr_timeline": pr_timeline,
            "readme": readme
        }
        
        return result
