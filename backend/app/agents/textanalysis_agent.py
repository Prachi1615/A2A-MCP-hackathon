class TextAnalysisAgent:
    def analyze_text(self, repo_data):
        """Performs text/documentation analysis on the repository data."""
        # Example: Return README and issues summary if available
        return {
            'readme': repo_data.get('text_content', {}).get('readme', ''),
            'issues': repo_data.get('open_issues', [])
        }

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
