# Import necessary libraries (keep existing ones + add new ones)
import requests
import json
import os
import base64
import re
import ast
import networkx as nx
import radon.metrics as metrics
import radon.complexity as complexity
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from IPython.display import display, Markdown, HTML
import numpy as np
from github import Github, GithubException # PyGithub, add GithubException
import time
from dotenv import load_dotenv # For environment variables

# --- Neo4j and Gemini ---
from neo4j import GraphDatabase, basic_auth
import google.generativeai as genai

# --- GitHubRepoInfo Class ---
class GitHubRepoInfo:
    """Enhanced class to get comprehensive information about a GitHub repository."""

    def __init__(self, token=None):
        """Initialize with optional GitHub API token."""
        self.base_url = "https://api.github.com"
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        self.token = token
        self.github = None # Initialize github attribute

        # Set up authentication
        if token:
            self.headers["Authorization"] = f"token {token}"
            try:
                self.github = Github(token)
                self.github.get_user().login # Test connection
            except Exception as e:
                print(f"Warning: Failed to initialize PyGithub with token: {e}")
                self.github = Github() # Fallback to unauthenticated
        elif os.environ.get("GITHUB_TOKEN"):
            self.token = os.environ.get("GITHUB_TOKEN")
            self.headers["Authorization"] = f"token {self.token}"
            try:
                self.github = Github(self.token)
                self.github.get_user().login # Test connection
            except Exception as e:
                print(f"Warning: Failed to initialize PyGithub with token: {e}")
                self.github = Github() # Fallback to unauthenticated
        else:
            self.github = Github() # Unauthenticated

        # Configure rate limit handling
        self.rate_limit_remaining = 5000 # Assume higher limit if authenticated
        self.rate_limit_reset = datetime.now()
        # Initialize rate limit info if possible
        if self.github:
            try:
                 rate_limit = self.github.get_rate_limit()
                 self.rate_limit_remaining = rate_limit.core.remaining
                 self.rate_limit_reset = datetime.fromtimestamp(rate_limit.core.reset)
            except Exception as e:
                 print(f"Warning: Could not get initial rate limit from PyGithub: {e}")


    # --- Keep ALL existing methods from the original GitHubRepoInfo class ---
    # ... ( _check_rate_limit, _paginated_get, get_repo_info, get_contributors, ...)
    def _check_rate_limit(self):
        """Check API rate limit and wait if necessary."""
        if self.rate_limit_remaining <= 10:
            reset_time = self.rate_limit_reset
            current_time = datetime.now()

            if reset_time > current_time:
                wait_time = (reset_time - current_time).total_seconds() + 10  # Add buffer
                print(f"Rate limit nearly exhausted. Waiting {wait_time:.0f} seconds for reset.")
                time.sleep(wait_time)

        # Update rate limit info after each API call
        response = requests.get(f"{self.base_url}/rate_limit", headers=self.headers)
        if response.status_code == 200:
            rate_data = response.json()
            self.rate_limit_remaining = rate_data["resources"]["core"]["remaining"]
            self.rate_limit_reset = datetime.fromtimestamp(rate_data["resources"]["core"]["reset"])

    def _paginated_get(self, url, params=None, max_items=None):
        """Handle paginated API responses with rate limit awareness."""
        if params is None:
            params = {}

        items = []
        page = 1
        per_page = min(100, params.get("per_page", 30))
        params["per_page"] = per_page

        while True:
            self._check_rate_limit()

            params["page"] = page
            response = requests.get(url, headers=self.headers, params=params)

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

    def get_repo_info(self, owner, repo):
        """Get basic repository information."""
        self._check_rate_limit()
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error {response.status_code}: {response.text}")
            return None

    def get_contributors(self, owner, repo, max_contributors=None):
        """Get repository contributors with pagination support."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contributors"
        return self._paginated_get(url, max_items=max_contributors)

    # ... ( get_languages, get_commits, get_commit_activity, get_code_frequency, ...)
    def get_languages(self, owner, repo):
        """Get languages used in the repository."""
        self._check_rate_limit()
        url = f"{self.base_url}/repos/{owner}/{repo}/languages"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting languages: {response.status_code}")
            return {}

    def get_commits(self, owner, repo, params=None, max_commits=None):
        """Get commits with enhanced filtering and pagination."""
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        return self._paginated_get(url, params=params, max_items=max_commits)

    def get_commit_activity(self, owner, repo):
        """Get commit activity stats for the past year."""
        self._check_rate_limit()
        url = f"{self.base_url}/repos/{owner}/{repo}/stats/commit_activity"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 202:
            # GitHub is computing the statistics, wait and retry
            print("GitHub is computing statistics, waiting and retrying...")
            time.sleep(2)
            return self.get_commit_activity(owner, repo)
        else:
            print(f"Error getting commit activity: {response.status_code}")
            return []

    def get_code_frequency(self, owner, repo):
        """Get weekly code addition and deletion statistics."""
        self._check_rate_limit()
        url = f"{self.base_url}/repos/{owner}/{repo}/stats/code_frequency"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 202:
            # GitHub is computing the statistics, wait and retry
            print("GitHub is computing statistics, waiting and retrying...")
            time.sleep(2)
            return self.get_code_frequency(owner, repo)
        else:
            print(f"Error getting code frequency: {response.status_code}")
            return []

    # ... ( get_contributor_activity, get_branches, get_releases, get_issues, ...)
    def get_contributor_activity(self, owner, repo):
        """Get contributor commit activity over time."""
        self._check_rate_limit()
        url = f"{self.base_url}/repos/{owner}/{repo}/stats/contributors"
        response = requests.get(url, headers=self.headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 202:
            # GitHub is computing the statistics, wait and retry
            print("GitHub is computing statistics, waiting and retrying...")
            time.sleep(2)
            return self.get_contributor_activity(owner, repo)
        else:
            print(f"Error getting contributor activity: {response.status_code}")
            return []

    def get_branches(self, owner, repo):
        """Get repository branches."""
        url = f"{self.base_url}/repos/{owner}/{repo}/branches"
        return self._paginated_get(url)

    def get_releases(self, owner, repo, max_releases=None):
        """Get repository releases with pagination support."""
        url = f"{self.base_url}/repos/{owner}/{repo}/releases"
        return self._paginated_get(url, max_items=max_releases)

    def get_issues(self, owner, repo, state="all", max_issues=None, params=None):
        """Get repository issues with enhanced filtering."""
        url = f"{self.base_url}/repos/{owner}/{repo}/issues"
        if params is None:
            params = {}
        params["state"] = state
        return self._paginated_get(url, params=params, max_items=max_issues)

    # ... ( get_issue_timeline, get_pull_requests, get_pr_timeline, get_contents, ...)
    def get_issue_timeline(self, owner, repo, days_back=180):
        """Analyze issue creation and closing over time."""
        # Get issues including closed ones
        issues = self.get_issues(owner, repo, state="all")

        # Prepare timeline data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Initialize daily counters
        date_range = pd.date_range(start=start_date, end=end_date)
        created_counts = {d.strftime('%Y-%m-%d'): 0 for d in date_range}
        closed_counts = {d.strftime('%Y-%m-%d'): 0 for d in date_range}

        # Collect issue creation and closing dates
        for issue in issues:
            created_at = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ')
            if created_at >= start_date:
                created_counts[created_at.strftime('%Y-%m-%d')] += 1

            if issue['state'] == 'closed' and issue.get('closed_at'):
                closed_at = datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
                if closed_at >= start_date:
                    closed_counts[closed_at.strftime('%Y-%m-%d')] += 1

        # Calculate resolution times for closed issues
        resolution_times = []
        for issue in issues:
            if issue['state'] == 'closed' and issue.get('closed_at'):
                created_at = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                closed_at = datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
                resolution_time = (closed_at - created_at).total_seconds() / 3600  # hours
                resolution_times.append(resolution_time)

        # Calculate issue labels distribution
        label_counts = defaultdict(int)
        for issue in issues:
            for label in issue.get('labels', []):
                label_counts[label['name']] += 1

        return {
            'created': created_counts,
            'closed': closed_counts,
            'resolution_times': resolution_times,
            'labels': dict(label_counts)
        }

    def get_pull_requests(self, owner, repo, state="all", max_prs=None, params=None):
        """Get repository pull requests with enhanced filtering."""
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls"
        if params is None:
            params = {}
        params["state"] = state
        return self._paginated_get(url, params=params, max_items=max_prs)

    def get_pr_timeline(self, owner, repo, days_back=180):
        """Analyze PR creation, closing, and metrics over time."""
        # Get PRs including closed and merged ones
        prs = self.get_pull_requests(owner, repo, state="all")

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

    def get_contents(self, owner, repo, path="", ref=None):
        """Get repository contents at the specified path."""
        self._check_rate_limit()
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            return response.json()
        else:
            # print(f"Error getting contents: {response.status_code}")
            return []
    # ... ( get_readme, get_file_content, is_text_file, get_recursive_contents, ...)
    def get_readme(self, owner, repo, ref=None):
        """Get repository README file."""
        self._check_rate_limit()
        url = f"{self.base_url}/repos/{owner}/{repo}/readme"
        params = {}
        if ref:
            params["ref"] = ref

        response = requests.get(url, headers=self.headers, params=params)

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

    def get_file_content(self, owner, repo, path, ref=None):
        """Get the content of a specific file in the repository."""
        self._check_rate_limit()
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref

        response = requests.get(url, headers=self.headers, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("content"):
                try:
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    return content
                except UnicodeDecodeError:
                    return "[Binary file content not displayed]"
            return None
        else:
            print(f"Error getting file content: {response.status_code}")
            return None

    def is_text_file(self, file_path):
        """Determine if a file is likely a text file based on extension."""
        text_extensions = [
            '.txt', '.md', '.rst', '.py', '.js', '.html', '.css', '.java', '.c',
            '.cpp', '.h', '.hpp', '.json', '.xml', '.yaml', '.yml', '.toml',
            '.ini', '.cfg', '.conf', '.sh', '.bat', '.ps1', '.rb', '.pl', '.php',
            '.go', '.rs', '.ts', '.jsx', '.tsx', '.vue', '.swift', '.kt', '.scala',
            '.groovy', '.lua', '.r', '.dart', '.ex', '.exs', '.erl', '.hrl',
            '.clj', '.hs', '.elm', '.f90', '.f95', '.f03', '.sql', '.gitignore',
            '.dockerignore', '.env', '.editorconfig', '.htaccess', '.cs', '.ipynb',
            '.R', '.Rmd', '.jl', '.fs', '.ml', '.mli', '.d', '.scm', '.lisp',
            '.el', '.m', '.mm', '.vb', '.asm', '.s', '.Dockerfile', '.gradle'
        ]

        extension = os.path.splitext(file_path)[1].lower()
        return extension in text_extensions

    def get_recursive_contents(self, owner, repo, path="", max_depth=3, current_depth=0, max_files=1000, ref=None):
        """Recursively get repository contents with a depth limit and file count limit."""
        if current_depth >= max_depth:
            return []

        contents = self.get_contents(owner, repo, path, ref)
        results = []
        file_count = 0

        for item in contents:
            if file_count >= max_files:
                break

            if item["type"] == "dir":
                # For directories, add the directory itself and recursively get contents
                dir_item = {
                    "type": "dir",
                    "name": item["name"],
                    "path": item["path"],
                    "contents": self.get_recursive_contents(
                        owner, repo, item["path"], max_depth, current_depth + 1,
                        max_files - file_count, ref
                    )
                }
                results.append(dir_item)
            else:
                # For files, add the file info
                results.append({
                    "type": "file",
                    "name": item["name"],
                    "path": item["path"],
                    "size": item["size"],
                    "url": item["html_url"]
                })
                file_count += 1

        return results
    # ... ( get_all_text_files, get_documentation_files, analyze_ast, analyze_js_ts, ...)
    def get_all_text_files(self, owner, repo, path="", max_files=50, ref=None):
        """Get content of all text files in the repository (with limit)."""
        contents = self.get_contents(owner, repo, path, ref)
        text_files = []
        file_count = 0

        # Process current directory
        for item in contents:
            if file_count >= max_files:
                break

            if item["type"] == "file" and self.is_text_file(item["name"]):
                content = self.get_file_content(owner, repo, item["path"], ref)
                if content and content != "[Binary file content not displayed]":
                    text_files.append({
                        "name": item["name"],
                        "path": item["path"],
                        "content": content
                    })
                    file_count += 1
            elif item["type"] == "dir":
                # Recursively get text files from subdirectories
                subdir_files = self.get_all_text_files(
                    owner, repo, item["path"], max_files - file_count, ref
                )
                text_files.extend(subdir_files)
                file_count += len(subdir_files)

        return text_files

    def get_documentation_files(self, owner, repo, ref=None):
        """Get documentation files from the repository."""
        # Common documentation file paths and directories
        doc_paths = [
            "docs", "doc", "documentation", "wiki", "CONTRIBUTING.md",
            "CONTRIBUTORS.md", "CODE_OF_CONDUCT.md", "SECURITY.md",
            "SUPPORT.md", "docs/index.md", "docs/README.md", "docs/getting-started.md",
            ".github/ISSUE_TEMPLATE", ".github/PULL_REQUEST_TEMPLATE.md"
        ]

        doc_files = []

        # Try to get each documentation file/directory
        for path in doc_paths:
            try:
                contents = self.get_contents(owner, repo, path, ref)

                # If it's a directory, get all markdown files in it
                if isinstance(contents, list):
                    for item in contents:
                        if item["type"] == "file" and item["name"].lower().endswith((".md", ".rst", ".txt")):
                            content = self.get_file_content(owner, repo, item["path"], ref)
                            if content:
                                doc_files.append({
                                    "name": item["name"],
                                    "path": item["path"],
                                    "content": content
                                })
                # If it's a file, get its content
                elif isinstance(contents, dict) and contents.get("type") == "file":
                    content = self.get_file_content(owner, repo, path, ref)
                    if content:
                        doc_files.append({
                            "name": contents["name"],
                            "path": contents["path"],
                            "content": content
                        })
            except:
                # Path doesn't exist or access issues
                continue

        return doc_files

    def analyze_ast(self, code, file_path):
        """Analyze Python code using AST (Abstract Syntax Tree)."""
        if not file_path.endswith('.py'):
            return None

        try:
            tree = ast.parse(code)

            # Extract more detailed information using AST
            functions = []
            classes = []
            imports = []
            function_complexities = {}

            for node in ast.walk(tree):
                # Get function definitions with arguments
                if isinstance(node, ast.FunctionDef):
                    args = []
                    defaults = len(node.args.defaults)
                    args_count = len(node.args.args) - defaults

                    # Get positional args
                    for arg in node.args.args[:args_count]:
                        if hasattr(arg, 'arg'):  # Python 3
                            args.append(arg.arg)
                        else:  # Python 2
                            args.append(arg.id)

                    # Get args with defaults
                    for i, arg in enumerate(node.args.args[args_count:]):
                        if hasattr(arg, 'arg'):  # Python 3
                            args.append(f"{arg.arg}=...")
                        else:  # Python 2
                            args.append(f"{arg.id}=...")

                    # Calculate function complexity
                    func_complexity = complexity.cc_visit(node)
                    function_complexities[node.name] = func_complexity

                    # Get docstring if available
                    docstring = ast.get_docstring(node)

                    functions.append({
                        'name': node.name,
                        'args': args,
                        'complexity': func_complexity,
                        'docstring': docstring
                    })

                # Get class definitions
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    class_docstring = ast.get_docstring(node)

                    # Get class methods
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            method_complexity = complexity.cc_visit(child)
                            method_docstring = ast.get_docstring(child)

                            methods.append({
                                'name': child.name,
                                'complexity': method_complexity,
                                'docstring': method_docstring
                            })

                    classes.append({
                        'name': node.name,
                        'methods': methods,
                        'docstring': class_docstring
                    })

                # Get imports
                elif isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        imports.append(f"{module}.{name.name}")

            # Calculate overall code complexity
            code_complexity = complexity.cc_visit_ast(tree)

            # Calculate maintainability index
            try:
                mi_score = metrics.mi_visit(code, True)
            except:
                mi_score = None

            return {
                'functions': functions,
                'classes': classes,
                'imports': imports,
                'complexity': {
                    'overall': code_complexity,
                    'functions': function_complexities,
                    'maintainability_index': mi_score
                }
            }

        except SyntaxError:
            print(f"Syntax error in Python file: {file_path}")
            return None
        except Exception as e:
            print(f"Error analyzing {file_path}: {str(e)}")
            return None

    def analyze_js_ts(self, code, file_path):
        """Analyze JavaScript/TypeScript code using regex with improved patterns."""
        if not file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            return None

        # More sophisticated regex patterns for JS/TS analysis
        results = {
            'functions': [],
            'classes': [],
            'imports': [],
            'exports': [],
            'hooks': []  # For React hooks
        }

        # Function patterns (covering various declaration styles)
        function_patterns = [
            # Regular functions
            r'function\s+(\w+)\s*\(([^)]*)\)',
            # Arrow functions assigned to variables
            r'(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=]*)\s*=>\s*{',
            # Class methods
            r'(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*{',
            # Object methods
            r'(\w+)\s*:\s*function\s*\(([^)]*)\)'
        ]

        for pattern in function_patterns:
            for match in re.finditer(pattern, code):
                func_name = match.group(1)
                args = match.group(2).strip() if len(match.groups()) > 1 else ""
                results['functions'].append({
                    'name': func_name,
                    'args': args
                })

        # Class pattern
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{([^}]*)}'
        for match in re.finditer(class_pattern, code, re.DOTALL):
            class_name = match.group(1)
            parent_class = match.group(2) if match.group(2) else None
            class_body = match.group(3)

            # Find methods in class
            methods = []
            method_pattern = r'(?:async\s+)?(\w+)\s*\(([^)]*)\)\s*{([^}]*)}'
            for method_match in re.finditer(method_pattern, class_body):
                method_name = method_match.group(1)
                methods.append(method_name)

            results['classes'].append({
                'name': class_name,
                'extends': parent_class,
                'methods': methods
            })

        # Import patterns
        import_patterns = [
            # ES6 imports
            r'import\s+(?:{([^}]*)}|\*\s+as\s+(\w+)|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]',
            # CommonJS requires
            r'(?:const|let|var)\s+(?:{([^}]*)}|(\w+))\s*=\s*require\([\'"]([^\'"]+)[\'"]\)'
        ]

        for pattern in import_patterns:
            for match in re.finditer(pattern, code):
                groups = match.groups()
                if groups[0]:  # Destructured import
                    imports = [name.strip() for name in groups[0].split(',')]
                    for imp in imports:
                        results['imports'].append(imp)
                elif groups[1]:  # Namespace import (import * as X)
                    results['imports'].append(groups[1])
                elif groups[2]:  # Default import
                    results['imports'].append(groups[2])
                elif groups[3]:  # Module name
                    results['imports'].append(groups[3])

        # React hooks detection (for React files)
        if file_path.endswith(('.jsx', '.tsx')):
            hook_pattern = r'use([A-Z]\w+)\s*\('
            for match in re.finditer(hook_pattern, code):
                hook_name = 'use' + match.group(1)
                results['hooks'].append(hook_name)

        # Export patterns
        export_patterns = [
            # Named exports
            r'export\s+(?:const|let|var|function|class)\s+(\w+)',
            # Default exports
            r'export\s+default\s+(?:function|class)?\s*(\w+)?'
        ]

        for pattern in export_patterns:
            for match in re.finditer(pattern, code):
                if match.group(1):
                    results['exports'].append(match.group(1))

        return results
    # ... ( extract_code_summary, analyze_dependencies, create_dependency_graph, ...)
    def extract_code_summary(self, file_content, file_path):
        """Extract comprehensive summary information from code files."""
        extension = os.path.splitext(file_path)[1].lower()

        # Initialize summary
        summary = {
            "functions": [],
            "classes": [],
            "imports": [],
            "description": "",
            "complexity": None
        }

        # Extract Python definitions with AST
        if extension == '.py':
            ast_result = self.analyze_ast(file_content, file_path)
            if ast_result:
                summary["functions"] = [f["name"] for f in ast_result["functions"]]
                summary["classes"] = [c["name"] for c in ast_result["classes"]]
                summary["imports"] = ast_result["imports"]
                summary["complexity"] = ast_result["complexity"]

                # Try to extract module docstring
                try:
                    tree = ast.parse(file_content)
                    module_docstring = ast.get_docstring(tree)
                    if module_docstring:
                        summary["description"] = module_docstring
                except:
                    pass

                # Add detailed function and class info
                summary["detailed_functions"] = ast_result["functions"]
                summary["detailed_classes"] = ast_result["classes"]

        # Extract JavaScript/TypeScript definitions
        elif extension in ['.js', '.ts', '.jsx', '.tsx']:
            js_result = self.analyze_js_ts(file_content, file_path)
            if js_result:
                summary["functions"] = [f["name"] for f in js_result["functions"]]
                summary["classes"] = [c["name"] for c in js_result["classes"]]
                summary["imports"] = js_result["imports"]

                # Add detailed function and class info
                summary["detailed_functions"] = js_result["functions"]
                summary["detailed_classes"] = js_result["classes"]
                summary["hooks"] = js_result.get("hooks", [])
                summary["exports"] = js_result.get("exports", [])

        # Calculate basic code metrics for any text file
        if file_content:
            lines = file_content.split('\n')
            code_lines = 0
            comment_lines = 0
            blank_lines = 0

            comment_prefixes = ['#', '//', '/*', '*', '<!--']

            for line in lines:
                line = line.strip()
                if not line:
                    blank_lines += 1
                elif any(line.startswith(prefix) for prefix in comment_prefixes):
                    comment_lines += 1
                else:
                    code_lines += 1

            summary["metrics"] = {
                "total_lines": len(lines),
                "code_lines": code_lines,
                "comment_lines": comment_lines,
                "blank_lines": blank_lines,
                "comment_ratio": comment_lines / max(1, code_lines + comment_lines)
            }

        return summary

    def analyze_dependencies(self, owner, repo, max_files=100):
        """Analyze code dependencies across the repository."""
        # Get Python and JavaScript files
        text_files = self.get_all_text_files(owner, repo, max_files=max_files)

        # Filter for Python and JS/TS files
        code_files = [f for f in text_files if f["name"].endswith(('.py', '.js', '.ts', '.jsx', '.tsx'))]

        # Track dependencies
        dependencies = {
            'internal': defaultdict(set),  # File to file dependencies
            'external': defaultdict(set),  # External package dependencies by file
            'modules': defaultdict(set)    # Defined modules/components by file
        }

        # Extract module names from file paths
        file_to_module = {}
        for file in code_files:
            # Convert file path to potential module name
            module_path = os.path.splitext(file["path"])[0].replace('/', '.')
            file_to_module[file["path"]] = module_path

            # Track what each file defines
            summary = self.extract_code_summary(file["content"], file["path"])

            if file["name"].endswith('.py'):
                for function in summary.get("functions", []):
                    dependencies['modules'][file["path"]].add(f"{module_path}.{function}")
                for class_name in summary.get("classes", []):
                    dependencies['modules'][file["path"]].add(f"{module_path}.{class_name}")
            else:  # JS/TS files
                for export in summary.get("exports", []):
                    dependencies['modules'][file["path"]].add(export)

        # Analyze imports/dependencies
        for file in code_files:
            summary = self.extract_code_summary(file["content"], file["path"])

            for imp in summary.get("imports", []):
                # Check if this is an internal import
                is_internal = False

                if file["name"].endswith('.py'):
                    # For Python, check if the import matches any module path
                    for module_path in file_to_module.values():
                        if imp == module_path or imp.startswith(f"{module_path}."):
                            is_internal = True
                            # Find the file that defines this module
                            for f_path, m_path in file_to_module.items():
                                if m_path == imp.split('.')[0]:
                                    dependencies['internal'][file["path"]].add(f_path)
                                    break
                else:
                    # For JS/TS, check relative imports
                    if imp.startswith('./') or imp.startswith('../'):
                        is_internal = True
                        # Try to resolve the relative import
                        src_dir = os.path.dirname(file["path"])
                        target_path = os.path.normpath(os.path.join(src_dir, imp))

                        # Add known extensions if not specified
                        if '.' not in os.path.basename(target_path):
                            for ext in ['.js', '.ts', '.jsx', '.tsx']:
                                test_path = f"{target_path}{ext}"
                                if test_path in file_to_module:
                                    dependencies['internal'][file["path"]].add(test_path)
                                    break

                # If not internal, consider it external
                if not is_internal:
                    # Clean up the import name (remove relative path parts)
                    if not file["name"].endswith('.py'):
                        imp = imp.split('/')[0]  # Take the package name part
                    dependencies['external'][file["path"]].add(imp)

        return dependencies

    def create_dependency_graph(self, dependencies):
        """Create a NetworkX graph from dependencies for visualization."""
        G = nx.DiGraph()

        # Add nodes for files
        for file_path in dependencies['internal'].keys():
            G.add_node(file_path, type='file')

        # Add edges for internal dependencies
        for file_path, deps in dependencies['internal'].items():
            for dep in deps:
                G.add_edge(file_path, dep)

        # Add nodes and edges for external dependencies
        external_nodes = set()
        for file_path, deps in dependencies['external'].items():
            for dep in deps:
                external_node = f"ext:{dep}"
                if external_node not in external_nodes:
                    G.add_node(external_node, type='external')
                    external_nodes.add(external_node)
                G.add_edge(file_path, external_node)

        return G
    # ... ( get_repo_text_summary, get_temporal_analysis, get_all_info, ...)
    def get_repo_text_summary(self, owner, repo, max_files=25):
        """Extract and summarize text content from the repository with improved metrics."""
        # Get README
        readme = self.get_readme(owner, repo)

        # Get documentation
        docs = self.get_documentation_files(owner, repo)

        # Get key code files (limit to avoid API rate limits)
        text_files = self.get_all_text_files(owner, repo, max_files=max_files)

        # Analyze code files
        code_summary = {}
        complexity_metrics = {
            'cyclomatic_complexity': [],
            'maintainability_index': [],
            'comment_ratios': []
        }

        for file in text_files:
            ext = os.path.splitext(file["name"])[1].lower()
            if ext in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                file_summary = self.extract_code_summary(file["content"], file["path"])
                code_summary[file["path"]] = file_summary

                # Collect complexity metrics
                if file_summary.get('complexity'):
                    cc = file_summary['complexity'].get('overall')
                    if cc is not None:
                        complexity_metrics['cyclomatic_complexity'].append((file["path"], cc))

                    mi = file_summary['complexity'].get('maintainability_index')
                    if mi is not None:
                        complexity_metrics['maintainability_index'].append((file["path"], mi))

                if file_summary.get('metrics'):
                    comment_ratio = file_summary['metrics'].get('comment_ratio', 0)
                    complexity_metrics['comment_ratios'].append((file["path"], comment_ratio))

        # Analyze dependencies
        dependencies = self.analyze_dependencies(owner, repo, max_files=max_files)

        # Summarize repository content by file type
        file_types = defaultdict(int)
        for file in text_files:
            ext = os.path.splitext(file["name"])[1].lower()
            file_types[ext] += 1

        # Calculate aggregate code metrics
        total_code_lines = sum(summary.get('metrics', {}).get('code_lines', 0)
                              for summary in code_summary.values())
        total_comment_lines = sum(summary.get('metrics', {}).get('comment_lines', 0)
                                 for summary in code_summary.values())

        aggregate_metrics = {
            'total_files': len(text_files),
            'total_code_lines': total_code_lines,
            'total_comment_lines': total_comment_lines,
            'average_comment_ratio': (total_comment_lines / total_code_lines) if total_code_lines > 0 else 0
        }

        return {
            "readme": readme,
            "documentation": docs,
            "code_summary": code_summary,
            "complexity_metrics": complexity_metrics,
            "dependencies": dependencies,
            "file_type_counts": dict(file_types),
            "aggregate_metrics": aggregate_metrics,
            "text_files": text_files  # Include the actual text file contents
        }

    def get_temporal_analysis(self, owner, repo):
        """Perform temporal analysis of repository activity."""
        # Get commit activity over time
        commit_activity = self.get_commit_activity(owner, repo)

        # Get code frequency (additions/deletions over time)
        code_frequency = self.get_code_frequency(owner, repo)

        # Get contributor activity
        contributor_activity = self.get_contributor_activity(owner, repo)

        # Get issue and PR timelines
        issue_timeline = self.get_issue_timeline(owner, repo)
        pr_timeline = self.get_pr_timeline(owner, repo)

        # Process data for visualization
        # - Weekly commit counts
        weekly_commits = []
        if commit_activity:
            for week in commit_activity:
                date = datetime.fromtimestamp(week['week'])
                weekly_commits.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'total': week['total'],
                    'days': week['days']  # Daily breakdown within the week
                })

        # - Weekly code changes
        weekly_code_changes = []
        if code_frequency:
            for item in code_frequency:
                date = datetime.fromtimestamp(item[0])
                weekly_code_changes.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'additions': item[1],
                    'deletions': -item[2]  # Convert to positive for visualization
                })

        # - Contributor timeline
        contributor_timeline = {}
        if contributor_activity:
            for contributor in contributor_activity:

                author = contributor['author']['login'] if contributor['author'] else "anonymous"
                weeks = contributor['weeks']

                if author not in contributor_timeline:
                    contributor_timeline[author] = []

                for week in weeks:
                    if week['c'] > 0:  # Only include weeks with commits
                        date = datetime.fromtimestamp(week['w'])
                        contributor_timeline[author].append({
                            'date': date.strftime('%Y-%m-%d'),
                            'commits': week['c'],
                            'additions': week['a'],
                            'deletions': week['d']
                        })

        return {
            'weekly_commits': weekly_commits,
            'weekly_code_changes': weekly_code_changes,
            'contributor_timeline': contributor_timeline,
            'issue_timeline': issue_timeline,
            'pr_timeline': pr_timeline
        }

    def get_all_info(self, owner, repo):
        """Get comprehensive information about a repository with enhanced metrics."""
        result = {
            "timestamp": datetime.now().isoformat(),
            "basic_info": self.get_repo_info(owner, repo)
        }

        if not result["basic_info"]:
            print(f"Could not retrieve repository information for {owner}/{repo}")
            return None

        print("Getting repository statistics...")

        # Get additional information
        result["languages"] = self.get_languages(owner, repo)
        result["contributors"] = self.get_contributors(owner, repo, max_contributors=30)
        result["recent_commits"] = self.get_commits(owner, repo, max_commits=30)
        result["branches"] = self.get_branches(owner, repo)
        result["releases"] = self.get_releases(owner, repo, max_releases=10)
        result["open_issues"] = self.get_issues(owner, repo, state="open", max_issues=50)
        result["open_pull_requests"] = self.get_pull_requests(owner, repo, state="open", max_prs=50)
        result["root_contents"] = self.get_contents(owner, repo)

        print("Analyzing repository content...")

        # Get text content and documentation
        result["text_content"] = self.get_repo_text_summary(owner, repo, max_files=30)

        print("Analyzing repository activity over time...")

        # Get temporal analysis
        result["temporal_analysis"] = self.get_temporal_analysis(owner, repo)

        return result
    # ... ( display_repo_info, display_code_files, export_repo_text )

    def display_repo_info(self, repo_data):
        """Display repository information in a Colab-friendly format with enhanced visualizations."""
        if not repo_data or not repo_data["basic_info"]:
            return

        basic = repo_data["basic_info"]

        # Display basic repository information
        display(HTML(f"""
        <h1 style="text-align:center;">Repository: {basic['full_name']}</h1>
        <div style="text-align:center;"><img src="{basic.get('owner', {}).get('avatar_url', '')}" width="100" height="100" style="border-radius:50%"></div>
        <div style="background-color:#f5f5f5; padding:15px; border-radius:5px; margin:10px 0;">
            <p><strong>Description:</strong> {basic['description'] or 'No description'}</p>
            <p><strong>URL:</strong> <a href="{basic['html_url']}" target="_blank">{basic['html_url']}</a></p>
            <p><strong>Created:</strong> {basic['created_at']}</p>
            <p><strong>Last updated:</strong> {basic['updated_at']}</p>
            <p><strong>Default branch:</strong> {basic['default_branch']}</p>
            <p><strong>Stars:</strong> {basic['stargazers_count']}</p>
            <p><strong>Forks:</strong> {basic['forks_count']}</p>
            <p><strong>Open issues:</strong> {basic['open_issues_count']}</p>
            <p><strong>License:</strong> {basic['license']['name'] if basic.get('license') else 'Not specified'}</p>
            <p><strong>Topics:</strong> {', '.join(basic.get('topics', ['None']))}</p>
        </div>
        """))

        # Display language distribution
        if repo_data["languages"]:
            display(Markdown("## Languages"))

            # Create DataFrame for languages
            lang_data = []
            total = sum(repo_data["languages"].values())
            for lang, bytes_count in repo_data["languages"].items():
                percentage = (bytes_count / total) * 100
                lang_data.append({
                    "Language": lang,
                    "Bytes": bytes_count,
                    "Percentage": percentage
                })

            lang_df = pd.DataFrame(lang_data)
            display(lang_df)

            # Create pie chart
            plt.figure(figsize=(10, 6))
            plt.pie(lang_df["Percentage"], labels=lang_df["Language"], autopct='%1.1f%%')
            plt.title("Language Distribution")
            plt.axis('equal')
            plt.show()

        # Display contributors
        if repo_data["contributors"]:
            display(Markdown("## Top Contributors"))

            # Create DataFrame for contributors
            contrib_data = []
            for contributor in repo_data["contributors"][:15]:
                contrib_data.append({
                    "Username": contributor['login'],
                    "Contributions": contributor['contributions'],
                    "Profile": contributor['html_url']
                })

            contrib_df = pd.DataFrame(contrib_data)
            display(contrib_df)

            # Create bar chart
            plt.figure(figsize=(12, 6))
            plt.bar(contrib_df["Username"], contrib_df["Contributions"])
            plt.title("Top Contributors")
            plt.xlabel("Contributor")
            plt.ylabel("Number of Contributions")
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            plt.show()

        # Display recent commits
        if repo_data["recent_commits"]:
            display(Markdown("## Recent Commits"))

            commit_data = []
            for commit in repo_data["recent_commits"][:10]:
                author = commit['commit']['author']['name']
                message = commit['commit']['message'].split('\n')[0]  # First line only
                date = commit['commit']['author']['date']
                commit_data.append({
                    "Author": author,
                    "Date": date,
                    "Message": message,
                    "URL": commit.get('html_url', '')
                })

            commit_df = pd.DataFrame(commit_data)
            display(commit_df)

        # Display repository structure
        if repo_data["root_contents"]:
            display(Markdown("## Repository Structure"))

            dir_content = []
            for item in repo_data["root_contents"]:
                dir_content.append({
                    "Name": item["name"],
                    "Type": item["type"],
                    "Size": item.get("size", ""),
                    "URL": item.get("html_url", "")
                })

            dir_df = pd.DataFrame(dir_content)
            display(dir_df)

        # Display README preview if available
        if repo_data["text_content"]["readme"]:
            display(Markdown("## README Preview"))

            readme = repo_data["text_content"]["readme"]
            display(Markdown(f"**{readme['name']}**"))

            # Show a preview of the README content (first few lines)
            lines = readme["content"].split("\n")
            preview_lines = lines[:min(15, len(lines))]
            preview = "\n".join(preview_lines)

            display(Markdown(preview))
            if len(lines) > 15:
                display(Markdown("*... (content truncated)* ..."))

        # Display code summary
        if repo_data["text_content"]["code_summary"]:
            display(Markdown("## Code Summary"))

            # Count total functions and classes
            total_functions = sum(len(summary.get("functions", [])) for summary in repo_data["text_content"]["code_summary"].values())
            total_classes = sum(len(summary.get("classes", [])) for summary in repo_data["text_content"]["code_summary"].values())

            # Get aggregate metrics
            agg_metrics = repo_data["text_content"]["aggregate_metrics"]

            display(HTML(f"""
            <div style="background-color:#e8f4f8; padding:15px; border-radius:5px; margin:10px 0;">
                <p><strong>Total Files Analyzed:</strong> {agg_metrics['total_files']}</p>
                <p><strong>Total Code Lines:</strong> {agg_metrics['total_code_lines']}</p>
                <p><strong>Total Comment Lines:</strong> {agg_metrics['total_comment_lines']}</p>
                <p><strong>Comment Ratio:</strong> {agg_metrics['average_comment_ratio']:.2f}</p>
                <p><strong>Total Functions:</strong> {total_functions}</p>
                <p><strong>Total Classes:</strong> {total_classes}</p>
            </div>
            """))

            # Display complexity metrics
            if repo_data["text_content"]["complexity_metrics"]["cyclomatic_complexity"]:
                display(Markdown("### Code Complexity"))

                # Get top 10 most complex files
                complexity_data = repo_data["text_content"]["complexity_metrics"]["cyclomatic_complexity"]
                complexity_data.sort(key=lambda x: x[1], reverse=True)

                complex_files = []
                for path, cc in complexity_data[:10]:
                    complex_files.append({
                        "File": os.path.basename(path),
                        "Path": path,
                        "Cyclomatic Complexity": cc
                    })

                complex_df = pd.DataFrame(complex_files)
                display(complex_df)

                # Plot complexity distribution - ensure we have numeric values only
                cc_values = []
                for _, cc in complexity_data:
                    try:
                        # Handle both direct numbers and lists that might contain complexity values
                        if isinstance(cc, (int, float)):
                            cc_values.append(float(cc))
                        elif isinstance(cc, list) and len(cc) > 0:
                            # If it's a list, use the first numeric value
                            for val in cc:
                                if isinstance(val, (int, float)):
                                    cc_values.append(float(val))
                                    break
                    except (ValueError, TypeError):
                        # Skip values that can't be converted to float
                        continue
                if cc_values:  # Only plot if we have data
                    plt.figure(figsize=(10, 6))
                    plt.hist(cc_values, bins=10, alpha=0.7)
                    plt.title("Cyclomatic Complexity Distribution")
                    plt.xlabel("Complexity")
                    plt.ylabel("Number of Files")
                    plt.axvline(np.mean(cc_values), color='r', linestyle='dashed', linewidth=1, label=f"Mean: {np.mean(cc_values):.2f}")
                    plt.legend()
                    plt.tight_layout()
                    plt.show()

            # Display maintainability index if available
            if repo_data["text_content"]["complexity_metrics"]["maintainability_index"]:
                mi_data = repo_data["text_content"]["complexity_metrics"]["maintainability_index"]
                # Ensure we have numeric values only
                mi_values = [float(mi) for _, mi in mi_data if mi is not None]

                if mi_values:  # Only plot if we have data
                    plt.figure(figsize=(10, 6))
                    plt.hist(mi_values, bins=10, alpha=0.7)
                    plt.title("Maintainability Index Distribution")
                    plt.xlabel("Maintainability Index (higher is better)")
                    plt.ylabel("Number of Files")
                    plt.axvline(np.mean(mi_values), color='g', linestyle='dashed', linewidth=1, label=f"Mean: {np.mean(mi_values):.2f}")
                    plt.legend()
                    plt.tight_layout()
                    plt.show()

            # Display file type distribution
            if repo_data["text_content"]["file_type_counts"]:
                display(Markdown("### File Type Distribution"))

                file_type_data = []
                for ext, count in repo_data["text_content"]["file_type_counts"].items():
                    if ext:  # Skip empty extensions
                        file_type_data.append({
                            "Extension": ext,
                            "Count": count
                        })

                file_type_df = pd.DataFrame(file_type_data)
                display(file_type_df)

                # Create bar chart
                plt.figure(figsize=(10, 6))
                plt.bar(file_type_df["Extension"], file_type_df["Count"])
                plt.title("File Type Distribution")
                plt.xlabel("File Extension")
                plt.ylabel("Count")
                plt.xticks(rotation=45, ha='right')
                plt.tight_layout()
                plt.show()

        # Display dependency graph if available
        if repo_data["text_content"]["dependencies"]:
            display(Markdown("## Code Dependencies"))

            # Create dependency graph
            G = self.create_dependency_graph(repo_data["text_content"]["dependencies"])

            # Display dependency statistics
            internal_deps = repo_data["text_content"]["dependencies"]["internal"]
            external_deps = repo_data["text_content"]["dependencies"]["external"]

            # Count unique external dependencies
            all_external = set()
            for deps in external_deps.values():
                all_external.update(deps)

            # Find most imported packages
            ext_counts = Counter()
            for deps in external_deps.values():
                ext_counts.update(deps)

            top_imports = ext_counts.most_common(10)

            display(HTML(f"""
            <div style="background-color:#e8f4f8; padding:15px; border-radius:5px; margin:10px 0;">
                <p><strong>Files with Dependencies:</strong> {len(internal_deps) + len(external_deps)}</p>
                <p><strong>Internal Dependency Relationships:</strong> {sum(len(deps) for deps in internal_deps.values())}</p>
                <p><strong>Unique External Dependencies:</strong> {len(all_external)}</p>
            </div>
            """))

            # Display most imported packages
            if top_imports:
                display(Markdown("### Most Used External Dependencies"))

                imports_data = []
                for pkg, count in top_imports:
                    imports_data.append({
                        "Package": pkg,
                        "Used in # Files": count
                    })

                imports_df = pd.DataFrame(imports_data)
                display(imports_df)

            # Visualize dependency network (if not too large)
            if len(G.nodes) <= 50:  # Only visualize if not too complex
                try:
                    display(Markdown("### Dependency Network"))

                    plt.figure(figsize=(12, 12))

                    # Node colors based on type
                    node_colors = []
                    for node in G.nodes:
                        if G.nodes[node].get('type') == 'external':
                            node_colors.append('red')
                        else:
                            node_colors.append('skyblue')

                    # Node sizes based on connections
                    node_sizes = [100 + 50 * G.degree(node) for node in G.nodes]

                    # Layout for the graph
                    pos = nx.spring_layout(G, k=0.5, iterations=50, seed=42)  # Adding seed for reproducibility

                    # Draw the graph
                    nx.draw_networkx(
                        G, pos,
                        with_labels=False,
                        node_color=node_colors,
                        node_size=node_sizes,
                        alpha=0.7,
                        arrows=True,
                        arrowsize=10,
                        width=0.5
                    )

                    # Add labels for external dependencies
                    external_labels = {node: node.replace('ext:', '')
                                    for node in G.nodes
                                    if G.nodes[node].get('type') == 'external'}

                    nx.draw_networkx_labels(
                        G, pos,
                        labels=external_labels,
                        font_size=8,
                        font_color='black'
                    )

                    plt.title("Code Dependency Network (red=external)")
                    plt.axis('off')
                    plt.tight_layout()
                    plt.show()
                except Exception as e:
                    print(f"Error generating dependency network visualization: {str(e)}")
                    print("Skipping network visualization due to data compatibility issues.")

        # Display temporal analysis
        if repo_data["temporal_analysis"]["weekly_commits"]:
            display(Markdown("## Repository Activity Over Time"))

            # Commit activity over time
            weekly_commits = repo_data["temporal_analysis"]["weekly_commits"]
            if weekly_commits:
                display(Markdown("### Weekly Commit Activity"))

                # Convert to DataFrame for plotting
                dates = [datetime.strptime(week['date'], '%Y-%m-%d') for week in weekly_commits]
                commits = [week['total'] for week in weekly_commits]

                try:
                    plt.figure(figsize=(14, 6))
                    plt.plot(dates, commits, marker='o', linestyle='-', alpha=0.7)
                    plt.title("Weekly Commit Activity")
                    plt.xlabel("Date")
                    plt.ylabel("Number of Commits")
                    plt.grid(True, alpha=0.3)

                    # Format x-axis to show dates nicely
                    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                    plt.gcf().autofmt_xdate()

                    plt.tight_layout()
                    plt.show()
                except Exception as e:
                    print(f"Error generating commit activity chart: {str(e)}")
                    print("Displaying raw data instead:")
                    activity_df = pd.DataFrame({
                        'Date': [week['date'] for week in weekly_commits],
                        'Commits': [week['total'] for week in weekly_commits]
                    })
                    display(activity_df.head(10))

            # Code changes over time
            weekly_code_changes = repo_data["temporal_analysis"]["weekly_code_changes"]
            if weekly_code_changes:
                display(Markdown("### Weekly Code Changes"))

                # Convert to DataFrame for plotting
                dates = [datetime.strptime(week['date'], '%Y-%m-%d') for week in weekly_code_changes]
                additions = [week['additions'] for week in weekly_code_changes]
                deletions = [week['deletions'] for week in weekly_code_changes]

                try:
                    # Convert data to proper format for plotting
                    plot_dates = np.array(dates)
                    plot_additions = np.array([float(a) for a in additions])
                    plot_deletions = np.array([float(d) for d in deletions])

                    plt.figure(figsize=(14, 6))
                    plt.bar(plot_dates, plot_additions, color='green', alpha=0.6, label='Additions')
                    plt.bar(plot_dates, plot_deletions, color='red', alpha=0.6, label='Deletions')
                    plt.title("Weekly Code Changes")
                    plt.xlabel("Date")
                    plt.ylabel("Lines Changed")
                    plt.legend()

                    # Format x-axis to show dates nicely
                    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                    plt.gcf().autofmt_xdate()

                    plt.tight_layout()
                    plt.show()
                except Exception as e:
                    print(f"Error generating code changes chart: {str(e)}")
                    print("Displaying raw data instead:")
                    changes_df = pd.DataFrame({
                        'Date': [week['date'] for week in weekly_code_changes],
                        'Additions': [week['additions'] for week in weekly_code_changes],
                        'Deletions': [week['deletions'] for week in weekly_code_changes]
                    })
                    display(changes_df.head(10))

            # Display issue resolution metrics
            issue_timeline = repo_data["temporal_analysis"]["issue_timeline"]
            if issue_timeline and issue_timeline.get('resolution_times'):
                display(Markdown("### Issue Resolution Statistics"))

                resolution_times = issue_timeline['resolution_times']

                if resolution_times:
                    # Calculate statistics
                    avg_resolution = np.mean(resolution_times)
                    median_resolution = np.median(resolution_times)

                    display(HTML(f"""
                    <div style="background-color:#f5f5f5; padding:15px; border-radius:5px; margin:10px 0;">
                        <p><strong>Average Time to Close Issues:</strong> {avg_resolution:.2f} hours ({avg_resolution/24:.2f} days)</p>
                        <p><strong>Median Time to Close Issues:</strong> {median_resolution:.2f} hours ({median_resolution/24:.2f} days)</p>
                        <p><strong>Issues Analyzed:</strong> {len(resolution_times)}</p>
                    </div>
                    """))

                    # Plot histogram of resolution times
                    try:
                        plt.figure(figsize=(10, 6))
                        # Ensure all values are float and clip to reasonable range
                        resolution_times_clean = np.array([float(rt) for rt in resolution_times if rt is not None])
                        plt.hist(np.clip(resolution_times_clean, 0, 168), bins=20, alpha=0.7)  # Clip to one week for readability
                        plt.title("Issue Resolution Times (Capped at 1 Week)")
                        plt.xlabel("Hours to Resolution")
                        plt.ylabel("Number of Issues")
                        plt.axvline(avg_resolution, color='r', linestyle='dashed', linewidth=1, label=f"Mean: {avg_resolution:.2f} hours")
                        plt.axvline(median_resolution, color='g', linestyle='dashed', linewidth=1, label=f"Median: {median_resolution:.2f} hours")
                        plt.legend()
                        plt.tight_layout()
                        plt.show()
                    except Exception as e:
                        print(f"Error generating issue resolution histogram: {str(e)}")
                        print("Skipping histogram visualization due to data compatibility issues.")

                # Display issue labels analysis
                if issue_timeline.get('labels'):
                    top_labels = sorted(issue_timeline['labels'].items(), key=lambda x: x[1], reverse=True)[:10]

                    if top_labels:
                        display(Markdown("### Top Issue Labels"))

                        labels = [label for label, _ in top_labels]
                        counts = [count for _, count in top_labels]

                        try:
                            plt.figure(figsize=(10, 6))

                            # Limit label length for display and handle potential non-string labels
                            cleaned_labels = []
                            for label in labels:
                                if isinstance(label, str):
                                    # Truncate long labels
                                    if len(label) > 20:
                                        cleaned_labels.append(label[:17] + "...")
                                    else:
                                        cleaned_labels.append(label)
                                else:
                                    # Convert non-string labels to string
                                    cleaned_labels.append(str(label))

                            plt.bar(cleaned_labels, counts, alpha=0.7)
                            plt.title("Most Common Issue Labels")
                            plt.xlabel("Label")
                            plt.ylabel("Count")
                            plt.xticks(rotation=45, ha='right')
                            plt.tight_layout()
                            plt.show()
                        except Exception as e:
                            print(f"Error generating issue labels chart: {str(e)}")
                            print("Skipping labels visualization due to data compatibility issues.")

            # Display PR statistics
            pr_timeline = repo_data["temporal_analysis"]["pr_timeline"]
            if pr_timeline:
                display(Markdown("### Pull Request Statistics"))

                # Display PR acceptance rate
                acceptance_rate = pr_timeline.get('acceptance_rate', 0)

                display(HTML(f"""
    <div style="background-color:#2c2c2c; color:#f5f5f5; padding:15px; border-radius:8px; margin:10px 0;">
        <p><strong>PR Acceptance Rate:</strong> {acceptance_rate:.2f}%</p>
    </div>
    """))

                # Display PR merge time statistics
                if pr_timeline.get('merge_times'):
                    merge_times = pr_timeline['merge_times']

                    if merge_times:
                        avg_merge = np.mean(merge_times)
                        median_merge = np.median(merge_times)

                        display(HTML(f"""
                        <div style="background-color:#2c2c2c; color:#f5f5f5; padding:15px; border-radius:8px; margin:10px 0;">
                            <p><strong>Average Time to Merge PRs:</strong> {avg_merge:.2f} hours ({avg_merge/24:.2f} days)</p>
                            <p><strong>Median Time to Merge PRs:</strong> {median_merge:.2f} hours ({median_merge/24:.2f} days)</p>
                            <p><strong>PRs Analyzed:</strong> {len(merge_times)}</p>
                        </div>
                        """))

                        # Plot histogram of merge times
                        try:
                            plt.figure(figsize=(10, 6))
                            # Ensure all values are float and clip to reasonable range
                            merge_times_clean = np.array([float(mt) for mt in merge_times if mt is not None])
                            plt.hist(np.clip(merge_times_clean, 0, 168), bins=20, alpha=0.7)  # Clip to one week for readability
                            plt.title("PR Merge Times (Capped at 1 Week)")
                            plt.xlabel("Hours to Merge")
                            plt.ylabel("Number of PRs")
                            plt.axvline(avg_merge, color='r', linestyle='dashed', linewidth=1, label=f"Mean: {avg_merge:.2f} hours")
                            plt.axvline(median_merge, color='g', linestyle='dashed', linewidth=1, label=f"Median: {median_merge:.2f} hours")
                            plt.legend()
                            plt.tight_layout()
                            plt.show()
                        except Exception as e:
                            print(f"Error generating PR merge time histogram: {str(e)}")
                            print("Skipping histogram visualization due to data compatibility issues.")

    def display_code_files(self, repo_data, max_files=5):
        """Display code files with syntax highlighting and complexity metrics."""
        if not repo_data or not repo_data["text_content"] or not repo_data["text_content"]["text_files"]:
            return

        display(Markdown("## Code File Preview"))

        # Filter for Python/JavaScript/TypeScript files
        code_files = [
            file for file in repo_data["text_content"]["text_files"]
            if file["name"].endswith(('.py', '.js', '.ts', '.jsx', '.tsx'))
        ]

        # Sort by complexity if available
        complexity_metrics = repo_data["text_content"]["complexity_metrics"]["cyclomatic_complexity"]
        complexity_dict = {path: cc for path, cc in complexity_metrics}

        # Sort files by complexity (if available) or by file size
        if complexity_dict:
            code_files.sort(key=lambda x: complexity_dict.get(x["path"], 0), reverse=True)
        else:
            code_files.sort(key=lambda x: len(x["content"]), reverse=True)

        # Display up to max_files
        for i, file in enumerate(code_files[:max_files]):
            file_path = file["path"]
            complexity = complexity_dict.get(file_path, "N/A")

            display(Markdown(f"### {file_path} (Complexity: {complexity})"))

            # Get code summary
            summary = repo_data["text_content"]["code_summary"].get(file_path, {})

            # Display functions and classes
            if summary.get("functions") or summary.get("classes"):
                func_list = ", ".join(summary.get("functions", []))
                class_list = ", ".join(summary.get("classes", []))

                display(HTML(f"""
                <div style="background-color:#2c2c2c; color:#f5f5f5; padding:10px; border-radius:5px; margin:5px 0; font-size:0.9em;">
                    <p><strong>Functions:</strong> {func_list or "None"}</p>
                    <p><strong>Classes:</strong> {class_list or "None"}</p>
                </div>
                """))

            # Get file extension for syntax highlighting
            ext = os.path.splitext(file["name"])[1][1:]  # Remove the dot

            # Display code with syntax highlighting (first 100 lines max)
            code = file["content"]
            lines = code.split("\n")
            preview_lines = lines[:min(100, len(lines))]
            preview = "\n".join(preview_lines)

            display(Markdown(f"```{ext}\n{preview}\n```"))

            if len(lines) > 100:
                display(Markdown(f"*... ({len(lines) - 100} more lines) ...*"))

    def export_repo_text(self, repo_data, output_dir='/content/repo_text'):
        """Export repository text content and analysis to files in Colab."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Write README
        if repo_data["text_content"]["readme"] and repo_data["text_content"]["readme"].get("content"):
            readme_path = os.path.join(output_dir, "README.md")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(repo_data["text_content"]["readme"]["content"])

        # Write documentation files
        if repo_data["text_content"]["documentation"]:
            docs_dir = os.path.join(output_dir, "docs")
            if not os.path.exists(docs_dir):
                os.makedirs(docs_dir)

            for doc in repo_data["text_content"]["documentation"]:
                # Create directory structure if needed
                doc_path = os.path.join(docs_dir, doc["name"])
                with open(doc_path, 'w', encoding='utf-8') as f:
                    f.write(doc["content"])

        # Write code files
        code_dir = os.path.join(output_dir, "code")
        if not os.path.exists(code_dir):
            os.makedirs(code_dir)

        for file in repo_data["text_content"]["text_files"]:
            if os.path.splitext(file["name"])[1].lower() in ['.py', '.js', '.ts', '.jsx', '.tsx']:
                file_path = os.path.join(code_dir, file["name"])
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(file["content"])

        # Write enhanced repository summary
        summary_path = os.path.join(output_dir, "repo_summary.md")
        with open(summary_path, 'w', encoding='utf-8') as f:
            # Get basic info
            basic = repo_data["basic_info"]

            f.write(f"# Repository Summary: {basic['full_name']}\n\n")
            f.write(f"**Description:** {basic['description'] or 'No description'}\n\n")
            f.write(f"**URL:** {basic['html_url']}\n")
            f.write(f"**Created:** {basic['created_at']}\n")
            f.write(f"**Last updated:** {basic['updated_at']}\n")
            f.write(f"**Default branch:** {basic['default_branch']}\n")
            f.write(f"**Stars:** {basic['stargazers_count']}\n")
            f.write(f"**Forks:** {basic['forks_count']}\n")
            f.write(f"**Open issues:** {basic['open_issues_count']}\n\n")

            # Analysis timestamp
            f.write(f"*Analysis performed: {repo_data['timestamp']}*\n\n")

            # Languages
            if repo_data["languages"]:
                f.write("## Languages\n\n")
                total = sum(repo_data["languages"].values())
                for lang, bytes_count in repo_data["languages"].items():
                    percentage = (bytes_count / total) * 100
                    f.write(f"- **{lang}**: {percentage:.1f}% ({bytes_count} bytes)\n")
                f.write("\n")

            # Contributors
            if repo_data["contributors"]:
                f.write("## Top Contributors\n\n")
                for i, contributor in enumerate(repo_data["contributors"][:10], 1):
                    f.write(f"{i}. {contributor['login']} - {contributor['contributions']} contributions\n")
                f.write("\n")

            # Repository Activity
            if repo_data["temporal_analysis"]["weekly_commits"]:
                f.write("## Repository Activity\n\n")

                # Recent commit activity
                recent_weeks = repo_data["temporal_analysis"]["weekly_commits"][-10:]
                f.write("### Recent Commit Activity\n\n")
                f.write("| Week | Commits |\n")
                f.write("|------|--------|\n")
                for week in recent_weeks:
                    f.write(f"| {week['date']} | {week['total']} |\n")
                f.write("\n")

                # Issue and PR stats
                issue_timeline = repo_data["temporal_analysis"]["issue_timeline"]
                pr_timeline = repo_data["temporal_analysis"]["pr_timeline"]

                if issue_timeline and issue_timeline.get('resolution_times'):
                    avg_resolution = np.mean(issue_timeline['resolution_times'])
                    median_resolution = np.median(issue_timeline['resolution_times'])

                    f.write("### Issue Statistics\n\n")
                    f.write(f"- Average time to close issues: {avg_resolution:.2f} hours ({avg_resolution/24:.2f} days)\n")
                    f.write(f"- Median time to close issues: {median_resolution:.2f} hours ({median_resolution/24:.2f} days)\n")
                    f.write(f"- Issues analyzed: {len(issue_timeline['resolution_times'])}\n\n")

                if pr_timeline and pr_timeline.get('merge_times'):
                    avg_merge = np.mean(pr_timeline['merge_times'])
                    median_merge = np.median(pr_timeline['merge_times'])

                    f.write("### Pull Request Statistics\n\n")
                    f.write(f"- PR acceptance rate: {pr_timeline['acceptance_rate']:.2f}%\n")
                    f.write(f"- Average time to merge PRs: {avg_merge:.2f} hours ({avg_merge/24:.2f} days)\n")
                    f.write(f"- Median time to merge PRs: {median_merge:.2f} hours ({median_merge/24:.2f} days)\n")
                    f.write(f"- PRs analyzed: {len(pr_timeline['merge_times'])}\n\n")

            # Code Complexity
            if repo_data["text_content"]["complexity_metrics"]["cyclomatic_complexity"]:
                f.write("## Code Complexity\n\n")

                complexity_data = repo_data["text_content"]["complexity_metrics"]["cyclomatic_complexity"]
                complexity_data.sort(key=lambda x: x[1], reverse=True)

                f.write("### Most Complex Files\n\n")
                f.write("| File | Cyclomatic Complexity |\n")
                f.write("|------|------------------------|\n")

                for path, cc in complexity_data[:10]:
                    f.write(f"| {path} | {cc} |\n")

                f.write("\n")

                # Get aggregate metrics
                """
                cc_values = [cc for _, cc in complexity_data]
                f.write(f"- **Average complexity**: {np.mean(cc_values):.2f}\n")
                f.write(f"- **Median complexity**: {np.median(cc_values):.2f}\n")
                f.write(f"- **Max complexity**: {np.max(cc_values)}\n")
                f.write(f"- **Files analyzed**: {len(cc_values)}\n\n")
                """
                cc_values = []
                for _, cc in complexity_data:
                    try:
                        # Handle different possible types
                        if isinstance(cc, (int, float)):
                            cc_values.append(float(cc))
                        elif isinstance(cc, list) and len(cc) > 0:
                            # If it's a list, try to get first numeric item
                            cc_values.append(float(cc[0]))
                        else:
                            # Try simple conversion as fallback
                            cc_values.append(float(cc))
                    except (ValueError, TypeError):
                        # Skip this value if conversion fails
                        continue
                if cc_values:
                    f.write(f"- **Average complexity**: {np.mean(cc_values):.2f}\n")
                    f.write(f"- **Median complexity**: {np.median(cc_values):.2f}\n")
                    f.write(f"- **Max complexity**: {max(cc_values)}\n")
                    f.write(f"- **Files analyzed**: {len(cc_values)}\n\n")
                else:
                    f.write("- **Complexity metrics**: Could not be calculated\n\n")

            # Code Dependencies
            if repo_data["text_content"]["dependencies"]:
                f.write("## Code Dependencies\n\n")

                external_deps = repo_data["text_content"]["dependencies"]["external"]

                # Count unique external dependencies
                all_external = set()
                for deps in external_deps.values():
                    all_external.update(deps)

                # Find most imported packages
                ext_counts = Counter()
                for deps in external_deps.values():
                    ext_counts.update(deps)

                top_imports = ext_counts.most_common(10)

                f.write("### Most Used External Dependencies\n\n")
                f.write("| Package | Used in # Files |\n")
                f.write("|---------|----------------|\n")

                for pkg, count in top_imports:
                    f.write(f"| {pkg} | {count} |\n")

                f.write("\n")

            # Code Summary
            if repo_data["text_content"]["code_summary"]:
                f.write("## Code Structure\n\n")

                # Get summary of most significant files
                complexity_data = repo_data["text_content"]["complexity_metrics"]["cyclomatic_complexity"]
                complexity_data.sort(key=lambda x: x[1], reverse=True)

                for path, _ in complexity_data[:5]:
                    summary = repo_data["text_content"]["code_summary"].get(path)
                    if summary:
                        f.write(f"### {path}\n\n")

                        if summary.get("description"):
                            f.write(f"{summary['description']}\n\n")

                        if summary.get("classes"):
                            f.write("**Classes:**\n\n")
                            for cls in summary["classes"]:
                                f.write(f"- `{cls}`\n")
                            f.write("\n")

                        if summary.get("functions"):
                            f.write("**Functions:**\n\n")
                            for func in summary["functions"]:
                                f.write(f"- `{func}()`\n")
                            f.write("\n")

                        if summary.get("imports"):
                            f.write("**Imports:**\n\n")
                            for imp in summary["imports"][:10]:  # Limit to top 10
                                if isinstance(imp, tuple):
                                    imp = ' '.join(filter(None, imp))
                                f.write(f"- `{imp}`\n")
                            f.write("\n")

    # --- NEW METHOD for getting specific PR details ---
    def get_pull_request_details(self, owner, repo, pr_number):
        """Get detailed information for a specific Pull Request using PyGithub."""
        if not self.github:
            print("PyGithub client not initialized. Cannot fetch PR details.")
            # Fallback maybe? Or just return None
            # You could try a direct REST call here if needed
            return None

        try:
            repo_obj = self.github.get_repo(f"{owner}/{repo}")
            pr = repo_obj.get_pull(pr_number)

            # Extract relevant information into a dictionary
            details = {
                "number": pr.number,
                "title": pr.title,
                "state": pr.state, # 'open', 'closed'
                "merged": pr.merged,
                "body": pr.body or "", # Ensure body is string
                "url": pr.html_url,
                "created_at": pr.created_at.isoformat() if pr.created_at else None,
                "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                "closed_at": pr.closed_at.isoformat() if pr.closed_at else None,
                "merged_at": pr.merged_at.isoformat() if pr.merged_at else None,
                "author": pr.user.login if pr.user else "N/A",
                "commits_count": pr.commits,
                "additions": pr.additions,
                "deletions": pr.deletions,
                "changed_files_count": pr.changed_files,
                "labels": [label.name for label in pr.labels],
                "assignees": [assignee.login for assignee in pr.assignees],
                "milestone": pr.milestone.title if pr.milestone else None,
                "repo_full_name": f"{owner}/{repo}", # Add repo context
                # Add more fields if needed (e.g., comments, reviews)
            }
            return details

        except GithubException as e:
            if e.status == 404:
                print(f"Error: Pull Request #{pr_number} not found in {owner}/{repo}.")
            else:
                print(f"Error fetching PR #{pr_number} details: {e}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred fetching PR details: {e}")
            return None


