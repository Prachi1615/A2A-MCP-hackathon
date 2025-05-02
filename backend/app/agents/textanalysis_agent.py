import os
import base64
from collections import Counter
from datetime import datetime, timedelta, timezone
from github import Github

class TextAnalysisAgent:
    def __init__(self, token=None):
        """Initialize the TextAnalysisAgent."""
        self.text_extensions = {
            '.md', '.txt', '.rst', '.adoc', '.doc', '.docx',
            '.pdf', '.rtf', '.wiki', '.org', '.tex'
        }
        self.github = Github(token) if token else Github()

    def is_text_file(self, file_path):
        """Check if a file is a text file based on its extension."""
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.text_extensions

    def analyze_text(self, repo_data):
        """Performs text/documentation analysis on the repository data."""
        owner = repo_data.get('basic_info', {}).get('owner', {}).get('login')
        repo = repo_data.get('basic_info', {}).get('name')

        if not owner or not repo:
            return {
                'error': 'Missing repository owner or name',
                'readme': '',
                'documentation': [],
                'issues': []
            }

        readme = self.get_readme(owner, repo)
        docs = self.get_documentation_files(owner, repo)
        text_summary = self.get_repo_text_summary(readme, docs)

        # Get temporal analysis
        temporal = self.get_temporal_analysis(owner, repo)

        return {
            'readme': readme,
            'documentation': docs,
            'text_summary': text_summary,
            'temporal_analysis': temporal,
            'issues': repo_data.get('recent_issues', [])
        }

    def get_readme(self, owner, repo):
        """Get the repository's README content."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            readme = github_repo.get_readme()
            return base64.b64decode(readme.content).decode('utf-8')
        except Exception as e:
            print(f"Error getting README: {str(e)}")
            return ''

    def get_documentation_files(self, owner, repo):
        """Get documentation files from the repository."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            contents = github_repo.get_contents('')
            docs = []

            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(github_repo.get_contents(file_content.path))
                elif self.is_text_file(file_content.path):
                    docs.append({
                        'path': file_content.path,
                        'content': base64.b64decode(file_content.content).decode('utf-8'),
                        'size': file_content.size,
                        'url': file_content.html_url
                    })
            return docs
        except Exception as e:
            print(f"Error getting documentation files: {str(e)}")
            return []

    def get_repo_text_summary(self, readme, docs):
        """Generate a summary of repository text content."""
        summary = {
            'readme_length': len(readme) if readme else 0,
            'doc_files': len(docs),
            'total_doc_size': sum(doc['size'] for doc in docs),
            'doc_types': Counter(os.path.splitext(doc['path'])[1] for doc in docs)
        }
        return summary

    def _get_repo_summary_for_llm(self, repo_data, max_issues=5, max_readme_chars=1000):
        """
        Prepare a concise summary of the repository's documentation and issues for LLM input.
        Returns a string suitable for LLM prompt.
        """
        readme = repo_data.get('text_content', {}).get('readme', '')
        issues = repo_data.get('open_issues', [])
        summary = []
        summary.append("# Repository Documentation Summary\n")
        if readme:
            summary.append("## README (truncated):\n" + readme[:max_readme_chars])
            if len(readme) > max_readme_chars:
                summary.append("...\n")
        else:
            summary.append("No README found.\n")
        summary.append(f"\n## Open Issues (showing up to {max_issues}):")
        if issues:
            for i, issue in enumerate(issues[:max_issues]):
                title = issue.get('title', 'No title')
                url = issue.get('html_url', '')
                summary.append(f"{i+1}. {title} ({url})")
            if len(issues) > max_issues:
                summary.append(f"...and {len(issues) - max_issues} more issues not shown.")
        else:
            summary.append("No open issues found.")
        return '\n'.join(summary)

    def get_issue_timeline(self, owner, repo, days=365):
        """Get timeline of issue activity."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            since = datetime.now(timezone.utc) - timedelta(days=days)
            issues = github_repo.get_issues(state='all', since=since)
            timeline = []

            for issue in issues:
                if not issue.pull_request:  # Exclude pull requests
                    timeline.append({
                        'event': 'issue_created',
                        'date': issue.created_at.replace(tzinfo=timezone.utc),
                        'title': issue.title,
                        'number': issue.number,
                        'state': issue.state
                    })
                    if issue.closed_at:
                        timeline.append({
                            'event': 'issue_closed',
                            'date': issue.closed_at.replace(tzinfo=timezone.utc),
                            'title': issue.title,
                            'number': issue.number,
                            'state': issue.state
                        })
            return sorted(timeline, key=lambda x: x['date'])
        except Exception as e:
            print(f"Error getting issue timeline: {str(e)}")
            return []

    def get_pr_timeline(self, owner, repo, days=365):
        """Get timeline of pull request activity."""
        try:
            github_repo = self.github.get_repo(f"{owner}/{repo}")
            since = datetime.now(timezone.utc) - timedelta(days=days)
            pulls = github_repo.get_pulls(state='all')
            timeline = []

            for pr in pulls:
                if pr.created_at >= since:
                    timeline.append({
                        'event': 'pr_created',
                        'date': pr.created_at.replace(tzinfo=timezone.utc),
                        'title': pr.title,
                        'number': pr.number,
                        'state': pr.state
                    })
                    if pr.closed_at:
                        timeline.append({
                            'event': 'pr_closed',
                            'date': pr.closed_at.replace(tzinfo=timezone.utc),
                            'title': pr.title,
                            'number': pr.number,
                            'state': pr.state
                        })
                    if pr.merged_at:
                        timeline.append({
                            'event': 'pr_merged',
                            'date': pr.merged_at.replace(tzinfo=timezone.utc),
                            'title': pr.title,
                            'number': pr.number,
                            'state': pr.state
                        })
            return sorted(timeline, key=lambda x: x['date'])
        except Exception as e:
            print(f"Error getting PR timeline: {str(e)}")
            return []

    def get_temporal_analysis(self, owner, repo, days=365):
        """Get temporal analysis of repository activity."""
        try:
            issue_timeline = self.get_issue_timeline(owner, repo, days)
            pr_timeline = self.get_pr_timeline(owner, repo, days)

            # Combine and sort all events
            all_events = issue_timeline + pr_timeline
            all_events.sort(key=lambda x: x['date'])

            # Calculate activity metrics
            now = datetime.now(timezone.utc)
            start_date = now - timedelta(days=days)

            analysis = {
                'total_issues': len([e for e in issue_timeline if e['event'] == 'issue_created']),
                'closed_issues': len([e for e in issue_timeline if e['event'] == 'issue_closed']),
                'total_prs': len([e for e in pr_timeline if e['event'] == 'pr_created']),
                'merged_prs': len([e for e in pr_timeline if e['event'] == 'pr_merged']),
                'events_timeline': all_events,
                'time_range': {
                    'start': start_date,
                    'end': now
                }
            }

            return analysis
        except Exception as e:
            print(f"Error getting temporal analysis: {str(e)}")
            return None
