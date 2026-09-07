---
name: fantasy-blog-generator
description: Generates a MkDocs Material blog post summarizing the weekly fantasy football performance, waivers, and draft strategies.
---

# Fantasy Blog Generator

This skill automates the creation of a MkDocs Material blog post documenting the weekly analysis or draft strategy.

## Instructions
When invoked to generate a blog post:
1. **Data Collection**: Ensure the latest reports have been generated (e.g., by checking `task report` output or the `reports/` directory).
2. **Draft Content**: Write a comprehensive, engaging blog post analyzing the current state of the fantasy league.
3. **Front Matter**: Prepend the content with the exact YAML front matter template defined in `AGENTS.md`:
   ```yaml
   ---
   title: <Report Title>
   author: Nicholas Wilde
   date: <Current Date in YYYY-MM-DD>
   tags:
     - fantasy-football
     - analysis
   ---
   ```
4. **Output Artifact**: Output the generated blog post directly to the console instead of saving it to a file.
