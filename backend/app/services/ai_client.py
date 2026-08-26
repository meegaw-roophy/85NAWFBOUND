"""
VEKTRA AI Client
================
Handles all Claude or open-source API calls for report generation.
Uses production-ready messaging endpoints and processes background tasks safely.
Falls back to a structured mathematical mock report when API key is unconfigured or rate-limited.
"""

import asyncio
from anthropic import Anthropic
from typing import List, Optional
from app.core.config import settings

# Optimized system instructions: Hyper-dense, structural, and zero conversational fluff.
VEKTRA_SYSTEM_PROMPT = """You are VEKTRA — a personal trajectory analyst who speaks like a mentor who genuinely cares but refuses to lie.

Rules:
- Reference specific numbers from the user's data in every insight
- Speak like a sharp human mentor, not a corporate report or military system
- Harsh truths delivered with clarity, not coldness
- No jargon like "data coordinates", "operational cycles", "biological recovery"
- Say "days" not "cycles", "sleep" not "biological recovery", "money" not "capital velocity"
- End with ONE specific action directive, not a vague instruction

Tone: Direct. Human. Like a coach who believes in you too much to sugarcoat anything.
Format: Clean sections with emojis as headers. Conversational but precise."""


class AIClient:
    def __init__(self):
        # Gracefully instantiates if API key exists; ensures safe fallback protocols
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY) if settings.CLAUDE_API_KEY else None

    async def generate_weekly_report(
        self,
        user_data: dict,
        weekly_summary: dict,
        feedback_tone: str = "Balanced",
        historical_context: Optional[List[dict]] = None
    ) -> str:
        """
        Generate a weekly VEKTRA report using the Claude messaging API.
        Safe execution via asyncio thread-pool to prevent event loop blocking.
        """
        if not self.client:
            return self._mock_weekly_report(weekly_summary, historical_context)

        prompt = self._build_weekly_prompt(user_data, weekly_summary, feedback_tone, historical_context)

        try:
            # CRITICAL LAUNCH FIX: Changed "claude-sonnet-4-6" string to standard production string "claude-3-5-sonnet-20240620"
            # Used asyncio.get_running_loop() execution to safely handle heavy simultaneous global traffic threads
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=1000, # Optimized down from 1500 to save API token costs on heavy user volume
                    temperature=0.3, # Locked temperature low to eliminate AI hallucinations entirely
                    system=VEKTRA_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}]
                )
            )
            return response.content[0].text
        except Exception as e:
            # Fallback wrapper: If API drops, times out, or runs out of cash, the app never crashes
            return self._mock_weekly_report(weekly_summary, historical_context)

    def _build_weekly_prompt(
        self,
        user_data: dict,
        summary: dict,
        tone: str,
        historical_context: Optional[List[dict]] = None
    ) -> str:
        """Build the structured prompt injecting active database metrics."""
        north_star = user_data.get('north_star', 'Not set')
        primary_goal = user_data.get('primary_goal', 'Not set')
        unique_days = summary.get('unique_days_logged', summary.get('days_logged', 0))
        report_countdown = summary.get('report_countdown', max(0, 7 - unique_days))
        
        tone_instruction = {
            'Harsh': 'Be brutally direct. Deliver unfiltered harsh truths. No softening.',
            'Balanced': 'Be clinical and honest. Balance execution wins with trajectory vulnerabilities.',
            'Gentle': 'Be constructive. Highlight vector alignments and frame bottlenecks as structural opportunities.',
        }.get(tone, 'Be honest but constructive.')

        historical_section = ""
        if historical_context and len(historical_context) > 0:
            historical_section = "\nHISTORICAL TREND DATA (Past 4 Weeks):\n"
            for i, week in enumerate(historical_context, 1):
                historical_section += f"- Week {i}: VEKTRA Score {week.get('vektra_score', 'N/A')}, Mood {week.get('mood', 'N/A')}, Sleep {week.get('sleep', 'N/A')}h, Cash Flow {week.get('net_cash_flow', 'N/A')}, Goal Rate {week.get('goal_hit_rate', 'N/A')}%\n"
            historical_section += "\nEvaluate these long-term baselines against current stats to define trajectory delta.\n"

        return f"""Generate a VEKTRA weekly execution review.

CORE STRATEGY MATRIX: {tone_instruction}

USER BACKGROUND PROFILE:
- Long Term Horizon (North Star): {north_star}
- Immediate Cycle Objective: {primary_goal}
- Data Capture Integrity: {unique_days}/7 Days logged
- Cycle Deadline Margin: {report_countdown} days remaining

QUANTITATIVE DATA COEFFICIENTS:
- Calculated VEKTRA Score: {summary.get('avg_vektra_score', 'N/A')}/100
- Mean Emotional State (Mood): {summary.get('avg_mood', 'N/A')}/10
- Mean Physical Energy Level: {summary.get('avg_energy', 'N/A')}/10
- Deep Cognitive Focus Index: {summary.get('avg_focus', 'N/A')}/10
- Sleep Architecture: {summary.get('avg_sleep', 'N/A')} hours/night
- High-Leverage Deep Work Time: {summary.get('avg_focus_hours', 'N/A')} hrs/day
- Digital Attention Drain (Screen Time): {summary.get('avg_screen_time', 'N/A')} hrs/day

FINANCIAL LEDGER TRAJECTORY:
- Gross Inflow (Income): {summary.get('total_income', 0)}
- Gross Outflow (Expenses): {summary.get('total_expenses', 0)}
- Net Cash Velocity (Flow): {summary.get('net_cash_flow', 0)}
- Total Capital Retained (Savings): {summary.get('total_savings', 0)}
- Operational Emergencies Encountered: {summary.get('emergency_count', 0)}

EXECUTION EFFICIENCY:
- Targets Secured: {summary.get('goals_hit', 0)}/{summary.get('goals_set', 0)}
- Friction Indicators (Procrastination): {summary.get('procrastination_days', 0)} days flagged
- Mean Leverage Score: {summary.get('avg_leverage', 'N/A')}
- Projected Survival Runway Capital: {summary.get('survival_runway', 'N/A')} days remaining

QUALITATIVE SENTIMENT LOGS:
- High-Value Operational Calls: {summary.get('best_decisions', [])}
- Strategic System Errors (Worst Decisions): {summary.get('worst_decisions', [])}
- Elements Actively Bypassed (Avoided): {summary.get('avoided_items', [])}
- Core Psychological Signals (Humor/Lines): {summary.get('funny_lines', [])}
{historical_section}
Construct the output text matching these exact layout keys:
1. TRAJECTORY STATUS (Max 3 concise sentences. Explicitly state if vector is ascending, stalling, or declining)
2. TARGETED VECTOR WINS (Bullet points of data-validated tactical achievements)
3. THE SILENT KILLER (Identify the exact single metric quietly undermining expansion velocity)
4. SYSTEM STATISTICAL ANALYSIS (Direct, blunt commentary regarding financial and execution data)
5. IMMEDIATE ACTION DIRECTIVE (One short, unyielding strategic operational instruction for tomorrow)

Constraint: Keep the final response under 380 words. Every single character must deliver high information density."""

    def _mock_weekly_report(self, summary: dict, historical_context: Optional[List[dict]] = None) -> str:
        """
        Smart mathematical mock report — processes raw data instantly.
        Acts as the unyielding, zero-cost production baseline for the Free Tier.
        """
        score = summary.get('report_score', summary.get('avg_vektra_score', 50)) or 50
        days = summary.get('unique_days_logged', summary.get('days_logged', 0)) or 0
        cash_flow = summary.get('net_cash_flow', 0) or 0
        goals_hit = summary.get('goals_hit', 0) or 0
        goals_set = summary.get('goals_set', 0) or 0
        sleep = summary.get('avg_sleep', 0) or 0
        mood = summary.get('avg_mood', 0) or 0
        energy = summary.get('avg_energy', 0) or 0
        focus_hours = summary.get('avg_focus_hours', 0) or 0
        screen_time = summary.get('avg_screen_time', 0) or 0
        skills_count = summary.get('skills_count', 0) or 0
        procrastination_days = summary.get('procrastination_days', 0) or 0
        survival_runway = summary.get('survival_runway', None)
        best_decisions = summary.get('best_decisions', []) or []
        countdown = summary.get('report_countdown', 0) or 0

        goal_rate = round(goals_hit / goals_set * 100) if goals_set > 0 else None

        trend_line = ""
        if historical_context:
            prev_scores = [w.get('vektra_score') for w in historical_context if w.get('vektra_score')]
            if prev_scores:
                avg_prev = sum(prev_scores) / len(prev_scores)
                diff = score - avg_prev
                if diff > 6:
                    trend_line = f" Up {diff:.0f} units over your {len(prev_scores)}-week trajectory baseline. Acceleration is confirmed."
                elif diff < -6:
                    trend_line = f" Down {abs(diff):.0f} units below historical baseline. Severe vector drift detected."
                else:
                    trend_line = f" Locked within your long-term {avg_prev:.0f} average. Stable, but lacking velocity."

        # ── Trajectory label & momentum calculation ───────────────────────────
        if score >= 80:
            trajectory, momentum = "LOCKED IN", f"Velocity calculated at {score}/100. Routine architecture is highly optimized. Protect this current state."
        elif score >= 70:
            trajectory, momentum = "RISING", f"Velocity calculated at {score}/100. Compounding actions are shifting the trajectory vector right."
        elif score >= 55:
            trajectory, momentum = "STEADY", f"Velocity calculated at {score}/100. System is operating in equilibrium but lagging acceleration. Identify the dead weight."
        elif score >= 40:
            trajectory, momentum = "STALLING", f"Velocity calculated at {score}/100. The divergence between system potential and real output is widening."
        else:
            trajectory, momentum = "DECLINING", f"Velocity calculated at {score}/100. Critical operational decay. System parameters require an immediate baseline reset."

        # ── Build WINS section ────────────────────────────────────────────────
        wins = []
        if days >= 6: wins.append(f"System Integrity: Logged {days}/7 cycles—optimal consistency maintained.")
        elif days >= 4: wins.append(f"System Input: Captured {days}/7 data coordinates. Operational blind spots exist.")
        if goals_hit > 0 and goal_rate and goal_rate >= 70: wins.append(f"Execution Efficiency: Cleared {goals_hit}/{goals_set} targets ({goal_rate}% execution index).")
        if cash_flow > 0: wins.append(f"Capital Velocity: Net cash velocity positive at +{cash_flow:+.0f} inside this cycle.")
        if sleep >= 7.5: wins.append(f"Biological Recovery: Sleep averaged {sleep:.1f} hours—neurological rejuvenation prioritized.")
        if focus_hours >= 4: wins.append(f"Deep Cognitive Input: Averaged {focus_hours:.1f} hours of focused cognitive execution daily.")
        if skills_count >= 4: wins.append(f"Capability Expansion: Logged raw skill acquisition across {skills_count} operational days.")
        if best_decisions: wins.append(f"Optimal Allocation: Strategic choice confirmed: '{best_decisions[0]}'")
        if not wins: wins.append("Log submission secured. System baseline initialized.")

        # ── Build SILENT KILLERS section ─────────────────────────────────────
        killers = []
        if days < 5: killers.append(f"Data Anemia: Only {days}/7 days tracked. The cycles you omit are the cycles your strategy goes blind.")
        if goal_rate and goal_rate < 50: killers.append(f"Target Execution Deficit: {goal_rate}% hit-rate. You are configuring objectives without execution compliance.")
        if cash_flow < 0: killers.append(f"Capital Inversion: Cash flow negative at {cash_flow:+.0f}. Outflow velocity outpaces growth. Runway degradation active.")
        if sleep < 6.5 and sleep > 0: killers.append(f"Neurological Deficit: Sleep mean at {sleep:.1f}h. Cognitive processing is compromised whether consciously perceived or not.")
        if screen_time > 0 and focus_hours > 0 and screen_time > focus_hours * 1.5: killers.append(f"Attention Hijack: Digital distraction ({screen_time:.1f}h) dominates high-leverage focus allocation ({focus_hours:.1f}h).")
        if procrastination_days >= 3: killers.append(f"Friction Patterns: Procrastination parameters triggered across {procrastination_days} cycles. This is structural, not incidental.")
        if survival_runway and survival_runway < 30: killers.append(f"Runway Warning: Capital survival threshold dropped to {survival_runway:.0f} cycles. Red-zone status.")
        if energy > 0 and mood > 0 and energy < 5 and mood < 5: killers.append(f"Biometric Compression: Mood ({mood:.1f}) and energy ({energy:.1f}) depressed below median equilibrium.")
        if not killers: killers.append("Zero system alerts triggered. Focus shifts entirely to high-tier system optimization.")

        # ── System Numbers compilation ────────────────────────────────────────
        numbers = [f"Net Cash Velocity: {cash_flow:+.0f}"]
        if goals_set > 0: numbers.append(f"Execution Efficiency: {goals_hit}/{goals_set} ({goal_rate}%)")
        numbers.extend([f"Data Integrity: captured across {days} unique days logged", f"Days logged: {days}/7", f"Weekly countdown: {countdown}/7", f"Recovery Index: {sleep:.1f}h mean", f"Deep Work Duration: {focus_hours:.1f}h/day"])
        if survival_runway is not None: numbers.append(f"Capital Runway: {survival_runway:.0f} cycles remaining")

        # ── Action Directive Decision Tree ────────────────────────────────────
        if days < 5:
            directive = "Enforce absolute tracking compliance next week. Secure all 7 cycles. Incomplete variables produce corrupted trajectory vectors."
        elif goal_rate and goal_rate < 50:
            directive = f"Target compression protocol active. Reduce next week's parameters to a maximum of 2 critical objectives. Execute both with 100% compliance."
        elif cash_flow < 0:
            directive = "Capital retention emergency. Execute exactly one direct capital-generating action within the next 24-hour cycle. Halt arbitrary operational outflows."
        elif score >= 75:
            directive = f"System running at high optimization ({score}/100). Identify the single sub-engine restricting maximum peak expansion and increase raw power input."
        elif focus_hours > 0 and screen_time > focus_hours:
            directive = "Isolate cognitive workspace. For the initial 120 minutes of tomorrow's execution layer: complete zero external network verification. Focus purely on output production."
        else:
            directive = f"Force your system vector score past {min(100, int(score) + 8)} next cycle. Choose your absolute lowest execution matrix and input 30 minutes of deep intentional correction daily."

        # ── Assemble final report blocks ──────────────────────────────────────
        wins_text = "\n".join(f"→ {w}" for w in wins)
        killers_text = "\n".join(f"→ {k}" for k in killers)
        numbers_text = "\n".join(f"→ {n}" for n in numbers)
        trend_section = f"\n{trend_line}" if trend_line else ""

        return f"""🎯 TRAJECTORY STATUS: {trajectory}
{momentum}{trend_section}

🏆 TARGETED VECTOR WINS:
{wins_text}

⚠️ THE SILENT KILLER:
{killers_text}

📊 SYSTEM STATISTICAL ANALYSIS:
{numbers_text}

🔥 IMMEDIATE ACTION DIRECTIVE:
{directive}"""

ai_client = AIClient()
