# GitHub Repository Analysis Workflow

This project uses Temporal.io to create a workflow that analyzes GitHub repositories and provides detailed information about them.

## Features

- Fetch repository details (stars, forks, issues, etc.)
- List top contributors with contribution counts
- Show recent commits with author information

## Setup

1. Make sure you have Python 3.7+ installed
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Start the Temporal server (if not already running):
   ```
   temporal server start-dev
   ```

## Running the Workflow

### Start the Worker

First, start the worker to process workflow tasks:

```bash
python run_worker.py
```

### Execute the Workflow

To analyze a GitHub repository, run:

```bash
python run_workflow.py <owner> <repo>
```

Example:

```bash
python run_workflow.py temporalio sdk-python
```

## Input Format

The workflow accepts the following input:

```
"Describe the repo including its details, contributors, any existing prs"
```

This input is processed by providing the owner and repository name as command-line arguments to the `run_workflow.py` script.

## Output

The workflow will output:

1. Basic repository information (description, stars, forks, issues)
2. Top contributors with contribution counts
3. Recent commits with author information

## Implementation Details

- Uses GitHub's REST API v3
- Handles API rate limiting and pagination
- Implements asynchronous activities with Temporal.io
