import pandas as pd
from tabulate import tabulate
import os

def generate_draft_report():
    """
    Generates a draft report for the 2025 season.
    """
    # Define file paths
    data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'player_adp.csv')
    report_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'reports', 'draft_report_2025.md')

    # Load data
    try:
        df = pd.read_csv(data_file)
    except FileNotFoundError:
        print(f"Error: {data_file} not found. Please run scripts/download_adp.py first.")
        return

    # --- Generate Report ---
    report_content = "# 2025 Fantasy Football Draft Report\n\n"

    # Top 20 Overall
    report_content += "## Top 20 Players Overall\n\n"
    top_20_overall = df.sort_values(by='adp').head(20)
    report_content += tabulate(top_20_overall[['full_name', 'position', 'adp']], headers='keys', tablefmt='pipe', showindex=False)
    report_content += "\n\n"

    # Top 20 by Position
    positions = ['QB', 'RB', 'WR', 'TE']
    for pos in positions:
        report_content += f"## Top 20 {pos}\n\n"
        top_20_pos = df[df['position'] == pos].sort_values(by='adp').head(20)
        report_content += tabulate(top_20_pos[['full_name', 'adp']], headers='keys', tablefmt='pipe', showindex=False)
        report_content += "\n\n"

    # Save the report
    with open(report_file, 'w') as f:
        f.write(report_content)

    print(f"Draft report generated at {report_file}")

if __name__ == '__main__':
    generate_draft_report()
