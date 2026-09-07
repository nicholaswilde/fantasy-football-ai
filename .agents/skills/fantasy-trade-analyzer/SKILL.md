---
name: fantasy-trade-analyzer
description: Comprehensive workflow for analyzing proposed fantasy football trades, assessing positional needs, and recommending outcomes.
---

# Fantasy Trade Analyzer

This skill orchestrates the evaluation of proposed fantasy football trades using the criteria defined in the global `AGENTS.md` file.

## Instructions
When the user asks you to analyze a trade or invoke this skill:
1. **Refresh Data**: If the user hasn't synced recently, politely suggest or run `task refresh` to ensure you have the latest available players and league settings.
2. **Execute Trade Suggester**: Run `task suggest_trades` or execute `uv run python -m fantasy_football_ai.trade_suggester` to gather data on player performance, Value Over Replacement (VOR), and recent consistency metrics.
3. **Analyze Rosters**: Read the data from `data/my_team.md` and the provided opponent's roster.
4. **Formulate Recommendation**: Generate a structured markdown response strictly following the output format described in the `Trade Analysis Assistant` section of `AGENTS.md`:
   - Concise summary
   - My Team's Perspective
   - Opponent's Perspective
   - **Final Recommendation** (ACCEPT, DECLINE, or NEGOTIATE)
