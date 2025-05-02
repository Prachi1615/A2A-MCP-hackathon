# Coordinator Agent
# Responsible for orchestrating the workflow between all agents.

from backend.app.agents.reporting_agent import ReportingAgent
from backend.app.agents.github_datafetcher_agent import GitHubDataFetcherAgent
from backend.app.agents.codeanalysis_agent import CodeAnalysisAgent
from backend.app.agents.textanalysis_agent import TextAnalysisAgent
from backend.app.agents.llm_agent import LLMAgent

class CoordinatorAgent:
    def __init__(self, github_agent, code_agent, text_agent, llm_agent, reporting_agent=None):
        self.github_agent = github_agent
        self.code_agent = code_agent
        self.text_agent = text_agent
        self.llm_agent = llm_agent
        self.reporting_agent = reporting_agent or ReportingAgent()
        self.repo_data = None
        self.code_analysis = None
        self.text_analysis = None
        self.llm_summary = None

    def run_pipeline(self):
        print("\n=== GitHub Repo Analyzer ===")
        owner = input("Enter repository owner (username/org): ")
        repo = input("Enter repository name (e.g., 'smart-cities', not the full URL): ")
        
        # Clean up repo name if full URL was provided
        if 'github.com' in repo:
            parts = repo.split('/')
            repo = parts[-1]  # Get the last part of the URL/path

        print(f"\nAnalyzing repository: {owner}/{repo}")
        print("Fetching repository data...")
        
        try:
            self.repo_data = self.github_agent.fetch_repo_data(owner, repo)
            if not self.repo_data:
                print("\nError: Could not fetch repository data. Please check:"
                      "\n1. Repository name and owner are correct"
                      "\n2. Repository is public or token has access"
                      "\n3. GitHub token is valid")
                return
                
            print("Repository data fetched successfully.")
            
            self.code_analysis = self.code_agent.analyze_repo(self.repo_data)
            print("Code analysis complete.")
            
            self.text_analysis = self.text_agent.analyze_text(self.repo_data)
            print("Text analysis complete.")
            
        except Exception as e:
            print(f"\nError during analysis: {str(e)}")
            return
        self.llm_summary = self.llm_agent.generate_summary(self.repo_data, self.code_analysis, self.text_analysis)
        print("\n--- LLM Summary ---\n", self.llm_summary)
        # Reporting options
        while True:
            print("\nOptions: [1] Show Repo Info  [2] Show Code Files  [3] Export README  [4] Export JSON  [5] Plot Languages  [q] Quit")
            opt = input("Choose an option: ").strip().lower()
            if opt == '1':
                self.reporting_agent.display_repo_info(self.repo_data)
            elif opt == '2':
                self.reporting_agent.display_code_files(self.code_analysis)
            elif opt == '3':
                self.reporting_agent.export_repo_text(self.repo_data)
            elif opt == '4':
                self.reporting_agent.save_json_to_file(self.repo_data)
            elif opt == '5':
                self.reporting_agent.plot_language_distribution(self.repo_data)
            elif opt == 'q':
                print("Exiting analyzer.")
                break
            else:
                print("Invalid option.")

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    github_token = os.getenv('YOUR_GITHUB_TOKEN')
    gemini_key = os.getenv('YOUR_GEMINI_API_KEY')

    if not github_token:
        print("Error: GitHub token not found in environment variables")
        exit(1)
    if not gemini_key:
        print("Error: Gemini API key not found in environment variables")
        exit(1)

    github_agent = GitHubDataFetcherAgent(token=github_token)
    text_agent = TextAnalysisAgent()
    code_agent = CodeAnalysisAgent()
    llm_agent = LLMAgent(api_key=gemini_key)
    coordinator = CoordinatorAgent(github_agent, code_agent, text_agent, llm_agent)
    coordinator.run_pipeline()