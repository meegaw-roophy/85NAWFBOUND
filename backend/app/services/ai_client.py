"""
VEKTRA AI Client
================
Handles all Claude API calls for report generation.
Uses claude-sonnet-4-6 with the messages API (not deprecated completions).
Falls back to structured mock report when API key not configured.
"""

import asyncio
from anthropic import Anthropic
from typing import List, Optional
from app.core.config import settings


VEKTRA_SYSTEM_PROMPT = """You are VEKTRA — an elite personal trajectory analyst. 
You speak with brutal honesty, data-driven precision, and genuine care for the user's growth.

Your reports follow this philosophy:
- No sugarcoating. The data tells the truth even when it's uncomfortable.
- Every insight must reference specific numbers from the user's data.
- Identify patterns, not just averages.
- Separate what the user controls from what they don't.
- End with a clear, specific directive for the next period.

Tone: Direct. Sharp. Like a mentor who believes in you too much to lie to you.
Format: Structured but conversational. No corporate language. No empty motivational phrases."""


class AIClient:
    def __init__(self):
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY) if settings.CLAUDE_API_KEY else None

    async def generate_weekly_report(
        self,
        user_data: dict,
        weekly_summary: dict,
        feedback_tone: str = "Balanced",
        historical_context: Optional[List[dict]] = None
    ) -> str:
        """
        Generate a weekly VEKTRA report using Claude API.
        Falls back to structured mock if no API key.
        """
        if not self.client:
            return self._mock_weekly_report(weekly_summary, historical_context)

        prompt = self._build_weekly_prompt(user_data, weekly_summary, feedback_tone, historical_context)

        response = await asyncio.to_thread(
            lambda: self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1500,
                system=VEKTRA_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
        )
        return response.content[0].text

    def _build_weekly_prompt(
        self,
        user_data: dict,
        summary: dict,
        tone: str,
        historical_context: Optional[List[dict]] = None
    ) -> str:
        """Build the weekly report prompt from user data and weekly summary."""

        north_star = user_data.get('north_star', 'Not set')
        primary_goal = user_data.get('primary_goal', 'Not set')
        unique_days = summary.get('unique_days_logged', summary.get('days_logged', 0))
        report_countdown = summary.get('report_countdown', max(0, 7 - unique_days))
        tone_instruction = {
            'Harsh': 'Be brutally direct. No softening. Call out failures clearly.',
            'Balanced': 'Be honest but constructive. Balance wins with areas to improve.',
            'Gentle': 'Be encouraging. Frame challenges as opportunities. Stay supportive.',
        }.get(tone, 'Be honest but constructive.')

        # Build historical context section
        historical_section = ""
        if historical_context and len(historical_context) > 0:
            historical_section = "\nHISTORICAL CONTEXT (Last 4 weeks):\n"
            for i, week in enumerate(historical_context, 1):
                historical_section += f"- Week {i}: VEKTRA Score {week.get('vektra_score', 'N/A')}, Mood {week.get('mood', 'N/A')}, Sleep {week.get('sleep', 'N/A')}h, Cash Flow {week.get('net_cash_flow', 'N/A')}, Goal Rate {week.get('goal_hit_rate', 'N/A')}%\n"
            historical_section += "\nUse this historical data to identify trends and patterns. Is the trajectory improving, declining, or stable?\n"

        return f"""Generate a VEKTRA weekly report for this user.

TONE INSTRUCTION: {tone_instruction}

USER CONTEXT:
- North Star: {north_star}
- Primary Goal: {primary_goal}
- Days logged this week: {unique_days}/7
- Weekly countdown: {report_countdown}/7

WEEKLY AVERAGES:
- VEKTRA Score: {summary.get('avg_vektra_score', 'N/A')}/100
- Mood: {summary.get('avg_mood', 'N/A')}/10
- Energy: {summary.get('avg_energy', 'N/A')}/10
- Focus Level: {summary.get('avg_focus', 'N/A')}/10
- Sleep: {summary.get('avg_sleep', 'N/A')} hours
- Focus Hours (deep work): {summary.get('avg_focus_hours', 'N/A')} hrs/day
- Screen Time: {summary.get('avg_screen_time', 'N/A')} hrs/day

FINANCIAL WEEK:
- Total Income: {summary.get('total_income', 0)}
- Total Expenses: {summary.get('total_expenses', 0)}
- Net Cash Flow: {summary.get('net_cash_flow', 0)}
- Total Saved/Invested: {summary.get('total_savings', 0)}
- Emergencies: {summary.get('emergency_count', 0)} this week

EXECUTION:
- Goals hit: {summary.get('goals_hit', 0)}/{summary.get('goals_set', 0)}
- Days with procrastination flagged: {summary.get('procrastination_days', 0)}
- Average leverage score: {summary.get('avg_leverage', 'N/A')}
- Survival runway: {summary.get('survival_runway', 'N/A')} days

GROWTH THIS WEEK:
- Skills logged: {summary.get('skills_count', 0)} days
- New ideas captured: {summary.get('ideas_count', 0)} days
- Interactions done: {summary.get('interactions_count', 0)} days

HIGHLIGHTS FROM LOGS:
- Best decisions: {summary.get('best_decisions', [])}
- Worst decisions: {summary.get('worst_decisions', [])}
- What was avoided: {summary.get('avoided_items', [])}
- Funny lines (wellbeing signal): {summary.get('funny_lines', [])}
{historical_section}
Generate a weekly report with these sections:
1. TRAJECTORY STATUS (2-3 sentences — is the vector moving right? Compare with historical trends if available)
2. YOUR WINS THIS WEEK (specific, data-backed)
3. SILENT KILLERS (what's quietly dragging the score down)
4. THE NUMBERS DON'T LIE (key financial and execution stats with commentary)
5. NEXT WEEK DIRECTIVE (one specific, actionable instruction)

Keep it under 400 words. Make every sentence earn its place."""

    def _mock_weekly_report(self, summary: dict, historical_context: Optional[List[dict]] = None) -> str:
        """
        Structured mock report when Claude API key not configured.
        Used during development before API key is added.
        """
        score = summary.get('report_score', summary.get('avg_vektra_score', 50))
        days = summary.get('days_logged', 0)
        cash_flow = summary.get('net_cash_flow', 0)
        goals_hit = summary.get('goals_hit', 0)
        goals_set = summary.get('goals_set', 0)
        sleep = summary.get('avg_sleep', 0)
        unique_days = summary.get('unique_days_logged', summary.get('days_logged', 0))
        report_countdown = summary.get('report_countdown', max(0, 7 - unique_days))
        goal_rate = round(goals_hit / goals_set * 100, 1) if goals_set > 0 else None

        # Analyze historical trend if available
        trend_analysis = ""
        if historical_context and len(historical_context) > 0:
            prev_scores = [w.get('vektra_score') for w in historical_context if w.get('vektra_score')]
            if prev_scores:
                avg_prev = sum(prev_scores) / len(prev_scores)
                if score > avg_prev + 5:
                    trend_analysis = f"Your trajectory is improving compared to your {len(prev_scores)}-week average of {avg_prev:.0f}."
                elif score < avg_prev - 5:
                    trend_analysis = f"Your trajectory is declining compared to your {len(prev_scores)}-week average of {avg_prev:.0f}."
                else:
                    trend_analysis = f"Your trajectory is stable around your {len(prev_scores)}-week average of {avg_prev:.0f}."

        trajectory = "RISING" if score >= 65 else "FLAT" if score >= 45 else "DECLINING"
        momentum_line = (
            'Strong momentum — keep the system running.'
            if score >= 65 else
            'Momentum is stalling. The gap between what you plan and what you execute is the problem.'
            if score >= 45 else
            'The trajectory is pointing down. Something needs to change this week, not next week.'
        )
        consistency_line = '- You showed up and logged data — consistency is the foundation.' if unique_days >= 4 else '- You logged some data — now build the habit of daily logging.'

        return f"""VEKTRA WEEKLY REPORT
{'='*40}

TRAJECTORY STATUS: {trajectory}
Your composite VEKTRA score this week was {score}/100 across {unique_days} unique days logged.
{momentum_line}
{trend_analysis}

YOUR WINS THIS WEEK:
{consistency_line}
{'- Cash flow was positive this week.' if cash_flow > 0 else ''}
{'- Sleep averaged above the optimal threshold.' if sleep and sleep >= 7 else ''}

SILENT KILLERS:
{'- Only logged ' + str(unique_days) + '/7 days — missing days = missing data = weak reports.' if unique_days < 7 else ''}
{'- Cash flow negative this week — expenses exceeding income.' if cash_flow < 0 else ''}
{'- Goal hit rate: ' + str(goals_hit) + '/' + str(goals_set) + ' — execution needs tightening.' if goals_set > 0 and goal_rate is not None and goal_rate < 60 else ''}

THE NUMBERS DON'T LIE:
- Net cash flow: {cash_flow}
- Goals completed: {goals_hit}/{goals_set}
- Days logged: {unique_days}/7
- Weekly countdown: {report_countdown}/7
- Average sleep: {sleep} hours

NEXT WEEK DIRECTIVE:
{'Log every single day this week. No exceptions. Incomplete data produces weak reports and weak insights.' if unique_days < 7 else 'Push your VEKTRA score above ' + str(min(100, int(score) + 10)) + ' — identify which sub-engine is dragging you and attack it specifically.'}

[Note: Connect your CLAUDE_API_KEY in .env to unlock full AI-powered narrative reports with historical trend analysis]
{'='*40}"""


ai_client = AIClient()
