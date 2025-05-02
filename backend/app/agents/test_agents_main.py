"""
Main test script for agent methods and LLM repo summaries.
This script will:
- Instantiate all agents
- Fetch repo data from GitHub
- Run code and text analysis
- Test _get_repo_summary_for_llm for all agents
- Print outputs to verify all functions are callable and working
"""
import os
from backend.app.agents.github_datafetcher_agent import GitHubDataFetcherAgent
from backend.app.agents.textanalysis_agent import TextAnalysisAgent
from backend.app.agents.codeanalysis_agent import CodeAnalysisAgent
from backend.app.agents.llm_agent import LLMAgent

def main():
    # Set these or use environment variables
    GITHUB_TOKEN = os.getenv("YOUR_GITHUB_TOKEN")
    GEMINI_API_KEY = os.getenv("YOUR_GEMINI_API_KEY")
    TEST_OWNER = "huggingface"
    TEST_REPO = "transformers"

    # Instantiate agents
    github_agent = GitHubDataFetcherAgent(token=GITHUB_TOKEN)
    text_agent = TextAnalysisAgent()
    code_agent = CodeAnalysisAgent()
    llm_agent = LLMAgent(api_key=GEMINI_API_KEY)

    # Fetch repo data
    print("\nFetching repo data...")
    repo_data = github_agent.fetch_repo_data(TEST_OWNER, TEST_REPO)
    print("Repo data fetched. Keys:", list(repo_data.keys()))

    # Test GitHubDataFetcherAgent _get_repo_summary_for_llm
    print("\n--- GitHubDataFetcherAgent _get_repo_summary_for_llm ---")
    print(github_agent._get_repo_summary_for_llm(repo_data))

    # Test TextAnalysisAgent
    print("\n--- TextAnalysisAgent.analyze_text ---")
    text_analysis = text_agent.analyze_text(repo_data)
    print(text_analysis)
    print("\n--- TextAnalysisAgent _get_repo_summary_for_llm ---")
    print(text_agent._get_repo_summary_for_llm(repo_data))

    # Test CodeAnalysisAgent (analyze_code and analyze_repo)
    print("\n--- CodeAnalysisAgent.analyze_code ---")
    print(code_agent.analyze_code(repo_data))
    print("\n--- CodeAnalysisAgent.analyze_repo (stub, may need mock get_all_text_files) ---")
    try:
        # This will fail unless repo_data['get_all_text_files'] is set up properly
        result = code_agent.analyze_repo(repo_data)
        print(result)
    except Exception as e:
        print(f"analyze_repo failed (expected if no get_all_text_files): {e}")

    # Test LLMAgent _get_repo_summary_for_llm
    print("\n--- LLMAgent _get_repo_summary_for_llm ---")
    print(llm_agent._get_repo_summary_for_llm(repo_data, code_agent.analyze_code(repo_data), text_analysis))
    # Optionally test generate_summary (calls LLM, may use up quota)
    # print("\n--- LLMAgent.generate_summary ---")
    # print(llm_agent.generate_summary(repo_data, code_agent.analyze_code(repo_data), text_analysis))

if __name__ == "__main__":
    main()
