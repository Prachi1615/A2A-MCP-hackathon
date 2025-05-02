"""
Main test script for agent methods and LLM repo summaries.
This script will:
- Instantiate all agents
- Fetch repo data from GitHub
- Run code and text analysis
- Test LLM methods including PR summaries
- Print outputs to verify all functions are callable and working
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.insert(0, project_root)

from backend.app.agents.github_datafetcher_agent import GitHubDataFetcherAgent
from backend.app.agents.textanalysis_agent import TextAnalysisAgent
from backend.app.agents.codeanalysis_agent import CodeAnalysisAgent
from backend.app.agents.llm_agent import LLMAgent
from backend.app.agents.reporting_agent import ReportingAgent

def run_reporting_tests(reporting_agent, repo_data, code_analysis):
    """Run tests for ReportingAgent"""
    print("\n--- Testing ReportingAgent Methods ---")
    
    # Test display_repo_info
    print("\nTesting display_repo_info...")
    reporting_agent.display_repo_info(repo_data)
    
    # Test display_code_files
    print("\nTesting display_code_files...")
    reporting_agent.display_code_files(code_analysis)
    
    # Test export_repo_text
    print("\nTesting export_repo_text...")
    reporting_agent.export_repo_text(repo_data, "test_repo_text.md")
    
    # Test save_json_to_colab
    print("\nTesting save_json_to_colab...")
    test_data = {
        'set_data': {1, 2, 3},
        'list_data': [4, 5, 6],
        'dict_data': {'key': {7, 8, 9}}
    }
    reporting_agent.save_json_to_colab(test_data, "test_data.json")

def run_code_analysis_tests(code_agent, repo_data):
    """Run tests for CodeAnalysisAgent"""
    print("\n--- Testing CodeAnalysisAgent Methods ---")
    
    code_analysis = {
        'summaries': {},
        'dependencies': {},
        'metrics': {}
    }
    
    try:
        # Test analyze_code
        print("\nTesting analyze_code...")
        code_analysis = code_agent.analyze_code(repo_data)
        print(f"Code analysis completed. Keys: {list(code_analysis.keys())}")
        
        # Test extract_code_summary with a sample Python file
        print("\nTesting extract_code_summary...")
        sample_code = "def hello():\n    print('Hello')\n"
        summary = code_agent.extract_code_summary(sample_code, "test.py")
        print(f"Code summary generated. Keys: {list(summary.keys() if summary else [])}")
        
        # Test analyze_ast
        print("\nTesting analyze_ast...")
        ast_analysis = code_agent.analyze_ast(sample_code, "test.py")
        print(f"AST analysis completed. Keys: {list(ast_analysis.keys() if ast_analysis else [])}")
    except Exception as e:
        print(f"Warning: Some code analysis tests failed - {e}")
    
    return code_analysis

def run_llm_tests(llm_agent, owner, repo):
    """Run tests for LLMAgent"""
    print("\n--- Testing PR Summarization ---")
    test_pr_number = 1  # Use first PR for testing
    roles = ["Developer", "Manager", "Product Owner"]
    
    try:
        for role in roles:
            print(f"\nGenerating {role} summary for PR #{test_pr_number}...")
            summary = llm_agent.summarize_pull_request(test_pr_number, role)
            print(f"Summary generated: {len(summary) if summary else 0} characters")
    except Exception as e:
        print(f"PR summarization failed: {e}")

def main():
    # Load environment variables
    load_dotenv()
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "") or os.getenv("YOUR_GITHUB_TOKEN", "")
    GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "") or os.getenv("YOUR_GEMINI_API_KEY", "")
    TEST_OWNER = "huggingface"
    TEST_REPO = "transformers"
    
    print(f"\nTesting with repository: {TEST_OWNER}/{TEST_REPO}")

    # Instantiate agents with dummy tokens for testing
    github_agent = GitHubDataFetcherAgent(token=GITHUB_TOKEN)
    text_agent = TextAnalysisAgent(token=GITHUB_TOKEN)
    code_agent = CodeAnalysisAgent()
    llm_agent = LLMAgent(gemini_api_key=GEMINI_API_KEY, github_token=GITHUB_TOKEN)
    reporting_agent = ReportingAgent()

    # Fetch repo data
    print("\nFetching repo data...")
    repo_data = github_agent.get_repo_info(TEST_OWNER, TEST_REPO)  # Updated method name
    print("Repo data fetched. Keys:", list(repo_data.keys()))

    # Test TextAnalysisAgent
    print("\n--- TextAnalysisAgent.analyze_text ---")
    text_analysis = text_agent.analyze_text(repo_data)
    print(text_analysis)

    # Initialize test data
    test_code_files = [
        {
            'path': 'test.py',
            'content': 'def test():\n    return True\n'
        }
    ]
    
    # Run tests for each agent
    print("\n=== Starting Agent Tests ===")
    
    try:
        # Test CodeAnalysisAgent
        print("\n=== CodeAnalysisAgent Tests ===")
        code_analysis = run_code_analysis_tests(code_agent, {'code_files': test_code_files})
        
        # Test ReportingAgent
        print("\n=== ReportingAgent Tests ===")
        run_reporting_tests(reporting_agent, repo_data, code_analysis)
        
        # Test LLMAgent
        print("\n=== LLMAgent Tests ===")
        run_llm_tests(llm_agent, TEST_OWNER, TEST_REPO)
        
        # Test LLM summary generation
        if hasattr(llm_agent, 'model'):
            try:
                print("\n=== Testing LLM Summary Generation ===")
                summary = llm_agent.generate_summary(repo_data, code_analysis, text_analysis)
                if summary:
                    print(f"Generated summary length: {len(summary)} characters")
                    print("\nGenerated Summary:")
                    print(summary)
            except Exception as e:
                print(f"Warning: LLM summary generation failed - {e}")
        else:
            print("\nSkipping LLM summary generation - Gemini model not initialized")
        
        print("\n=== Tests completed ===\n")
        print("Note: Some warnings/errors are expected in test environment due to missing API keys")
    except Exception as e:
        print(f"\nError during tests: {e}")

if __name__ == "__main__":
    main()
