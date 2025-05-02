"""
Reporting Agent (RA)
- Formats and presents the analyzed data to the user.
- Generates visualizations (plots, tables).
- Handles exporting data to files (JSON, Markdown).
"""
import json
import matplotlib.pyplot as plt
from pathlib import Path

class ReportingAgent:
    def __init__(self):
        self.output_dir = Path('output')
        self.output_dir.mkdir(exist_ok=True)

    def convert_sets_to_lists(self, obj):
        """Convert any sets in the object to lists for JSON serialization."""
        if isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self.convert_sets_to_lists(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_sets_to_lists(item) for item in obj]
        return obj

    def display_repo_info(self, repo_data):
        """Display basic repository information."""
        print("\nRepository Info:")
        basic_info = repo_data.get('basic_info', {})
        for k, v in basic_info.items():
            if isinstance(v, dict) and 'login' in v:
                print(f"{k}: {v['login']}")
            else:
                print(f"{k}: {v}")

    def display_code_files(self, code_analysis):
        """Display analyzed code files and their summaries."""
        print("\nCode Files Analysis:")
        summaries = code_analysis.get('summaries', {})
        for path, summary in summaries.items():
            print(f"\nFile: {path}")
            if 'functions' in summary:
                print(f"Functions: {len(summary['functions'])}")
            if 'classes' in summary:
                print(f"Classes: {len(summary['classes'])}")
            if 'metrics' in summary:
                print("Metrics:", summary['metrics'])

    def export_repo_text(self, repo_data, filename="repo_text_export.md"):
        """Export repository text content to a markdown file."""
        output_path = self.output_dir / filename
        content = [
            "# Repository Text Content\n",
            "## README\n",
            repo_data.get('text_content', {}).get('readme', 'No README found'),
            "\n## Documentation\n",
            *[f"### {doc['path']}\n{doc['content']}\n" 
              for doc in repo_data.get('text_content', {}).get('documentation', [])]
        ]
        
        with open(output_path, 'w') as f:
            f.writelines(content)
        print(f"Exported text content to {output_path}")

    def save_json_to_colab(self, data, filename="repo_data.json"):
        """Save data as JSON, converting sets to lists for serialization."""
        output_path = self.output_dir / filename
        serializable_data = self.convert_sets_to_lists(data)
        
        with open(output_path, 'w') as f:
            json.dump(serializable_data, f, indent=2, default=str)
        print(f"Exported JSON data to {output_path}")

    def plot_language_distribution(self, repo_data):
        languages = repo_data.get('languages', {})
        if not languages:
            print("No language data to plot.")
            return
        labels = list(languages.keys())
        sizes = list(languages.values())
        plt.figure(figsize=(8, 5))
        plt.pie(sizes, labels=labels, autopct='%1.1f%%')
        plt.title('Language Distribution')
        plt.show()
