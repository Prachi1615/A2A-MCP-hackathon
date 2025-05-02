# LLM Agent (Rime/Gemini)
# Uses an LLM to generate summaries or insights.

import os
from dotenv import load_dotenv
import google.generativeai as genai
from backend.app.agents.github_datafetcher_agent import GitHubDataFetcherAgent

class LLMAgent:
    def __init__(self, gemini_api_key=None, github_token=None, neo4j_uri=None, neo4j_user=None, neo4j_password=None):
        """Initialize with credentials."""
        load_dotenv()
        
        # LLM settings
        self.gemini_api_key = gemini_api_key or os.getenv("GOOGLE_API_KEY", "")
        if self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                print("Gemini model initialized.")
            except Exception as e:
                print(f"Error initializing Gemini: {e}")
                self.model = None
        else:
            print("Warning: Google API Key not provided. Gemini features will be disabled.")
            self.model = None
        
        # GitHub settings
        self.github_token = github_token or os.getenv("GITHUB_TOKEN", "")
        self.github_analyzer = GitHubDataFetcherAgent(token=self.github_token) if self.github_token else None
        self.owner = None
        self.repo = None
        self.repo_full_name = None
        
        # Neo4j settings (optional)
        self.neo4j_uri = neo4j_uri or os.getenv("NEO4J_URI", "")
        self.neo4j_user = neo4j_user or os.getenv("NEO4J_USERNAME", "")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD", "")
        self.neo4j_driver = None
        
        if all([self.neo4j_uri, self.neo4j_user, self.neo4j_password]):
            try:
                from neo4j import GraphDatabase, basic_auth
                self.neo4j_driver = GraphDatabase.driver(self.neo4j_uri, auth=basic_auth(self.neo4j_user, self.neo4j_password))
                self.neo4j_driver.verify_connectivity()
                print("Successfully connected to Neo4j.")
            except Exception as e:
                print(f"Error connecting to Neo4j: {e}")
                print("Graph features will be disabled.")
                self.neo4j_driver = None
        else:
            print("Warning: Neo4j credentials not fully provided. Graph features will be disabled.")

    def generate_summary(self, repo_data, code_analysis, text_analysis):
        """Generates a summary using the LLM based on all analyses."""
        if not self.model:
            return "Gemini model not initialized. Cannot generate summary."
        
        # Create a prompt from the available data
        prompt = "Please provide a summary of this repository based on the following information:\n\n"
        
        # Add repository info
        if repo_data:
            prompt += "\nRepository Information:\n"
            for key, value in repo_data.items():
                if key in ['name', 'full_name', 'description', 'url']:
                    prompt += f"- {key}: {value}\n"
        
        # Add code analysis info
        if code_analysis:
            prompt += "\nCode Analysis:\n"
            if 'summaries' in code_analysis:
                prompt += "- Code Summaries:\n"
                for file, summary in code_analysis['summaries'].items():
                    prompt += f"  - {file}: {summary}\n"
            if 'metrics' in code_analysis:
                prompt += "- Code Metrics:\n"
                for metric, value in code_analysis['metrics'].items():
                    prompt += f"  - {metric}: {value}\n"
        
        # Add text analysis info
        if text_analysis:
            prompt += "\nText Analysis:\n"
            if 'readme' in text_analysis:
                prompt += f"- README: {text_analysis['readme'][:500]}...\n"
            if 'documentation' in text_analysis:
                prompt += f"- Documentation Files: {len(text_analysis['documentation'])}\n"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating summary: {e}"

    def summarize_pull_request(self, pr_number, role):
        """Fetches PR details and generates a role-based summary using Gemini."""
        if not self.model:
            return "Model not initialized. Cannot generate summary."
        if not self.owner or not self.repo:
            return "Repository owner and name not set. Analyze a repository first."
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
