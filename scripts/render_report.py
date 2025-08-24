#!/usr/bin/env python3
################################################################################
#
# Script Name: render_report.py
# ----------------
# Renders a Markdown report to an HTML file and opens it in a web browser.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import markdown
import webbrowser
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from fantasy_ai.errors import FileOperationError

def render_markdown_to_html(markdown_file, output_html_file):
    """
    Reads a Markdown file, converts it to HTML, and saves it to an HTML file.
    """
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except IOError as e:
        raise FileOperationError(f"Could not read Markdown file '{markdown_file}': {e}") from e

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fantasy Football Analysis Report</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; line-height: 1.6; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        pre {{ background-color: #eee; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        code {{ font-family: monospace; }}
    </style>
</head>
<body>
{markdown.markdown(markdown_content)}
</body>
</html>"""

    try:
        with open(output_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    except IOError as e:
        raise FileOperationError(f"Could not write HTML file '{output_html_file}': {e}") from e

    print(f"Successfully rendered '{markdown_file}' to '{output_html_file}'")
    return True

def main():
    report_markdown_file = "reports/report.md"
    report_html_file = "reports/report.html"

    # Ensure the reports directory exists
    output_dir = os.path.dirname(report_html_file)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            raise FileOperationError(f"Could not create directory '{output_dir}': {e}") from e

    if os.path.exists(report_markdown_file):
        try:
            if render_markdown_to_html(report_markdown_file, report_html_file):
                webbrowser.open_new_tab(os.path.abspath(report_html_file))
        except FileOperationError as e:
            print(f"Error during report rendering: {e}")
    else:
        print(f"Error: Markdown report file not found at '{report_markdown_file}'. Please run 'task report' first.")

if __name__ == "__main__":
    main()