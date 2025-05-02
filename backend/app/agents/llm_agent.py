# LLM Agent (Rime/Gemini)
# Uses an LLM to generate summaries or insights.

import google.generativeai as genai

class LLMAgent:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generate_summary(self, repo_data, code_analysis, text_analysis):
        """Generates a summary using the LLM based on all analyses."""
        prompt = self._get_repo_summary_for_llm(repo_data, code_analysis, text_analysis)
        response = self.model.generate_content(prompt)
        return response.text

    def _get_repo_summary_for_llm(self, repo_data, code_analysis=None, text_analysis=None, max_issues=5, max_readme_chars=1000):
        """
        Prepare a concise, LLM-optimized summary string from repo_data, code_analysis, and text_analysis.
        Returns a string suitable for LLM prompt.
        """
        basic_info = repo_data.get('basic_info', {})
        languages = repo_data.get('languages', {})
        contributors = repo_data.get('contributors', [])
        readme = ''
        issues = []
        if text_analysis:
            readme = text_analysis.get('readme', '')
            issues = text_analysis.get('issues', [])
        summary = []
        summary.append(f"# Repository: {basic_info.get('full_name', 'Unknown')}")
        summary.append(f"Description: {basic_info.get('description', 'No description')}")
        summary.append(f"Stars: {basic_info.get('stargazers_count', 0)} | Forks: {basic_info.get('forks_count', 0)} | Open Issues: {basic_info.get('open_issues_count', 0)}")
        summary.append(f"Created: {basic_info.get('created_at', 'N/A')} | Updated: {basic_info.get('updated_at', 'N/A')}")
        summary.append("")
        if code_analysis:
            summary.append("## Code Metrics:")
            for k, v in code_analysis.items():
                summary.append(f"- {k}: {v}")
            summary.append("")
        summary.append("## README (truncated):")
        if readme:
            summary.append(readme[:max_readme_chars])
            if len(readme) > max_readme_chars:
                summary.append("...")
        else:
            summary.append("No README found.")
        summary.append("")
        summary.append(f"## Open Issues (showing up to {max_issues}):")
        if issues:
            for i, issue in enumerate(issues[:max_issues]):
                title = issue.get('title', 'No title')
                url = issue.get('html_url', '')
                summary.append(f"{i+1}. {title} ({url})")
            if len(issues) > max_issues:
                summary.append(f"...and {len(issues) - max_issues} more issues not shown.")
        else:
            summary.append("No open issues found.")
        if languages:
            summary.append("")
            summary.append("## Languages:")
            for lang, bytes_count in list(languages.items()):
                summary.append(f"- {lang}: {bytes_count} bytes")
        if contributors:
            summary.append("")
            summary.append("## Contributors:")
            for c in contributors[:5]:
                summary.append(f"- {c.get('login', 'Unknown')} ({c.get('contributions', 0)} contributions)")
        return '\n'.join(summary)
