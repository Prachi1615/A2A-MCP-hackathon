import requests
import base64
from datetime import datetime, timedelta
from temporalio import activity
from typing import Optional, List, Dict, Any
import pandas as pd

# Constants for GitHub API
BASE_URL = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github.v3+json"}

@activity.defn
async def get_repo_info(owner: str, repo: str) -> Optional[Dict[str, Any]]:
    url = f"{BASE_URL}/repos/{owner}/{repo}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error get_repo_info: {response.status_code}: {response.text}")
        return None

async def _paginated_get(url: str, params: Optional[Dict[str, Any]] = None, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
    """Handle paginated API responses with rate limit awareness."""
    if params is None:
        params = {}

    items = []
    page = 1
    per_page = min(100, params.get("per_page", 30))
    params["per_page"] = per_page

    while True:
        params["page"] = page
        response = requests.get(url, headers=HEADERS, params=params)

        if response.status_code == 200:
            page_items = response.json()
            if not page_items:
                break

            items.extend(page_items)
            page += 1

            # Check if we've reached the requested limit
            if max_items and len(items) >= max_items:
                return items[:max_items]

            # Check if we've reached the end (GitHub returns fewer items than requested)
            if len(page_items) < per_page:
                break
        else:
            print(f"Error {response.status_code}: {response.text}")
            break

    return items

@activity.defn
async def get_contributors(owner: str, repo: str, max_contributors: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get repository contributors with pagination support."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/contributors"
    return await _paginated_get(url, max_items=max_contributors)

@activity.defn
async def get_commits(owner: str, repo: str, params: Optional[Dict[str, Any]] = None, max_commits: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get commits with enhanced filtering and pagination."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
    return await _paginated_get(url, params=params, max_items=max_commits)

@activity.defn
async def get_branches(owner: str, repo: str) -> List[Dict[str, Any]]:
    """Get repository branches."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/branches"
    return await _paginated_get(url)

@activity.defn
async def get_issues(owner: str, repo: str, state: str = "all", max_issues: Optional[int] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Get repository issues with enhanced filtering."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/issues"
    if params is None:
        params = {}
    params["state"] = state
    return await _paginated_get(url, params=params, max_items=max_issues)

@activity.defn
async def get_pull_requests(owner: str, repo: str, state: str = "all", max_prs: Optional[int] = None, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Get repository pull requests with enhanced filtering."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls"
    if params is None:
        params = {}
    params["state"] = state
    return await _paginated_get(url, params=params, max_items=max_prs)

@activity.defn
async def get_pr_timeline(owner: str, repo: str, days_back: int = 180) -> Dict[str, Any]:
    """Analyze PR creation, closing, and metrics over time."""
    # Get PRs including closed and merged ones
    prs = await get_pull_requests(owner, repo, state="all")

    # Prepare timeline data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    # Initialize daily counters
    date_range = pd.date_range(start=start_date, end=end_date)
    created_counts = {d.strftime('%Y-%m-%d'): 0 for d in date_range}
    closed_counts = {d.strftime('%Y-%m-%d'): 0 for d in date_range}
    merged_counts = {d.strftime('%Y-%m-%d'): 0 for d in date_range}

    # Track metrics
    merge_times = []
    pr_sizes = []

    # Collect PR data
    for pr in prs:
        created_at = datetime.strptime(pr['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        if created_at >= start_date:
            created_counts[created_at.strftime('%Y-%m-%d')] += 1

            # Get PR size (additions + deletions)
            if pr.get('additions') is not None and pr.get('deletions') is not None:
                pr_sizes.append({
                    'additions': pr['additions'],
                    'deletions': pr['deletions'],
                    'total': pr['additions'] + pr['deletions'],
                    'files_changed': pr.get('changed_files', 0)
                })

        # Check if PR is closed
        if pr['state'] == 'closed':
            closed_at = datetime.strptime(pr['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
            if closed_at >= start_date:
                closed_counts[closed_at.strftime('%Y-%m-%d')] += 1

                # Check if PR was merged
                if pr['merged_at']:
                    merged_at = datetime.strptime(pr['merged_at'], '%Y-%m-%dT%H:%M:%SZ')
                    if merged_at >= start_date:
                        merged_counts[merged_at.strftime('%Y-%m-%d')] += 1

                        # Calculate time to merge
                        merge_time = (merged_at - created_at).total_seconds() / 3600  # hours
                        merge_times.append(merge_time)

    # Calculate acceptance rate
    total_closed = sum(closed_counts.values())
    total_merged = sum(merged_counts.values())
    acceptance_rate = (total_merged / total_closed) * 100 if total_closed > 0 else 0

    return {
        'created': created_counts,
        'closed': closed_counts,
        'merged': merged_counts,
        'merge_times': merge_times,
        'pr_sizes': pr_sizes,
        'acceptance_rate': acceptance_rate
    }

@activity.defn
async def get_readme(owner: str, repo: str, ref: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get repository README content."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/readme"
    params = {}
    if ref:
        params["ref"] = ref

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        data = response.json()
        if data.get("content"):
            content = base64.b64decode(data["content"]).decode("utf-8")
            return {
                "name": data["name"],
                "path": data["path"],
                "content": content
            }
        return data
    else:
        print(f"README not found or error: {response.status_code}")
        return None