# --- Colab Helpers (Keep these as provided) ---
try:
    from google.colab import files
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

# ...(keep download_file and save_json_to_colab functions)...
class CustomJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, set):
                return list(obj)
            elif isinstance(obj, (datetime, np.datetime64)):
                 # Handle both standard datetime and numpy datetime64
                if isinstance(obj, np.datetime64):
                     # Convert numpy datetime64 to standard datetime
                     ts = pd.to_datetime(obj)
                     return ts.isoformat()
                return obj.isoformat()
            elif isinstance(obj, (np.int64, np.int32)):
                 return int(obj)
            elif isinstance(obj, (np.float64, np.float32)):
                 return float(obj)
            elif hasattr(obj, '__dict__'):
                 # Be careful with complex objects, might expose too much
                 # Consider filtering attributes if needed
                 return {k: v for k, v in obj.__dict__.items() if not k.startswith('_') and not callable(v)}
            # Let the base class default method raise the TypeError
            return super(CustomJSONEncoder, self).default(obj)

def convert_sets_to_lists(obj):
    # Recursive function to convert sets and handle numpy types
    if isinstance(obj, dict):
        return {k: convert_sets_to_lists(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_sets_to_lists(i) for i in obj]
    elif isinstance(obj, set):
        return [convert_sets_to_lists(i) for i in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_sets_to_lists(i) for i in obj)
    elif isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
         return float(obj)
    elif isinstance(obj, np.datetime64):
         ts = pd.to_datetime(obj)
         return ts.isoformat()
    elif isinstance(obj, np.bool_):
         return bool(obj)
    elif isinstance(obj, np.ndarray):
         return convert_sets_to_lists(obj.tolist()) # Convert numpy arrays to lists
    else:
        # Attempt to handle other non-serializable types gracefully
        try:
            json.dumps(obj) # Test if serializable
            return obj
        except TypeError:
            return str(obj) # Convert to string as a fallback

def save_json_to_colab(data, filename='/content/repo_info.json'):
    """Save JSON data to a file in Colab and provide download option."""
    # ... (rest of the save_json_to_colab function using the above helpers) ...
    converted_data = convert_sets_to_lists(data)
    try:
        with open(filename, 'w') as f:
            json.dump(converted_data, f, indent=2, cls=CustomJSONEncoder)
        print(f"Data saved to {filename}")
        if IN_COLAB:
            print("To download the JSON file, run the following cell:")
            print(f"from google.colab import files")
            print(f"files.download('{filename}')")
    except TypeError as e:
        print(f"Error saving JSON: {e}")
        print("There might be non-serializable data types remaining.")


# --- GraphRepoAnalyzer Class ---
class GraphRepoAnalyzer:
    """Integrates GitHub analysis with Neo4j and Gemini."""

    # --- Keep ALL existing methods from the previous version ---
    # ... ( __init__, close, _create_neo4j_constraints, _run_cypher, ...)
    def __init__(self, github_token=None, neo4j_uri=None, neo4j_user=None, neo4j_password=None, gemini_api_key=None):
        """Initialize with credentials."""
        load_dotenv() # Load .env file if it exists

        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USERNAME")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")

        if not all([self.neo4j_uri, self.neo4j_user, self.neo4j_password]):
            print("Warning: Neo4j credentials not fully provided. Graph features will be disabled.")
            self.neo4j_driver = None
        else:
            try:
                # Use basic_auth for Neo4j driver authentication
                self.neo4j_driver = GraphDatabase.driver(self.neo4j_uri, auth=basic_auth(self.neo4j_user, self.neo4j_password))
                self.neo4j_driver.verify_connectivity()
                print("Successfully connected to Neo4j.")
                self._create_neo4j_constraints()
            except Exception as e:
                print(f"Error connecting to Neo4j: {e}")
                print("Graph features will be disabled.")
                self.neo4j_driver = None

        if not self.gemini_api_key:
            print("Warning: Google API Key not provided. Gemini features will be disabled.")
            self.gemini_model = None
        else:
            try:
                genai.configure(api_key=self.gemini_api_key)
                # Use the latest Gemini 1.5 Pro model
                self.gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
                print("Claude model initialized.")
            except Exception as e:
                print(f"Error initializing Gemini: {e}")
                self.gemini_model = None

        self.github_analyzer = GitHubRepoInfo(token=self.github_token)
        self.repo_data = None
        self.repo_full_name = None # Store repo name for context

    def close(self):
        """Close the Neo4j driver connection."""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            print("Neo4j connection closed.")

    def _create_neo4j_constraints(self):
        """Create unique constraints for better performance and data integrity."""
        if not self.neo4j_driver: return
        constraints = [
            "CREATE CONSTRAINT repo_name IF NOT EXISTS FOR (r:Repository) REQUIRE r.fullName IS UNIQUE;",
            "CREATE CONSTRAINT user_login IF NOT EXISTS FOR (u:User) REQUIRE u.login IS UNIQUE;",
            "CREATE CONSTRAINT commit_sha IF NOT EXISTS FOR (c:Commit) REQUIRE c.sha IS UNIQUE;",
            "CREATE CONSTRAINT file_path IF NOT EXISTS FOR (f:File) REQUIRE f.path IS UNIQUE;",
            "CREATE CONSTRAINT lang_name IF NOT EXISTS FOR (l:Language) REQUIRE l.name IS UNIQUE;",
            "CREATE CONSTRAINT dep_name IF NOT EXISTS FOR (d:Dependency) REQUIRE d.name IS UNIQUE;",
            "CREATE CONSTRAINT issue_num IF NOT EXISTS FOR (i:Issue) REQUIRE i.number IS UNIQUE;", # Assumes issue number is unique within repo context - adjust if needed
            "CREATE CONSTRAINT pr_num IF NOT EXISTS FOR (p:PullRequest) REQUIRE p.number IS UNIQUE;", # Same assumption for PRs
        ]
        try:
            with self.neo4j_driver.session() as session:
                for constraint in constraints:
                    session.run(constraint)
            print("Neo4j constraints ensured.")
        except Exception as e:
            print(f"Error creating Neo4j constraints: {e}")


    def _run_cypher(self, query, parameters=None):
        """Helper function to run Cypher queries."""
        if not self.neo4j_driver:
            print("Neo4j connection not available.")
            return None
        try:
            with self.neo4j_driver.session() as session:
                result = session.run(query, parameters)
                return [record.data() for record in result] # Return results as list of dicts
        except Exception as e:
            print(f"Error running Cypher query: {e}")
            print(f"Query: {query}")
            print(f"Parameters: {parameters}")
            return None

    # ... ( _populate_basic_info, _populate_contributors, _populate_commits, ...)

    def _populate_basic_info(self, tx, repo_node, basic_info):
        """Populate basic repo info and owner."""
        owner_login = basic_info.get('owner', {}).get('login')
        if owner_login:
            tx.run("""
                MERGE (u:User {login: $owner_login})
                ON CREATE SET u.avatarUrl = $avatar_url, u.type = $owner_type
                MERGE (r)-[:OWNED_BY]->(u)
                """, owner_login=owner_login,
                     avatar_url=basic_info.get('owner', {}).get('avatar_url'),
                     owner_type=basic_info.get('owner', {}).get('type'))

        # Add languages
        languages = self.repo_data.get("languages", {})
        if languages:
            for lang, bytes_count in languages.items():
                tx.run("""
                    MERGE (l:Language {name: $lang})
                    MERGE (repo)-[rel:USES_LANGUAGE]->(l)
                    SET rel.bytes = $bytes_count
                    """, repo=repo_node, lang=lang, bytes_count=bytes_count)

    def _populate_contributors(self, tx, repo_node):
        """Populate contributors."""
        contributors = self.repo_data.get("contributors", [])
        if contributors:
            for contrib in contributors:
                tx.run("""
                    MERGE (u:User {login: $login})
                    ON CREATE SET u.avatarUrl = $avatar_url, u.profileUrl = $profile_url
                    MERGE (repo)-[rel:HAS_CONTRIBUTOR]->(u)
                    SET rel.contributions = $contributions
                    """, repo=repo_node, login=contrib['login'],
                         avatar_url=contrib.get('avatar_url'),
                         profile_url=contrib.get('html_url'),
                         contributions=contrib['contributions'])

    def _populate_commits(self, tx, repo_node):
        """Populate recent commits and link authors."""
        commits = self.repo_data.get("recent_commits", [])
        if commits:
            for commit_data in commits:
                sha = commit_data['sha']
                commit_info = commit_data['commit']
                author_info = commit_info.get('author', {})
                committer_info = commit_info.get('committer', {})
                author_login = commit_data.get('author', {}).get('login') # GitHub user if linked
                committer_login = commit_data.get('committer', {}).get('login')

                # Create commit node
                tx.run("""
                    MERGE (c:Commit {sha: $sha})
                    ON CREATE SET c.message = $message, c.date = datetime($date)
                    MERGE (repo)-[:HAS_COMMIT]->(c)
                    """, repo=repo_node, sha=sha,
                         message=commit_info.get('message', '')[:500], # Limit message size
                         date=author_info.get('date')) # Use author date

                # Link author (if GitHub user)
                if author_login:
                    tx.run("""
                        MATCH (c:Commit {sha: $sha})
                        MERGE (u:User {login: $login})
                        MERGE (u)-[:AUTHORED]->(c)
                        """, sha=sha, login=author_login)
                # Else, could store author name/email on commit node if needed

                # Link committer (if GitHub user and different from author)
                if committer_login and committer_login != author_login:
                     tx.run("""
                        MATCH (c:Commit {sha: $sha})
                        MERGE (u:User {login: $login})
                        MERGE (u)-[:COMMITTED]->(c)
                        """, sha=sha, login=committer_login)

    # ... ( _populate_files_and_code, _populate_dependencies, populate_neo4j_graph, ...)
    def _populate_files_and_code(self, tx, repo_node):
        """Populate files, basic structure, and code analysis results."""
        code_summary = self.repo_data.get("text_content", {}).get("code_summary", {})
        text_files = self.repo_data.get("text_content", {}).get("text_files", [])

        # Create file nodes first
        for file_info in text_files:
            path = file_info['path']
            name = file_info['name']
            extension = os.path.splitext(name)[1].lower()
            is_code = extension in ['.py', '.js', '.ts', '.jsx', '.tsx'] # Add more if needed

            tx.run("""
                MERGE (f:File {path: $path})
                ON CREATE SET f.name = $name, f.extension = $extension, f.isCode = $is_code
                MERGE (repo)-[:CONTAINS_FILE]->(f)
                """, repo=repo_node, path=path, name=name, extension=extension, is_code=is_code)

            # If it's a code file with analysis, add details
            if path in code_summary:
                summary = code_summary[path]
                metrics = summary.get('metrics', {})
                complexity = summary.get('complexity', {})

                # Add metrics
                if metrics:
                    tx.run("""
                        MATCH (f:File {path: $path})
                        SET f.linesTotal = $total, f.linesCode = $code, f.linesComment = $comment, f.linesBlank = $blank, f.commentRatio = $ratio
                        """, path=path, total=metrics.get('total_lines'), code=metrics.get('code_lines'),
                             comment=metrics.get('comment_lines'), blank=metrics.get('blank_lines'),
                             ratio=metrics.get('comment_ratio'))

                # Add complexity
                if complexity:
                    tx.run("""
                        MATCH (f:File {path: $path})
                        SET f.complexityCyclomatic = $cc, f.maintainabilityIndex = $mi
                        """, path=path, cc=complexity.get('overall'), mi=complexity.get('maintainability_index'))

                # Add Functions (if language supports detailed analysis)
                for func in summary.get("detailed_functions", []):
                     # Ensure func_name is a string
                    func_name = str(func.get('name', 'unknown_function'))
                    tx.run("""
                        MATCH (f:File {path: $path})
                        MERGE (fn:Function {name: $func_name, file: $path}) // Unique by name + file path
                        ON CREATE SET fn.args = $args, fn.complexity = $cc, fn.docstring = $doc
                        MERGE (f)-[:DEFINES_FUNCTION]->(fn)
                        """, path=path, func_name=func_name,
                             args=json.dumps(func.get('args', [])), # Store args as JSON string
                             cc=func.get('complexity'),
                             doc=func.get('docstring', '')[:200]) # Limit docstring

                # Add Classes (if language supports detailed analysis)
                for cls in summary.get("detailed_classes", []):
                     # Ensure cls_name is a string
                    cls_name = str(cls.get('name', 'unknown_class'))
                    tx.run("""
                        MATCH (f:File {path: $path})
                        MERGE (cl:Class {name: $cls_name, file: $path}) // Unique by name + file path
                        ON CREATE SET cl.methods = $methods, cl.docstring = $doc, cl.extends = $extends
                        MERGE (f)-[:DEFINES_CLASS]->(cl)
                        """, path=path, cls_name=cls_name,
                             methods=json.dumps([m['name'] for m in cls.get('methods', [])]), # Store method names
                             doc=cls.get('docstring', '')[:200],
                             extends=cls.get('extends')) # If JS/TS analysis provides it


    def _populate_dependencies(self, tx, repo_node):
        """Populate internal and external code dependencies."""
        dependencies = self.repo_data.get("text_content", {}).get("dependencies", {})
        internal_deps = dependencies.get('internal', {})
        external_deps = dependencies.get('external', {})

        # Internal Dependencies (File -> File)
        for source_path, target_paths in internal_deps.items():
            for target_path in target_paths:
                 # Ensure both files exist before creating relationship
                tx.run("""
                    MATCH (source:File {path: $source_path}), (target:File {path: $target_path})
                    WHERE EXISTS(source.path) AND EXISTS(target.path) // Ensure nodes exist
                    MERGE (source)-[:DEPENDS_ON]->(target)
                    """, source_path=source_path, target_path=target_path)

        # External Dependencies (File -> Dependency)
        for source_path, package_names in external_deps.items():
            for package_name in package_names:
                 # Ensure package name is valid before creating
                if package_name and isinstance(package_name, str):
                    tx.run("""
                        MATCH (source:File {path: $source_path})
                        WHERE EXISTS(source.path) // Ensure source file exists
                        MERGE (dep:Dependency {name: $package_name})
                        MERGE (source)-[:IMPORTS]->(dep)
                        """, source_path=source_path, package_name=package_name)


    def populate_neo4j_graph(self):
        """Populate the Neo4j graph with data from self.repo_data."""
        if not self.neo4j_driver:
            print("Neo4j connection not available. Skipping graph population.")
            return
        if not self.repo_data or not self.repo_data.get("basic_info"):
            print("No repository data available to populate the graph.")
            return

        basic_info = self.repo_data["basic_info"]
        full_name = basic_info['full_name']
        print(f"Populating Neo4j graph for repository: {full_name}")

        try:
            with self.neo4j_driver.session(database="neo4j") as session: # Ensure using correct database if needed
                # Create/Merge Repository Node
                repo_result = session.execute_write(
                    lambda tx: tx.run("""
                        MERGE (r:Repository {fullName: $full_name})
                        ON CREATE SET
                            r.name = $name,
                            r.owner = $owner,
                            r.description = $description,
                            r.url = $url,
                            r.createdAt = datetime($created_at),
                            r.updatedAt = datetime($updated_at),
                            r.stars = $stars,
                            r.forks = $forks,
                            r.openIssues = $open_issues,
                            r.language = $language,
                            r.license = $license
                        RETURN r
                        """, full_name=full_name,
                                       name=basic_info['name'],
                                       owner=basic_info['owner']['login'],
                                       description=basic_info.get('description', ''),
                                       url=basic_info['html_url'],
                                       created_at=basic_info['created_at'],
                                       updated_at=basic_info['updated_at'],
                                       stars=basic_info['stargazers_count'],
                                       forks=basic_info['forks_count'],
                                       open_issues=basic_info['open_issues_count'],
                                       language=basic_info.get('language'),
                                       license=basic_info.get('license', {}).get('name')
                                       ).single()[0] # Get the repo node itself
                )

                # Call helper functions within transactions for atomicity
                session.execute_write(self._populate_basic_info, repo_result, basic_info)
                session.execute_write(self._populate_contributors, repo_result)
                session.execute_write(self._populate_commits, repo_result)
                session.execute_write(self._populate_files_and_code, repo_result)
                session.execute_write(self._populate_dependencies, repo_result)
                # Add calls for issues, PRs etc. if needed

            print(f"Successfully populated graph for {full_name}.")

        except Exception as e:
            print(f"Error populating Neo4j graph: {e}")


    # ... ( analyze_repo, _get_graph_summary_for_llm, _node_to_string, ...)
    def analyze_repo(self, owner, repo, display=True, save_json=False, export_text=False):
        """Fetch, analyze, display, and optionally populate graph."""
        self.owner = owner
        self.repo = repo
        self.repo_full_name = f"{owner}/{repo}"
        print(f"\nFetching repository information for {self.repo_full_name}...")
        # Use the github_analyzer instance associated with this GraphRepoAnalyzer
        self.repo_data = self.github_analyzer.get_all_info(owner, repo)

        if self.repo_data:
            if display:
                print("\nGenerating visualizations and analysis...")
                self.github_analyzer.display_repo_info(self.repo_data)
                self.github_analyzer.display_code_files(self.repo_data) # Show code preview

            if self.neo4j_driver:
                 populate = input("\nPopulate Neo4j graph with this data? (y/n): ").lower() == 'y'
                 if populate:
                     self.populate_neo4j_graph()

            if save_json:
                default_filename = f'/content/{self.repo}_info.json' if IN_COLAB else f'./{self.repo}_info.json'
                filename = input(f"Enter filename for JSON output (default: {default_filename}): ") or default_filename
                save_json_to_colab(self.repo_data, filename) # Use the enhanced save function

            if export_text:
                default_dir = f'/content/{self.repo}_text' if IN_COLAB else f'./{self.repo}_text'
                output_dir = input(f"Enter output directory for text export (default: {default_dir}): ") or default_dir
                self.github_analyzer.export_repo_text(self.repo_data, output_dir)
        else:
            print(f"Failed to get repository information for {self.repo_full_name}")

    def _get_graph_summary_for_llm(self, max_nodes=10, max_rels=20):
        """Fetch a small, representative sample of the graph for LLM context."""
        if not self.neo4j_driver or not self.repo_full_name:
            return "No graph data available."

        # Get counts
        node_counts_query = "MATCH (n) RETURN labels(n) AS label, count(*) AS count"
        rel_counts_query = "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count"
        node_counts = self._run_cypher(node_counts_query)
        rel_counts = self._run_cypher(rel_counts_query)

        # Get sample nodes/rels related to the repo
        sample_query = """
        MATCH (repo:Repository {fullName: $repo_name})
        // Get repo node, owner, some contributors, some files, some commits
        OPTIONAL MATCH (repo)-[:OWNED_BY]->(owner:User)
        OPTIONAL MATCH (repo)-[:HAS_CONTRIBUTOR]->(contrib:User)
        WITH repo, owner, collect(contrib)[..5] AS contributors // Limit contributors
        OPTIONAL MATCH (repo)-[:CONTAINS_FILE]->(file:File)
        WITH repo, owner, contributors, collect(file)[..10] AS files // Limit files
        OPTIONAL MATCH (repo)-[:HAS_COMMIT]->(commit:Commit)
        WITH repo, owner, contributors, files, collect(commit)[..5] AS commits // Limit commits
        // Get relationships between these sampled nodes
        CALL apoc.path.subgraphNodes([repo, owner] + contributors + files + commits, {
            maxLevel: 1, relationshipFilter:'>' // Only outgoing relationships from these nodes
        }) YIELD node
        MATCH (n)-[r]->(m)
        WHERE n IN [repo, owner] + contributors + files + commits AND m IN [repo, owner] + contributors + files + commits
        RETURN n AS source, type(r) AS relationship, m AS target
        LIMIT $max_rels
        """
        # Note: Needs APOC installed in Neo4j for subgraphNodes.
        # Simpler alternative without APOC: Fetch specific relationships manually.
        # Example simple alternative:
        # sample_query_simple = """
        # MATCH (repo:Repository {fullName: $repo_name})
        # OPTIONAL MATCH (repo)-[r1:OWNED_BY|:HAS_CONTRIBUTOR|:CONTAINS_FILE|:HAS_COMMIT]->(related)
        # WITH repo, type(r1) as rel_type, related LIMIT 15
        # RETURN repo AS source, rel_type AS relationship, related AS target
        # """

        try:
             # Attempt APOC query first
            graph_sample = self._run_cypher(sample_query, {"repo_name": self.repo_full_name, "max_rels": max_rels})
        except Exception as e:
             print(f"APOC query failed ({e}), trying simpler graph sample query.")
             sample_query_simple = """
             MATCH (repo:Repository {fullName: $repo_name})
             OPTIONAL MATCH (repo)-[r1:OWNED_BY|:HAS_CONTRIBUTOR|:CONTAINS_FILE|:HAS_COMMIT|:USES_LANGUAGE]->(related)
             WITH repo, type(r1) as rel_type, related LIMIT $max_rels
             RETURN repo AS source, rel_type AS relationship, related AS target
             UNION
             MATCH (repo:Repository {fullName: $repo_name})<-[r2:AUTHORED|:COMMITTED]-(user:User)
             WITH repo, type(r2) as rel_type, user LIMIT $max_rels
             RETURN user AS source, rel_type AS relationship, repo AS target // Show user -> repo link
             UNION
             MATCH (file:File)<-[:CONTAINS_FILE]-(repo:Repository {fullName: $repo_name})
             OPTIONAL MATCH (file)-[r3:DEFINES_FUNCTION|:DEFINES_CLASS|:DEPENDS_ON|:IMPORTS]->(related_code)
             WITH file, type(r3) as rel_type, related_code LIMIT $max_rels
             RETURN file AS source, rel_type AS relationship, related_code AS target
             """
             graph_sample = self._run_cypher(sample_query_simple, {"repo_name": self.repo_full_name, "max_rels": max_rels})


        summary = "Graph Context Summary:\n"
        if node_counts:
             summary += "Node Counts: " + ", ".join([f"{c['label'][0]}: {c['count']}" for c in node_counts if c['label']]) + "\n"
        if rel_counts:
             summary += "Relationship Counts: " + ", ".join([f"{r['type']}: {r['count']}" for r in rel_counts if r['type']]) + "\n"
        if graph_sample:
             summary += f"\nSample Relationships (up to {max_rels}):\n"
             for rel in graph_sample:
                 # Safely extract node properties for display
                 source_repr = self._node_to_string(rel.get('source'))
                 target_repr = self._node_to_string(rel.get('target'))
                 rel_type = rel.get('relationship', 'UNKNOWN_REL')
                 if source_repr and target_repr and rel_type:
                    summary += f"- ({source_repr})-[:{rel_type}]->({target_repr})\n"
        else:
             summary += "No specific graph sample retrieved.\n"

        return summary.strip()

    def _node_to_string(self, node):
        """Helper to create a string representation of a Neo4j node."""
        if not node or not hasattr(node, 'labels') or not hasattr(node, 'items'):
            return None

        label = list(node.labels)[0] if node.labels else 'Node'
        props = dict(node.items())
        # Choose a representative property
        if 'fullName' in props: name = props['fullName']
        elif 'login' in props: name = props['login']
        elif 'path' in props: name = os.path.basename(props['path']) # Show file name
        elif 'name' in props: name = props['name']
        elif 'sha' in props: name = props['sha'][:7] # Short SHA
        elif 'number' in props: name = f"#{props['number']}"
        else: name = node.element_id # Fallback to element ID

        # Limit name length
        name_str = str(name)
        if len(name_str) > 40:
             name_str = name_str[:37] + "..."

        return f"{label}:{name_str}"




    def _get_pr_summary_prompt(self, pr_details, role):
        """Generates the Gemini prompt for PR summarization based on role."""
        # Extract key details safely
        title = pr_details.get('title', 'N/A')
        body = pr_details.get('body', 'No description provided.')
        pr_number = pr_details.get('number', 'N/A')
        repo_name = pr_details.get('repo_full_name', 'N/A')
        author = pr_details.get('author', 'N/A')
        state = pr_details.get('state', 'N/A')
        merged_status = 'Merged' if pr_details.get('merged') else ('Closed' if state == 'closed' else 'Open')
        created_at = pr_details.get('created_at', 'N/A')
        commits_count = pr_details.get('commits_count', 'N/A')
        changed_files = pr_details.get('changed_files_count', 'N/A')
        additions = pr_details.get('additions', 'N/A')
        deletions = pr_details.get('deletions', 'N/A')
        labels = ', '.join(pr_details.get('labels', [])) or 'None'

        # Truncate long body
        max_body_len = 1500
        truncated_body = body[:max_body_len] + ('...' if len(body) > max_body_len else '')

        base_prompt = f"""
You are an AI assistant specializing in summarizing GitHub Pull Requests.
Analyze the following Pull Request details from repository '{repo_name}' and provide a summary tailored for a '{role}'.

**Pull Request #{pr_number}: {title}**
*   **Author:** {author}
*   **Status:** {state.capitalize()} ({merged_status})
*   **Created:** {created_at}
*   **Commits:** {commits_count}
*   **Changed Files:** {changed_files}
*   **Code Churn:** +{additions} / -{deletions} lines
*   **Labels:** {labels}
*   **Description/Body:**
{truncated_body}
---
"""
        role_instructions = ""
        # Define role-specific instructions
        if role == 'Developer':
            role_instructions = """
**Summary Focus (Developer):**
*   Summarize the core technical changes and their purpose.
*   Identify key files, modules, or functions affected.
*   Mention any potential technical complexities, risks, or areas needing careful code review (based *only* on the description and metadata).
*   Note any mention of tests added or modified.
*   Be concise and focus on technical aspects relevant for peer review or understanding the change.
"""
        elif role == 'Manager' or role == 'Team Lead':
             role_instructions = """
**Summary Focus (Manager/Team Lead):**
*   Explain the high-level purpose and business value (what problem does this PR solve or what feature does it add?).
*   Summarize the overall status (e.g., Ready for Review, Needs Work, Merged, Blocked?).
*   Give a sense of the PR's size/complexity (e.g., Small/Medium/Large based on file/line changes and description).
*   Highlight any mentioned risks, blockers, or dependencies on other work.
*   Include the author and key dates (created, merged/closed).
*   Focus on information needed for tracking progress and impact.
"""
        elif role == 'Program Manager' or role == 'Product Owner':
            role_instructions = """
**Summary Focus (Program/Product Manager):**
*   Describe the user-facing impact or the feature/bug fix being addressed.
*   Relate the PR to product goals or requirements if possible (based on title/body/labels).
*   Note the status (especially if merged or closed).
*   Mention associated issues or tickets if referenced in the body (though not explicitly provided here, look for patterns like '#123').
*   Focus on 'what' and 'why' from a product perspective.
"""
        else: # Default/General
            role_instructions = """
**Summary Focus (General):**
*   State the main goal or purpose of the PR clearly.
*   Identify the author and the current status (Open/Closed/Merged).
*   Provide a brief, balanced overview of the key changes made.
*   Keep the summary accessible to a wider audience.
"""

        return base_prompt + role_instructions + "\n**Summary:**" # Ask for summary explicitly


    def summarize_pull_request(self, pr_number, role):
        """Fetches PR details and generates a role-based summary using Gemini."""
        if not self.gemini_model:
            return "Gemini model not initialized. Cannot generate summary."
        if not self.owner or not self.repo:
             return "Repository owner and name not set. Analyze a repository first."
        # Use the github_analyzer instance created in __init__
        if not self.github_analyzer:
             return "GitHub Analyzer not initialized."


        print(f"\nFetching details for PR #{pr_number} in {self.repo_full_name}...")
        pr_details = self.github_analyzer.get_pull_request_details(self.owner, self.repo, pr_number)

        if not pr_details:
            return f"Could not retrieve details for PR #{pr_number}."

        print(f"Generating summary for role: {role}...")

        # Generate the role-specific prompt
        prompt = self._get_pr_summary_prompt(pr_details, role)

        # 4. Send to Gemini and Get Response
        try:
            # print("--- Sending Prompt to Gemini ---")
            # print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt) # Debug: Print truncated prompt
            # print("-----------------------------")

            response = self.gemini_model.generate_content(prompt)

            print("\n--- Gemini PR Summary ---")
            summary_text = response.text
            display(Markdown(summary_text))
            print("------------------------")
            return summary_text

        except Exception as e:
            print(f"Error communicating with Gemini for PR summary: {e}")
            return f"Error asking Gemini: {e}"
    # ... ( _get_repo_summary_for_llm, ask_gemini_about_repo )
    def _get_repo_summary_for_llm(self):
        """Create a concise text summary of the repo_data for the LLM prompt."""
        if not self.repo_data or not self.repo_data.get("basic_info"):
            return "No repository data available."

        basic = self.repo_data["basic_info"]
        summary = f"Repository Summary: {basic['full_name']}\n"
        summary += f"Description: {basic.get('description', 'N/A')}\n"
        summary += f"Stars: {basic.get('stargazers_count', 0)}, Forks: {basic.get('forks_count', 0)}, Open Issues: {basic.get('open_issues_count', 0)}\n"
        summary += f"Main Language: {basic.get('language', 'N/A')}\n"
        summary += f"Last Updated: {basic.get('updated_at', 'N/A')}\n"

        if self.repo_data.get("languages"):
            langs = list(self.repo_data["languages"].keys())
            summary += f"Languages Used: {', '.join(langs[:5])}{'...' if len(langs) > 5 else ''}\n"

        if self.repo_data.get("contributors"):
            contribs = [c['login'] for c in self.repo_data["contributors"][:5]]
            summary += f"Top Contributors: {', '.join(contribs)}{'...' if len(self.repo_data['contributors']) > 5 else ''}\n"

        if self.repo_data.get("text_content", {}).get("aggregate_metrics"):
            metrics = self.repo_data["text_content"]["aggregate_metrics"]
            summary += f"Code Metrics (approx): {metrics.get('total_code_lines', 0)} LoC, Comment Ratio: {metrics.get('average_comment_ratio', 0):.2f}\n"

        # Add complexity summary if available
        complexity_data = self.repo_data.get("text_content", {}).get("complexity_metrics",{}).get("cyclomatic_complexity", [])
        if complexity_data:
            cc_values = [c[1] for c in complexity_data if isinstance(c[1], (int, float))] # Extract valid numbers
            if cc_values:
                 summary += f"Avg Cyclomatic Complexity: {np.mean(cc_values):.2f}\n"

        # Add dependency summary if available
        deps = self.repo_data.get("text_content", {}).get("dependencies", {}).get("external", {})
        if deps:
             ext_counts = Counter()
             for dep_list in deps.values():
                 ext_counts.update(dep for dep in dep_list if isinstance(dep, str)) # Count valid string deps
             top_deps = ext_counts.most_common(5)
             if top_deps:
                 summary += f"Top External Dependencies: {', '.join([d[0] for d in top_deps])}\n"


        return summary.strip()

    def ask_gemini_about_repo(self, question):
        """Ask Gemini a question about the analyzed repository, using graph context."""
        if not self.gemini_model:
            return "Gemini model not initialized. Please provide GOOGLE_API_KEY."
        if not self.repo_data:
            return "No repository has been analyzed yet. Run analyze_repo() first."

        print("\nAsking Gemini...")

        # 1. Get Base Summary Context (from fetched GitHub data)
        repo_summary = self._get_repo_summary_for_llm()

        # 2. Get Graph Context (GraphRAG - Retrieval Step)
        #    (Simple version: get generic graph summary. Advanced: tailor query to question)
        graph_context = self._get_graph_summary_for_llm() # Use the helper

        # 3. Construct the Prompt
        prompt = f"""You are an expert software engineering assistant analyzing the GitHub repository '{self.repo_full_name}'.
You have access to the following information:

**Repository Summary (from GitHub API):**
{repo_summary}

**Knowledge Graph Context (Sample from Neo4j):**
{graph_context}

---

Based *only* on the information provided above, please answer the following question:

**Question:** {question}

---

Provide a concise and informative answer, referencing the data sources (summary or graph) where possible. If the information isn't available in the provided context, state that explicitly.
"""

        # 4. Send to Gemini and Get Response
        try:
            print("--- Sending Prompt to Gemini ---")
            print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt) # Print truncated prompt for review
            print("-----------------------------")

            response = self.gemini_model.generate_content(prompt)

            print("\n--- Gemini's Response ---")
            # Display response using Markdown for better formatting
            display(Markdown(response.text))
            print("------------------------")
            return response.text

        except Exception as e:
            print(f"Error communicating with Gemini: {e}")
            return f"Error asking Gemini: {e}"

    def __init__(self, github_token=None, neo4j_uri=None, neo4j_user=None, neo4j_password=None, gemini_api_key=None):
        """Initialize with credentials."""
        load_dotenv() # Load .env file if it exists

        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USERNAME")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY")

        self.neo4j_driver = None
        self.gemini_model = None
        # Initialize github_analyzer using the potentially updated GitHubRepoInfo
        self.github_analyzer = GitHubRepoInfo(token=self.github_token)

        if not all([self.neo4j_uri, self.neo4j_user, self.neo4j_password]):
            print("Warning: Neo4j credentials not fully provided. Graph features will be disabled.")
        else:
            try:
                self.neo4j_driver = GraphDatabase.driver(self.neo4j_uri, auth=basic_auth(self.neo4j_user, self.neo4j_password))
                self.neo4j_driver.verify_connectivity()
                print("Successfully connected to Neo4j.")
                self._create_neo4j_constraints()
            except Exception as e:
                print(f"Error connecting to Neo4j: {e}")
                print("Graph features will be disabled.")
                self.neo4j_driver = None

        if not self.gemini_api_key:
            print("Warning: Google API Key not provided. Gemini features will be disabled.")
        else:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp-01-21')
                print("Claude model model initialized.")
            except Exception as e:
                print(f"Error initializing Gemini: {e}")
                self.gemini_model = None

        self.repo_data = None
        self.repo_full_name = None # Store repo name for context
        self.owner = None # Store owner
        self.repo = None # Store repo name


    def analyze_repo(self, owner, repo, display=True, save_json=False, export_text=False):
        """Fetch, analyze, display, and optionally populate graph."""
        self.owner = owner
        self.repo = repo
        self.repo_full_name = f"{owner}/{repo}"
        print(f"\nFetching repository information for {self.repo_full_name}...")
        # Use the github_analyzer instance associated with this GraphRepoAnalyzer
        self.repo_data = self.github_analyzer.get_all_info(owner, repo)

        if self.repo_data:
            if display:
                print("\nGenerating visualizations and analysis...")
                self.github_analyzer.display_repo_info(self.repo_data)
                self.github_analyzer.display_code_files(self.repo_data) # Show code preview

            if self.neo4j_driver:
                 populate = input("\nPopulate Neo4j graph with this data? (y/n): ").lower() == 'y'
                 if populate:
                     self.populate_neo4j_graph()

            if save_json:
                default_filename = f'/content/{self.repo}_info.json' if IN_COLAB else f'./{self.repo}_info.json'
                filename = input(f"Enter filename for JSON output (default: {default_filename}): ") or default_filename
                save_json_to_colab(self.repo_data, filename) # Use the enhanced save function

            if export_text:
                default_dir = f'/content/{self.repo}_text' if IN_COLAB else f'./{self.repo}_text'
                output_dir = input(f"Enter output directory for text export (default: {default_dir}): ") or default_dir
                self.github_analyzer.export_repo_text(self.repo_data, output_dir)
        else:
            print(f"Failed to get repository information for {self.repo_full_name}")


    def _get_pr_summary_prompt(self, pr_details, role):
        """Generates the Gemini prompt for PR summarization based on role."""
        # Extract key details safely
        title = pr_details.get('title', 'N/A')
        body = pr_details.get('body', 'No description provided.')
        pr_number = pr_details.get('number', 'N/A')
        repo_name = pr_details.get('repo_full_name', 'N/A')
        author = pr_details.get('author', 'N/A')
        state = pr_details.get('state', 'N/A')
        merged_status = 'Merged' if pr_details.get('merged') else ('Closed' if state == 'closed' else 'Open')
        created_at = pr_details.get('created_at', 'N/A')
        commits_count = pr_details.get('commits_count', 'N/A')
        changed_files = pr_details.get('changed_files_count', 'N/A')
        additions = pr_details.get('additions', 'N/A')
        deletions = pr_details.get('deletions', 'N/A')
        labels = ', '.join(pr_details.get('labels', [])) or 'None'

        # Truncate long body
        max_body_len = 1500
        truncated_body = body[:max_body_len] + ('...' if len(body) > max_body_len else '')

        base_prompt = f"""
You are an AI assistant specializing in summarizing GitHub Pull Requests.
Analyze the following Pull Request details from repository '{repo_name}' and provide a summary tailored for a '{role}'.

**Pull Request #{pr_number}: {title}**
*   **Author:** {author}
*   **Status:** {state.capitalize()} ({merged_status})
*   **Created:** {created_at}
*   **Commits:** {commits_count}
*   **Changed Files:** {changed_files}
*   **Code Churn:** +{additions} / -{deletions} lines
*   **Labels:** {labels}
*   **Description/Body:**
{truncated_body}
---
"""
        role_instructions = ""
        # Define role-specific instructions
        if role == 'Developer':
            role_instructions = """
**Summary Focus (Developer):**
*   Summarize the core technical changes and their purpose.
*   Identify key files, modules, or functions affected.
*   Mention any potential technical complexities, risks, or areas needing careful code review (based *only* on the description and metadata).
*   Note any mention of tests added or modified.
*   Be concise and focus on technical aspects relevant for peer review or understanding the change.
"""
        elif role == 'Manager' or role == 'Team Lead':
             role_instructions = """
**Summary Focus (Manager/Team Lead):**
*   Explain the high-level purpose and business value (what problem does this PR solve or what feature does it add?).
*   Summarize the overall status (e.g., Ready for Review, Needs Work, Merged, Blocked?).
*   Give a sense of the PR's size/complexity (e.g., Small/Medium/Large based on file/line changes and description).
*   Highlight any mentioned risks, blockers, or dependencies on other work.
*   Include the author and key dates (created, merged/closed).
*   Focus on information needed for tracking progress and impact.
"""
        elif role == 'Program Manager' or role == 'Product Owner':
            role_instructions = """
**Summary Focus (Program/Product Manager):**
*   Describe the user-facing impact or the feature/bug fix being addressed.
*   Relate the PR to product goals or requirements if possible (based on title/body/labels).
*   Note the status (especially if merged or closed).
*   Mention associated issues or tickets if referenced in the body (though not explicitly provided here, look for patterns like '#123').
*   Focus on 'what' and 'why' from a product perspective.
"""
        else: # Default/General
            role_instructions = """
**Summary Focus (General):**
*   State the main goal or purpose of the PR clearly.
*   Identify the author and the current status (Open/Closed/Merged).
*   Provide a brief, balanced overview of the key changes made.
*   Keep the summary accessible to a wider audience.
"""

        return base_prompt + role_instructions + "\n**Summary:**" # Ask for summary explicitly


    def summarize_pull_request(self, pr_number, role):
        """Fetches PR details and generates a role-based summary using Gemini."""
        if not self.gemini_model:
            return "Gemini model not initialized. Cannot generate summary."
        if not self.owner or not self.repo:
             return "Repository owner and name not set. Analyze a repository first."
        # Use the github_analyzer instance created in __init__
        if not self.github_analyzer:
             return "GitHub Analyzer not initialized."


        print(f"\nFetching details for PR #{pr_number} in {self.repo_full_name}...")
        pr_details = self.github_analyzer.get_pull_request_details(self.owner, self.repo, pr_number)

        if not pr_details:
            return f"Could not retrieve details for PR #{pr_number}."

        print(f"Generating summary for role: {role}...")

        # Generate the role-specific prompt
        prompt = self._get_pr_summary_prompt(pr_details, role)

        # 4. Send to Gemini and Get Response
        try:
            # print("--- Sending Prompt to Gemini ---")
            # print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt) # Debug: Print truncated prompt
            # print("-----------------------------")

            response = self.gemini_model.generate_content(prompt)

            print("\n--- Gemini PR Summary ---")
            summary_text = response.text
            display(Markdown(summary_text))
            print("------------------------")
            return summary_text

        except Exception as e:
            print(f"Error communicating with Gemini for PR summary: {e}")
            return f"Error asking Gemini: {e}"


