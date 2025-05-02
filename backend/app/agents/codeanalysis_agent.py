# CodeAnalysis Agent
# Analyzes code structure, dependencies, and metrics.

import os
import ast
import re
from collections import defaultdict
import radon.metrics as metrics
import radon.complexity as complexity

class CodeAnalysisAgent:
    def analyze_repo(self, repo_data, max_files=100):
        """Analyze the repository for code summaries, metrics, and dependencies."""
        # Assume repo_data contains at least: owner, repo, and a method to get all text/code files
        owner = repo_data.get('owner')
        repo = repo_data.get('repo')
        get_all_text_files = repo_data.get('get_all_text_files')
        if not (owner and repo and get_all_text_files):
            raise ValueError("repo_data must contain 'owner', 'repo', and 'get_all_text_files' callable.")

        # Get all code files (Python, JS, TS, JSX, TSX)
        text_files = get_all_text_files(owner, repo, max_files=max_files)
        code_files = [f for f in text_files if f['name'].endswith(('.py', '.js', '.ts', '.jsx', '.tsx'))]

        # Extract code summaries
        summaries = {}
        for f in code_files:
            summaries[f['path']] = self.extract_code_summary(f['content'], f['path'])

        # Analyze dependencies
        dependencies = self.analyze_dependencies_from_files(code_files, summaries)

        # Aggregate metrics
        aggregate_metrics = self.aggregate_code_metrics(summaries)

        return {
            'summaries': summaries,
            'dependencies': dependencies,
            'aggregate_metrics': aggregate_metrics
        }

    def analyze_code(self, repo_data):
        """Analyze code files in the repository."""
        try:
            code_files = repo_data.get('code_files', [])
            if not code_files:
                return {
                    'error': 'No code files found in repository data',
                    'summaries': {},
                    'dependencies': {},
                    'metrics': {}
                }

            # Analyze each code file
            file_summaries = {}
            for file_info in code_files:
                if not isinstance(file_info, dict) or 'content' not in file_info:
                    continue
                file_path = file_info.get('path', '')
                content = file_info['content']
                summary = self.extract_code_summary(content, file_path)
                if summary:
                    file_summaries[file_path] = summary

            # Analyze dependencies between files
            dependencies = self.analyze_dependencies_from_files(
                [f for f in code_files if isinstance(f, dict)],
                file_summaries
            )

            # Aggregate metrics
            metrics = self.aggregate_code_metrics(file_summaries)

            return {
                'summaries': file_summaries,
                'dependencies': dependencies,
                'metrics': metrics
            }

        except Exception as e:
            return {
                'error': f'Error analyzing code: {str(e)}',
                'summaries': {},
                'dependencies': {},
                'metrics': {}
            }

    def analyze_ast(self, code, file_path):
        """Analyze Python code using AST."""
        try:
            tree = ast.parse(code)
            result = {
                'functions': [],
                'classes': [],
                'imports': [],
                'metrics': {
                    'loc': len(code.splitlines()),
                    'lloc': metrics.sloc(code),
                    'complexity': complexity.cc_visit(code)
                }
            }

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        result['imports'].append({
                            'name': name.name,
                            'alias': name.asname
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for name in node.names:
                        result['imports'].append({
                            'name': f'{module}.{name.name}',
                            'alias': name.asname
                        })

            # Extract functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'args': [],
                        'decorators': [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                        'docstring': ast.get_docstring(node),
                        'start_line': node.lineno,
                        'end_line': node.end_lineno
                    }
                    
                    # Get arguments
                    for arg in node.args.args:
                        func_info['args'].append({
                            'name': arg.arg,
                            'annotation': arg.annotation.id if arg.annotation and hasattr(arg.annotation, 'id') else None
                        })
                    
                    result['functions'].append(func_info)

            # Extract classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        'name': node.name,
                        'bases': [base.id for base in node.bases if isinstance(base, ast.Name)],
                        'decorators': [d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                        'docstring': ast.get_docstring(node),
                        'methods': [],
                        'start_line': node.lineno,
                        'end_line': node.end_lineno
                    }
                    
                    # Get methods
                    for child in ast.iter_child_nodes(node):
                        if isinstance(child, ast.FunctionDef):
                            method_info = {
                                'name': child.name,
                                'args': [],
                                'decorators': [d.id for d in child.decorator_list if isinstance(d, ast.Name)],
                                'docstring': ast.get_docstring(child),
                                'start_line': child.lineno,
                                'end_line': child.end_lineno
                            }
                            
                            # Get arguments
                            for arg in child.args.args:
                                method_info['args'].append({
                                    'name': arg.arg,
                                    'annotation': arg.annotation.id if arg.annotation and hasattr(arg.annotation, 'id') else None
                                })
                            
                            class_info['methods'].append(method_info)
                    
                    result['classes'].append(class_info)

            return result

        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None

    def extract_code_summary(self, file_content, file_path):
        """Extract code summary based on file type."""
        if file_path.endswith('.py'):
            return self.analyze_ast(file_content, file_path)
        elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
            return self.analyze_js_ts(file_content, file_path)
        else:
            return {
                'functions': [],
                'classes': [],
                'imports': [],
                'description': 'Unsupported file type',
                'complexity': None,
                'metrics': {}
            }

    def analyze_dependencies_from_files(self, code_files, summaries):
        """Analyze dependencies between files."""
        dependencies = {
            'internal': defaultdict(set),
            'external': defaultdict(set),
            'metrics': {
                'total_imports': 0,
                'internal_imports': 0,
                'external_imports': 0
            }
        }

        for file_path, summary in summaries.items():
            if not summary:
                continue

            imports = summary.get('imports', [])
            for imp in imports:
                dependencies['metrics']['total_imports'] += 1
                if isinstance(imp, dict):
                    module_name = imp.get('name', '')
                else:
                    module_name = imp

                # Check if the import is internal (exists in our codebase)
                is_internal = False
                for other_file in code_files:
                    if other_file != file_path:
                        if module_name in other_file or module_name.replace('.', '/') in other_file:
                            dependencies['internal'][file_path].add(other_file)
                            dependencies['metrics']['internal_imports'] += 1
                            is_internal = True
                            break

                if not is_internal:
                    dependencies['external'][file_path].add(module_name)
                    dependencies['metrics']['external_imports'] += 1

        return dependencies
        # Return the analyzed dependencies
        return dependencies

    def aggregate_code_metrics(self, summaries):
        """Aggregate code metrics across all summaries."""
        total_lines = code_lines = comment_lines = blank_lines = 0
        for summary in summaries.values():
            metrics = summary.get('metrics', {})
            total_lines += metrics.get('total_lines', 0)
            code_lines += metrics.get('code_lines', 0)
            comment_lines += metrics.get('comment_lines', 0)
            blank_lines += metrics.get('blank_lines', 0)
        comment_ratio = comment_lines / max(1, code_lines + comment_lines)
        return {
            'total_lines': total_lines,
            'code_lines': code_lines,
            'comment_lines': comment_lines,
            'blank_lines': blank_lines,
            'comment_ratio': comment_ratio
        }

    def run_graph_repo_analyzer(self, github_agent, text_agent=None, llm_agent=None):
        """
        Run a CLI-based enhanced GitHub repository analyzer using agent structure.
        github_agent: instance of GitHubDataFetcherAgent
        text_agent: instance of TextAnalysisAgent (optional)
        llm_agent: instance of LLMAgent (optional, for Q&A and PR summarization)
        """
        print("Enhanced GitHub Repository Information Tool (Agent Version)")
        print("="*70)
        print("\nThis tool fetches comprehensive information about a GitHub repository,")
        print("and analyzes code, text, and optionally supports Q&A with an LLM.")
        print("\nEnsure you have all API keys configured (.env or environment variables).\n")

        owner = input("Enter the repository owner (username or organization): ")
        repo = input("Enter the repository name: ")

        repo_data = github_agent.fetch_repo_data(owner, repo)
        print("\nRepository data fetched. Running code analysis...")
        code_analysis = self.analyze_code(repo_data)
        print("Code analysis complete.")

        if text_agent:
            print("Running text/documentation analysis...")
            text_analysis = text_agent.analyze_text(repo_data)
            print("Text analysis complete.")
        else:
            text_analysis = {}

        print("\n--- Code Metrics ---")
        for k, v in code_analysis.items():
            print(f"{k}: {v}")

        if text_analysis:
            print("\n--- Documentation/Issues ---")
            print(f"README: {text_analysis.get('readme', '')[:200]}{'...' if len(text_analysis.get('readme', ''))>200 else ''}")
            print(f"Open Issues: {len(text_analysis.get('issues', []))}")

        if llm_agent:
            print("\n--- LLM Summary ---")
            summary = llm_agent.generate_summary(repo_data, code_analysis, text_analysis)
            print(summary)

            # Interactive Q&A
            while True:
                question = input("\nAsk a question about the repository (or type 'quit'): ")
                if question.lower() == 'quit':
                    break
                if not question:
                    continue
                # You could implement a method like llm_agent.ask_question if desired
                print("(LLM Q&A not implemented: add ask_question method to LLMAgent)")

            # PR Summarization (if PR data and LLM support exist)
            if 'open_pull_requests' in repo_data:
                while True:
                    pr_num_str = input("\nEnter a Pull Request number to summarize (or type 'skip'/'quit'): ")
                    if pr_num_str.lower() in ['skip', 'quit']:
                        break
                    try:
                        pr_number = int(pr_num_str)
                        if pr_number <= 0:
                            raise ValueError("PR number must be positive.")
                        print("(PR summarization not implemented: add summarize_pull_request method to LLMAgent)")
                    except ValueError:
                        print("Invalid input. Please enter a positive integer for the PR number.")
        print("\nAnalysis complete. Exiting.")
