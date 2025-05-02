"""
Reporting Agent (RA)
- Formats and presents the analyzed data to the user.
- Generates visualizations (plots, tables).
- Handles exporting data to files (JSON, Markdown).
"""
import json
import matplotlib.pyplot as plt

class ReportingAgent:
    def display_repo_info(self, repo_data):
        print("\nRepository Info:")
        for k, v in repo_data.get('basic_info', {}).items():
            print(f"{k}: {v}")

    def display_code_files(self, code_analysis):
        print("\nCode Files:")
        for path, summary in code_analysis.get('summaries', {}).items():
            print(f"{path}: {summary.get('description', '')}")

    def export_repo_text(self, repo_data, filename="repo_text_export.md"):
        readme = repo_data.get('text_content', {}).get('readme', '')
        with open(filename, 'w') as f:
            f.write(readme)
        print(f"Exported README to {filename}")

    def save_json_to_file(self, data, filename="repo_data.json"):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Exported data to {filename}")

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
