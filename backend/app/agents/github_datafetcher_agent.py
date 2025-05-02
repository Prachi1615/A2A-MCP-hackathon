# GitHub DataFetcher Agent
# Responsible for all interactions with the GitHub API.

import os
import requests
from datetime import datetime, timedelta, timezone
from github import Github
import time

class GitHubDataFetcherAgent:
    """Handles all GitHub API interactions and data fetching."""

    def __init__(self, token=None):
        """Initialize with GitHub API token."""
        self.base_url = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        self.token = token
        self.github = None

        # Set up authentication
        if token:
            self.headers["Authorization"] = f"token {token}"
            try:
                self.github = Github(token)
                self.github.get_user().login  # Test connection
            except Exception as e:
                print(f"Warning: Failed to initialize PyGithub with token: {e}")
                self.github = Github()  # Fallback to unauthenticated
        elif os.environ.get("YOUR_GITHUB_TOKEN"):
            self.token = os.environ.get("YOUR_GITHUB_TOKEN")
            self.headers["Authorization"] = f"token {self.token}"
            try:
                self.github = Github(self.token)
                self.github.get_user().login  # Test connection
            except Exception as e:
                print(f"Warning: Failed to initialize PyGithub with token: {e}")
                self.github = Github()  # Fallback to unauthenticated
        else:
            print("Warning: No GitHub token provided. API rate limits will be restricted.")
            self.github = Github()

        # Configure rate limit handling
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = datetime.now(timezone.utc)
        
        # Initialize rate limit info if possible
        if self.github:
            try:
                # Test the token by making a simple API call
                user = self.github.get_user().login
                print(f"Successfully authenticated as: {user}")
            except Exception as e:
                print(f"Warning: Could not authenticate with GitHub: {e}")

                self.rate_limit_reset = datetime.now(timezone.utc)

    def _check_rate_limit(self):
        """Check API rate limit and wait if necessary."""
        if self.rate_limit_remaining <= 10:
            reset_time = self.rate_limit_reset
            current_time = datetime.now(timezone.utc)
            if reset_time > current_time:
                wait_time = (reset_time - current_time).total_seconds() + 10
                print(f"Rate limit nearly exhausted. Waiting {wait_time:.0f} seconds for reset.")
                time.sleep(wait_time)

        response = requests.get(f"{self.base_url}/rate_limit", headers=self.headers)
        if response.status_code == 200:
            rate_data = response.json()
            self.rate_limit_remaining = rate_data["resources"]["core"]["remaining"]
            self.rate_limit_reset = datetime.fromtimestamp(rate_data["resources"]["core"]["reset"], tz=timezone.utc)

    def fetch_repo_data(self, owner, repo):
        """Fetch all relevant data about a repository."""
        try:
            # Get basic repository information
            repo_info = self.get_repo_info(owner, repo)
            if not repo_info:
                print(f"Could not retrieve repository information for {owner}/{repo}")
                return None

            # Fetch additional data
            languages = self.get_languages(owner, repo)
            contributors = self.get_contributors(owner, repo)
            commits = self.get_recent_commits(owner, repo)
            issues = self.get_recent_issues(owner, repo)
            pull_requests = self.get_recent_pull_requests(owner, repo)

            return {
                "basic_info": repo_info,
                "languages": languages,
                "contributors": contributors,
                "recent_commits": commits,
                "recent_issues": issues,
                "recent_pull_requests": pull_requests
            }

        except Exception as e:
            print(f"Error fetching repository data: {str(e)}")
            return None

    def get_repo_info(self, owner, repo):
        """Get basic repository information."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            return {
                "id": github_repo.id,
                "name": github_repo.name,
                "full_name": github_repo.full_name,
                "description": github_repo.description,
                "url": github_repo.html_url,
                "created_at": github_repo.created_at.isoformat(),
                "updated_at": github_repo.updated_at.isoformat(),
                "pushed_at": github_repo.pushed_at.isoformat() if github_repo.pushed_at else None,
                "size": github_repo.size,
                "stargazers_count": github_repo.stargazers_count,
                "watchers_count": github_repo.watchers_count,
                "forks_count": github_repo.forks_count,
                "open_issues_count": github_repo.open_issues_count,
                "default_branch": github_repo.default_branch,
                "owner": {
                    "login": github_repo.owner.login,
                    "id": github_repo.owner.id,
                    "url": github_repo.owner.html_url
                }
            }
        except Exception as e:
            print(f"Error getting repository info: {str(e)}")
            return None

    def get_languages(self, owner, repo):
        """Get languages used in the repository."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            return github_repo.get_languages()
        except Exception as e:
            print(f"Error getting languages: {str(e)}")
            return {}

    def get_contributors(self, owner, repo, max_contributors=None):
        """Get repository contributors."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            contributors = github_repo.get_contributors()
            result = []
            for contributor in contributors:
                result.append({
                    "login": contributor.login,
                    "id": contributor.id,
                    "contributions": contributor.contributions,
                    "url": contributor.html_url
                })
                if max_contributors and len(result) >= max_contributors:
                    break
            return result
        except Exception as e:
            print(f"Error getting contributors: {str(e)}")
            return []

    def get_recent_commits(self, owner, repo, days=30):
        """Get recent commits from the repository."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            since = datetime.now() - timedelta(days=days)
            commits = github_repo.get_commits(since=since)
            result = []
            for commit in commits:
                result.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name,
                    "date": commit.commit.author.date.isoformat(),
                    "url": commit.html_url
                })
            return result
        except Exception as e:
            print(f"Error getting commits: {str(e)}")
            return []

    def fetch_recent_pull_requests(self, owner, repo, days_back=30, max_prs=100):
        """Fetch recent pull requests from the repository."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            since = datetime.now(tz=tz.tzutc()) - timedelta(days=days_back)
            prs = github_repo.get_pulls(state='all', sort='created', direction='desc')
            recent_prs = []
            for pr in prs:
                if pr.created_at < since or len(recent_prs) >= max_prs:
                    break
                recent_prs.append({
                    'number': pr.number,
                    'title': pr.title,
                    'state': pr.state,
                    'created_at': pr.created_at.replace(tzinfo=tz.tzutc()),
                    'updated_at': pr.updated_at.replace(tzinfo=tz.tzutc()) if pr.updated_at else None,
                    'merged_at': pr.merged_at.replace(tzinfo=tz.tzutc()) if pr.merged_at else None,
                    'author': pr.user.login if pr.user else None,
                    'url': pr.html_url
                })
            return recent_prs
        except Exception as e:
            print(f"Error getting pull requests: {str(e)}")
            return []

    def get_recent_pull_requests(self, owner, repo, state="all", days=30):
        """Get recent pull requests from the repository."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            since = datetime.now(timezone.utc) - timedelta(days=days)
            pulls = github_repo.get_pulls(state=state)
            result = []
            for pr in pulls:
                if pr.created_at >= since:
                    result.append({
                        "number": pr.number,
                        "title": pr.title,
                        "state": pr.state,
                        "created_at": pr.created_at.replace(tzinfo=timezone.utc),
                        "updated_at": pr.updated_at.replace(tzinfo=timezone.utc) if pr.updated_at else None,
                        "closed_at": pr.closed_at.replace(tzinfo=timezone.utc) if pr.closed_at else None,
                        "merged_at": pr.merged_at.replace(tzinfo=timezone.utc) if pr.merged_at else None,
                        "author": pr.user.login,
                        "url": pr.html_url,
                        "additions": pr.additions,
                        "deletions": pr.deletions,
                        "changed_files": pr.changed_files
                    })
            return result
        except Exception as e:
            print(f"Error getting pull requests: {str(e)}")
            return []

    def get_recent_issues(self, owner, repo, state="all", days=30):
        """Get recent issues from the repository."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            since = datetime.now(timezone.utc) - timedelta(days=days)
            issues = github_repo.get_issues(state=state, since=since)
            result = []
            for issue in issues:
                if not issue.pull_request:  # Exclude pull requests
                    result.append({
                        "number": issue.number,
                        "title": issue.title,
                        "state": issue.state,
                        "created_at": issue.created_at.replace(tzinfo=timezone.utc),
                        "updated_at": issue.updated_at.replace(tzinfo=timezone.utc) if issue.updated_at else None,
                        "closed_at": issue.closed_at.replace(tzinfo=timezone.utc) if issue.closed_at else None,
                        "author": issue.user.login if issue.user else None,
                        "url": issue.html_url
                    })
            return result
        except Exception as e:
            print(f"Error getting issues: {str(e)}")
            return []

    def get_file_content(self, owner, repo, path, ref=None):
        """Get the content of a file from the repository."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            content = github_repo.get_contents(path, ref=ref)
            if isinstance(content, list):
                return None  # This is a directory
            return {
                "content": content.decoded_content.decode('utf-8'),
                "sha": content.sha,
                "size": content.size,
                "type": content.type,
                "url": content.html_url
            }
        except Exception as e:
            print(f"Error getting file content: {str(e)}")
            return None

    def _get_repo_summary_for_llm(self, repo_data, max_contributors=5, max_languages=5):
        """Prepare a concise summary of the repository's metadata and key stats for LLM input."""
        basic_info = repo_data.get('basic_info', {})
        languages = repo_data.get('languages', {})
        contributors = repo_data.get('contributors', [])
        commits = repo_data.get('recent_commits', [])
        issues = repo_data.get('recent_issues', [])
        prs = repo_data.get('recent_pull_requests', [])

        summary = []
        summary.append(f"# Repository: {basic_info.get('full_name', 'Unknown')}")
        summary.append(f"Description: {basic_info.get('description', 'No description')}")
        summary.append(f"Stars: {basic_info.get('stargazers_count', 0)} | Forks: {basic_info.get('forks_count', 0)} | Open Issues: {basic_info.get('open_issues_count', 0)}")
        summary.append(f"Created: {basic_info.get('created_at', 'N/A')} | Updated: {basic_info.get('updated_at', 'N/A')}")
        summary.append("")

        summary.append(f"## Top Languages (up to {max_languages}):")
        if languages:
            for i, (lang, bytes_count) in enumerate(list(languages.items())[:max_languages]):
                summary.append(f"{i+1}. {lang} ({bytes_count} bytes)")
            if len(languages) > max_languages:
                summary.append(f"...and {len(languages) - max_languages} more languages not shown.")
        else:
            summary.append("No language data found.")
        summary.append("")

        summary.append(f"## Top Contributors (up to {max_contributors}):")
        if contributors:
            for i, contrib in enumerate(contributors[:max_contributors]):
                name = contrib.get('login', 'Unknown')
                count = contrib.get('contributions', 0)
                summary.append(f"{i+1}. {name} ({count} contributions)")
            if len(contributors) > max_contributors:
                summary.append(f"...and {len(contributors) - max_contributors} more contributors not shown.")
        else:
            summary.append("No contributor data found.")
        summary.append("")

        summary.append("## Recent Activity:")
        if commits:
            summary.append(f"Recent Commits: {len(commits)}")
            for commit in commits[:3]:
                summary.append(f"- {commit['message'][:100]}..." if len(commit['message']) > 100 else f"- {commit['message']}")
        if issues:
            summary.append(f"Recent Issues: {len(issues)}")
        if prs:
            summary.append(f"Recent PRs: {len(prs)}")

        return '\n'.join(summary)
