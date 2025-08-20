#!/usr/bin/env python3

import markdown
import webbrowser
import os

def render_markdown_to_html(markdown_file, output_html_file):
    """
    Reads a Markdown file, converts it to HTML, and saves it to an HTML file.
    """
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

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

        with open(output_html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"Successfully rendered '{markdown_file}' to '{output_html_file}'")
        return True
    except Exception as e:
        print(f"Error rendering Markdown to HTML: {e}")
        return False

if __name__ == "__main__":
    report_markdown_file = "reports/report.md"
    report_html_file = "reports/report.html"

    # Ensure the reports directory exists
    output_dir = os.path.dirname(report_html_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if os.path.exists(report_markdown_file):
        if render_markdown_to_html(report_markdown_file, report_html_file):
            webbrowser.open_new_tab(os.path.abspath(report_html_file))
    else:
        print(f"Error: Markdown report file not found at '{report_markdown_file}'. Please run 'task report' first.")