# --- Main function for running in Colab/Script ---
def run_graph_repo_analyzer():
    """Run the enhanced GitHub repository analyzer with Graph and LLM features."""
    print("Enhanced GitHub Repository Information Tool (with Neo4j & Claude)")
    print("="*70)
    print("\nThis tool fetches comprehensive information about a GitHub repository,")
    print("stores it in a Neo4j graph, and allows querying with Claude model,")
    print("including role-based Pull Request summaries.")
    print("\nEnsure you have Neo4j running and API keys configured (.env or Colab Secrets).")

    # Get user input
    owner = input("Enter the repository owner (username or organization): ")
    repo = input("Enter the repository name: ")

    # Initialize the analyzer (credentials loaded from .env or passed)
    analyzer = GraphRepoAnalyzer() # Assumes .env or Colab secrets

    if not analyzer.github_analyzer or not analyzer.github_analyzer.github:
         print("GitHub analyzer could not be initialized correctly. Check token/PyGithub.")
         return
    if not analyzer.neo4j_driver:
         print("Proceeding without Neo4j features.")
    if not analyzer.gemini_model:
         print("Proceeding without Gemini features.")

    try:
        # Analyze the repository (includes display and option to populate graph)
        analyzer.analyze_repo(owner, repo, display=True, save_json=True, export_text=False) # Ask about saving/exporting

        # --- Section for PR Summarization ---
        if analyzer.gemini_model and analyzer.repo_data:
             print("\n--- Pull Request Summarizer ---")
             while True:
                  pr_num_str = input("Enter a Pull Request number to summarize (or type 'skip'/'quit'): ")
                  if pr_num_str.lower() in ['skip', 'quit']:
                      break
                  try:
                      pr_number = int(pr_num_str)
                      if pr_number <= 0: raise ValueError("PR number must be positive.")

                      role = input("Enter your role (e.g., Developer, Manager, Product Owner, Team Lead, General): ").strip().capitalize()
                      # Basic role validation/mapping could be added here if needed
                      if not role: role = "General" # Default role

                      analyzer.summarize_pull_request(pr_number, role)

                  except ValueError:
                      print("Invalid input. Please enter a positive integer for the PR number.")
                  except Exception as e:
                       print(f"An error occurred during PR summarization: {e}")


        # --- Section for Interactive Q&A ---
        if analyzer.gemini_model and analyzer.repo_data:
            print("\n--- Interactive Q&A about the Repository ---")
            while True:
                question = input("Ask a question about the repository (or type 'quit'): ")
                if question.lower() == 'quit':
                    break
                if not question:
                    continue
                analyzer.ask_gemini_about_repo(question) # Use the existing method
        elif not analyzer.gemini_model:
             print("\nGemini interaction disabled (API key missing or initialization failed).")
        elif not analyzer.repo_data:
             print("\nCannot start Q&A as repository analysis failed.")


    finally:
        # Clean up Neo4j connection
        analyzer.close()

# --- Example Usage ---
if __name__ == "__main__":
    run_graph_repo_analyzer()