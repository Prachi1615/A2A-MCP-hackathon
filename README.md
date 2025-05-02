
# GENIE: GitHub Repository Analyzer

A comprehensive tool for analyzing GitHub repositories using a multi-agent architecture, graph database storage, and LLM integration.

## Overview

GENIE is a powerful tool designed to help developers, managers, and researchers gain deeper insights into GitHub repositories. The system uses a modular multi-agent architecture that fetches, analyzes, visualizes, and stores repository data, while also providing natural language interaction capabilities through LLM integration.

## Features

- **Comprehensive Repository Analysis**: Code metrics, contributor analytics, temporal statistics
- **Graph Database Integration**: Store repository structure in Neo4j for complex querying
- **LLM-Powered Insights**: Ask questions about repositories in natural language
- **Role-Based PR Summaries**: Generate summaries tailored to different roles (Developer, Manager, etc.)
- **Interactive Visualizations**: Charts and metrics for repository understanding
- **Code Structure Analysis**: Extract functions, classes, dependencies from code files
- **Export Capabilities**: JSON, Markdown outputs of analysis results

## Architecture

The system is built on a modular multi-agent architecture where each agent specializes in specific tasks:

### Coordinator Agent (CA)
- Manages the overall workflow
- Handles user interaction (getting repo details, questions, PR numbers, export options)
- Initializes and coordinates other specialized agents
- Maintains the overall state or context

### GitHub DataFetcher Agent (GDF)
- Responsible for all interactions with the GitHub API
- Fetches repository metadata, contents, commits, issues, PRs, etc.
- Handles API rate limiting and pagination

### CodeAnalysis Agent (CAA)
- Analyzes retrieved code content
- Performs AST analysis (Python), regex analysis (JS/TS)
- Calculates code metrics (lines of code, comments)
- Identifies functions, classes, imports, and dependencies

### TextAnalysis Agent (TAA)
- Analyzes non-code text files (README, docs)
- Processes textual data like issue/PR timelines and descriptions
- Calculates aggregate text/repo metrics

### LLM Agent (LLMA)
- Interacts with language models (Gemini)
- Generates summaries (e.g., role-based PR summaries)
- Answers questions based on provided context
- Formats data/prompts for the LLM

### Graph Population Agent (GPA)
- Manages Neo4j database connection
- Creates and maintains graph schema
- Populates the graph with repository data
- Retrieves data for LLM context enhancement

### Reporting Agent (RA)
- Formats and presents analyzed data to the user
- Generates visualizations (plots, tables)
- Handles exporting data to files (JSON, Markdown)

## Installation

### Prerequisites

- Python 3.8+
- Neo4j (optional, for graph features)
- GitHub API token (for higher rate limits)
- Google API key (for Gemini LLM features)

### Setup

```bash
git clone https://github.com/yourusername/github-repo-analyzer.git
cd github-repo-analyzer
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GITHUB_TOKEN=your_github_token
NEO4J_URI=neo4j://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
GOOGLE_API_KEY=your_gemini_api_key
```

## Usage

### Basic Usage

```python
from repository_analyzer import CoordinatorAgent

coordinator = CoordinatorAgent()
coordinator.analyze_repository("owner", "repo")
response = coordinator.ask_question("What are the most complex files in this repository?")
summary = coordinator.summarize_pr(123, role="Developer")
```

### Command Line Interface

```bash
python run_analyzer.py
```

This will start an interactive prompt allowing you to:
- Enter repository details
- View analysis results
- Ask questions about the repository
- Generate PR summaries
- Export data as needed

## Example Outputs

### Repository Analysis Dashboard

Repository: user/repo  
Stars: 1250, Forks: 345, Open Issues: 67  
Contributors: 23  
Languages: Python (65%), JavaScript (20%), TypeScript (10%), Other (5%)  

### PR Summary (Developer Role)

**PR #123: "Add multi-threaded data processing"**

This PR implements a multi-threaded approach to data processing which significantly improves performance for large datasets. The core changes are in the `data_processor.py` module, specifically refactoring the `process_batch()` function to use a thread pool.

Key technical aspects:
- Adds ThreadPoolExecutor with configurable thread count
- Implements thread-safe result aggregation
- Includes unit tests to verify correctness with concurrent execution
- Adds error handling for thread exceptions

Potential review points: Thread synchronization in the `_aggregate_results()` helper method may need careful review to ensure thread safety.

### LLM Q&A Example

**Q: What are the most complex files in this repository?**

**A:** Based on the repository analysis, the most complex files by cyclomatic complexity are:
1. `data_processor.py` (Complexity: 28) - Contains core data transformation logic
2. `auth_manager.py` (Complexity: 22) - Handles authentication workflows
3. `api_client.py` (Complexity: 19) - Manages external API interactions

These files might benefit from refactoring to reduce complexity and improve maintainability.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

```bash
# Fork the repository
# Create your feature branch
git checkout -b feature/amazing-feature

# Commit your changes
git commit -m 'Add some amazing feature'

# Push to the branch
git push origin feature/amazing-feature

# Open a Pull Request
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- PyGithub - GitHub API client  
- Google Gemini - LLM capabilities  
- Matplotlib - Visualization library
