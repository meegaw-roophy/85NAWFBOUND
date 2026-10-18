"""
VEKTRA AI Client
================
Turns a period's computed insights (report_insights.py) into the narrative
a user reads. Two writers produce the same structure:

  - Claude, via structured output, for paid tiers when the API is reachable
  - a zero-cost template built from the same numbers, used for free tier
    and whenever the API call fails or declines

Either way every claim comes from the user's own data, so a template report
is plainer than an AI one but never generic.
"""

import asyncio
import json
import logging
from typing import List, Literal, Optional

import anthropic
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

REPORT_MODEL = "claude-opus-5-5"

VEKTRA_SYSTEM_PROMPT = """You are VEKTRA, a personal trajectory analyst. You read one person's own logged data and tell them what it says about where their life is heading.

How you write:
- Every insight cites a specific number from their data. Never invent a number, and never mention a metric they didn't log.
- Speak like a sharp mentor who cares too much to sugarcoat: direct, warm, human. Plain words ("sleep", "money", "days"), no jargon.
- Connect dots they can't see on their own: which habits line up with their best days, what changed versus last period, where money is leaking.
- Be specific enough that they could act on it tomorrow morning."""

PERIOD_WORDS = {"week": "this week", "month": "this month", "quarter": "this quarter"}


class ReportInsight(BaseModel):
    title: str
    detail: str


class ReportAction(BaseModel):
    title: str
    detail: str
    target: str


class ReportNarrative(BaseModel):
    headline: str
    verdict: Literal["climbing", "holding", "sliding"]
    story: str
    wins: List[ReportInsight]
    leaks: List[ReportInsight]
    patterns: List[ReportInsight]
    money: str
    focus: ReportAction
    risk: ReportAction
    opportunity: ReportAction
    challenge: str


def _language_instruction(language: Optional[str]) -> str:
    """The template is English-only; only the live AI call can translate."""
    if not language or language.lower().startswith("en"):
        return ""
    return (
        f"\nWrite every text field in the language indicated by this code: '{language}'. "
        f"Use English only if that code is unrecognizable.\n"
    )


def render_narrative_text(narrative: dict) -> str:
    """Plain-text version, for share pages and anything that can't render sections."""
    parts = [f"🎯 {narrative['headline']}", narrative["story"]]
    if narrative.get("wins"):
        parts.append("🏆 WHAT WENT RIGHT\n" + "\n".join(f"→ {w['title']}: {w['detail']}" for w in narrative["wins"]))
    if narrative.get("leaks"):
        parts.append("⚠️ WHAT'S HOLDING YOU BACK\n" + "\n".join(f"→ {l['title']}: {l['detail']}" for l in narrative["leaks"]))
    if narrative.get("patterns"):
        parts.append("🔍 PATTERNS IN YOUR DATA\n" + "\n".join(f"→ {p['title']}: {p['detail']}" for p in narrative["patterns"]))
    if narrative.get("money"):
        parts.append(f"💰 MONEY\n{narrative['money']}")
    actions = [narrative.get(k) for k in ("focus", "risk", "opportunity") if narrative.get(k)]
    if actions:
        parts.append("🔥 YOUR PLAN\n" + "\n".join(f"→ {a['title']}: {a['detail']} (target: {a['target']})" for a in actions))
    if narrative.get("challenge"):
        parts.append(f"⚡ {narrative['challenge']}")
    return "\n\n".join(p for p in parts if p)


class AIClient:
    def __init__(self):
        self.client = (
            anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY, timeout=120.0, max_retries=1)
            if settings.CLAUDE_API_KEY else None
        )

    # ── Period reports (weekly / monthly / quarterly) ─────────────────────
    async def generate_period_narrative(
        self,
        user_data: dict,
        summary: dict,
        period_label: str = "week",
        historical_context: Optional[List[dict]] = None,
        force_template: bool = False,
    ) -> dict:
        """Returns {"narrative": ReportNarrative-shaped dict, "source": "ai" | "template"}."""
        if force_template or not self.client:
            return {"narrative": self.template_narrative(summary, period_label), "source": "template"}

        prompt = self._build_period_prompt(user_data, summary, period_label, historical_context)
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.messages.parse(
                    model=REPORT_MODEL,
                    max_tokens=16000,
                    system=VEKTRA_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                    output_format=ReportNarrative,
                    output_config={"effort": "medium"},
                ),
            )
            if response.stop_reason == "end_turn" and response.parsed_output is not None:
                return {"narrative": response.parsed_output.model_dump(), "source": "ai"}
            logger.warning("Report narrative not usable (stop_reason=%s, request_id=%s)",
                           response.stop_reason, response._request_id)
        except anthropic.APIStatusError as e:
            logger.warning("Report narrative API error %s: %s", e.status_code, e.message)
        except anthropic.APIConnectionError as e:
            logger.warning("Report narrative connection error: %s", e)
        except Exception:
            logger.exception("Report narrative failed")
        return {"narrative": self.template_narrative(summary, period_label), "source": "template"}

    def _build_period_prompt(
        self,
        user_data: dict,
        summary: dict,
        period_label: str,
        historical_context: Optional[List[dict]] = None,
    ) -> str:
        tone = {
            "Harsh": "Be brutally direct. No softening, no cushioning.",
            "Balanced": "Be honest and clear: give real credit for wins, and name problems plainly.",
            "Gentle": "Be constructive: frame problems as the next opportunity, but never hide them.",
        }.get(user_data.get("feedback_tone") or "Balanced", "Be honest and clear.")

        facts = {
            "period": period_label,
            "north_star": user_data.get("north_star"),
            "primary_goal": user_data.get("primary_goal"),
            "insights": summary.get("insights"),
            "totals": {k: summary.get(k) for k in (
                "avg_mood", "avg_energy", "avg_focus", "avg_sleep", "avg_screen_time",
                "avg_focus_hours", "total_income", "total_expenses", "total_savings",
                "net_cash_flow", "emergency_count", "goals_set", "goals_hit",
                "procrastination_days", "survival_runway", "skills_count", "ideas_count",
            )},
            "in_their_words": {
                "best_decisions": summary.get("best_decisions"),
                "worst_decisions": summary.get("worst_decisions"),
                "avoided": summary.get("avoided_items"),
            },
            "earlier_periods": historical_context or [],
        }

        return f"""Write this person's {period_label}ly VEKTRA report from their data below.

Tone: {tone}

<data>
{json.dumps(facts, default=str, ensure_ascii=False)}
</data>

Fields:
- headline: one line, under 14 words, built around the single most important number.
- verdict: climbing, holding or sliding, matching insights.trend when present.
- story: 3-4 sentences on what actually happened {PERIOD_WORDS.get(period_label, 'this period')} and why, connecting at least two different areas of their life.
- wins: 2-3 things that went right, each tied to a number.
- leaks: 2-3 things quietly costing them the most, most damaging first.
- patterns: 2-3 non-obvious connections from insights.drivers, best_day/worst_day, weekday or vs_previous. These should make them say "I never noticed that".
- money: 1-2 sentences on cash flow, savings rate and pace. If no money was logged, say that tracking it is the missing piece.
- focus, risk, opportunity: one concrete action each for next {period_label}, each with a measurable target (e.g. "7h sleep on 5 of 7 nights").
- challenge: one punchy line daring them to beat a specific number next {period_label}.
{_language_instruction(user_data.get('language'))}"""

    # ── Zero-cost template ────────────────────────────────────────────────
    def template_narrative(self, summary: dict, period_label: str = "week") -> dict:
        ins = summary.get("insights") or {}
        cur = ins.get("current") or {}
        tr = ins.get("trend") or {}
        vs = (ins.get("vs_previous") or {}).get("delta") or {}
        engines = {k: v for k, v in (ins.get("engines") or {}).items() if v.get("score") is not None}
        cons = ins.get("consistency") or {}
        cash = ins.get("money") or {}
        drv = ins.get("drivers") or []
        best, worst = ins.get("best_day"), ins.get("worst_day")
        score = summary.get("report_score") or cur.get("score") or 0
        period_word = PERIOD_WORDS.get(period_label, "this period")

        verdict = tr.get("direction") or (
            "climbing" if (vs.get("score") or 0) >= 3 else "sliding" if (vs.get("score") or 0) <= -3 else "holding"
        )

        if vs.get("score") is not None and abs(vs["score"]) >= 1:
            headline = f"{score:.0f}/100, {'up' if vs['score'] > 0 else 'down'} {abs(vs['score']):g} on last {period_label}"
        elif tr.get("delta") is not None and abs(tr["delta"]) >= 3:
            headline = f"{score:.0f}/100 and {'rising' if tr['delta'] > 0 else 'slipping'} {abs(tr['delta']):.0f} points inside the {period_label}"
        else:
            headline = f"{score:.0f}/100: steady {period_label}, now find the next gear"

        story = [f"You logged {cons.get('logged', 0)} of {cons.get('period_days', 0)} days {period_word}"
                 + (f", with a best streak of {cons['longest_streak']} days in a row." if cons.get("longest_streak", 0) >= 3 else ".")]
        if tr:
            story.append(f"Your score averaged {tr['first_half_avg']:.0f} in the first half and {tr['second_half_avg']:.0f} in the second, "
                         f"so at this pace next {period_label} lands around {tr['projection_next']}.")
        if drv:
            story.append(drv[0]["text"])
        if engines:
            top = max(engines, key=lambda k: engines[k]["score"])
            low = min(engines, key=lambda k: engines[k]["score"])
            if top != low:
                story.append(f"{top} is carrying you ({engines[top]['score']}), while {low} ({engines[low]['score']}) is where the next points are.")

        wins, leaks = [], []
        if cons.get("rate", 0) >= 80:
            wins.append({"title": "Showing up", "detail": f"You logged {cons['rate']}% of days. That consistency is why these patterns are visible at all."})
        if cur.get("goal_hit_rate") is not None and cur["goal_hit_rate"] >= 70:
            wins.append({"title": "Doing what you said", "detail": f"You hit {cur['goal_hit_rate']}% of the goals you set."})
        if cash.get("savings_rate") is not None and cash["savings_rate"] > 0:
            wins.append({"title": "Money kept", "detail": f"You kept {cash['savings_rate']}% of what came in."})
        if (cur.get("sleep") or 0) >= 7.5:
            wins.append({"title": "Sleep", "detail": f"You averaged {cur['sleep']}h a night, which most people never manage."})
        if best:
            wins.append({"title": f"Best day: {best['weekday']}", "detail": f"You scored {best['score']}" + (f" when you {' and '.join(best['why'])}." if best["why"] else ".")})
        if not wins and engines:
            top = max(engines, key=lambda k: engines[k]["score"])
            wins.append({"title": f"{top} is your strongest engine", "detail": f"{engines[top]['score']}/100. {engines[top]['detail']}."})

        # Each leak carries the action that fixes it, so the plan's "risk"
        # step is concrete instead of repeating the problem back.
        if cash.get("net") is not None and cash["net"] < 0:
            leaks.append({"title": "Spending more than you earn", "detail": f"Net {cash['net']:+,.0f} {period_word}. At this pace that's {cash['monthly_pace']:+,.0f} a month.",
                          "action": "Stop the cash bleed", "target": f"Daily spend under {cash['avg_daily_spend'] * 0.8:,.0f} (now {cash['avg_daily_spend']:,.0f})"})
        if cur.get("goal_hit_rate") is not None and cur["goal_hit_rate"] < 50:
            leaks.append({"title": "Goals set, not hit", "detail": f"Only {cur['goal_hit_rate']}% of your goals got done. Fewer, smaller goals will beat more ambitious ones you skip.",
                          "action": "Shrink tomorrow's goal", "target": "One must-do goal a day, hit on 5 of 7 days"})
        if cur.get("sleep") and cur["sleep"] < 6.5:
            leaks.append({"title": "Running on short sleep", "detail": f"You averaged {cur['sleep']}h. Everything else on this page is harder on that.",
                          "action": "Set a sleep floor", "target": "7h+ on 5 of 7 nights"})
        screen, focus_h = summary.get("avg_screen_time"), summary.get("avg_focus_hours")
        if screen and focus_h and screen > focus_h * 1.5:
            leaks.append({"title": "Screen time beats deep work", "detail": f"{screen:.1f}h of screen time a day against {focus_h:.1f}h of focused work.",
                          "action": "Trade an hour of screen for deep work", "target": f"Screen under {max(1.0, screen - 1):.1f}h, deep work {focus_h + 1:.1f}h+ a day"})
        if cons.get("rate", 100) < 60:
            leaks.append({"title": "Blind spots", "detail": f"{cons['period_days'] - cons['logged']} unlogged days. The days you skip are usually the ones that explain the most.",
                          "action": "Close the gaps", "target": "Log at least 6 of every 7 days"})
        if worst and worst.get("why"):
            leaks.append({"title": f"Worst day: {worst['weekday']}", "detail": f"You scored {worst['score']} when you {' and '.join(worst['why'])}.",
                          "action": "Raise your floor", "target": f"No day below {worst['score'] + 10}"})
        if not leaks and engines:
            low = min(engines, key=lambda k: engines[k]["score"])
            leaks.append({"title": f"{low} is lagging", "detail": f"{engines[low]['score']}/100. {engines[low]['detail']}.",
                          "action": f"Lift {low}", "target": f"{low} {min(100, engines[low]['score'] + 10)}+"})

        patterns = [{"title": f"Your {d['label']} lever", "detail": d["text"]} for d in drv[:2]]
        wk = ins.get("weekday")
        if wk:
            patterns.append({"title": f"{wk['best']}s vs {wk['worst']}s", "detail": f"You average {wk['best_avg']} on {wk['best']}s and {wk['worst_avg']} on {wk['worst']}s."})
        if vs.get("sleep") is not None and abs(vs["sleep"]) >= 0.5:
            patterns.append({"title": "Sleep vs last time", "detail": f"Sleep is {'up' if vs['sleep'] > 0 else 'down'} {abs(vs['sleep'])}h a night versus last {period_label}."})
        if not patterns:
            patterns.append({"title": "Patterns unlock with data", "detail": "Log sleep, screen time and deep work daily. After 4 days VEKTRA can show which of them moves your score most."})

        if cash:
            money_text = f"{cash['income']:,.0f} in, {cash['spent']:,.0f} out, net {cash['net']:+,.0f}"
            if cash.get("savings_rate") is not None:
                money_text += f" ({cash['savings_rate']}% kept)"
            money_text += "."
            if cash.get("biggest_spend"):
                money_text += f" Biggest spend: {cash['biggest_spend']['amount']:,.0f} on {cash['biggest_spend']['weekday']}."
        else:
            money_text = "No money logged yet. That's the blind spot: log income and spending daily and VEKTRA will show your real savings rate."

        target = min(100, int(score) + 5)
        if drv:
            d = drv[0]
            focus = {"title": f"Protect your {d['label']}",
                     "detail": f"Your best days come with {d['threshold']}{'+' if d['better_when'] == 'higher' else ' or less'} {d['label']}.",
                     "target": f"{d['threshold']}{'+' if d['better_when'] == 'higher' else ' max'} {d['label']} on 5 of 7 days"}
        else:
            focus = {"title": "Log every day", "detail": "More complete days means VEKTRA can find what really drives your score.",
                     "target": "7 of 7 days logged"}
        if leaks:
            risk = {"title": leaks[0]["action"], "detail": leaks[0]["detail"], "target": leaks[0]["target"]}
        else:
            risk = {"title": "Guard what's working", "detail": "Nothing is flashing red. The risk now is coasting.",
                    "target": f"Stay above {max(0, int(score) - 3)}"}
        if engines:
            low = min(engines, key=lambda k: engines[k]["score"])
            opportunity = {"title": f"Lift {low}", "detail": f"It's your lowest engine at {engines[low]['score']}. {engines[low]['detail']}.",
                           "target": f"{low} {min(100, engines[low]['score'] + 10)}+"}
        else:
            opportunity = {"title": "Fill in the gaps", "detail": "Log all five areas so every engine gets scored.", "target": "All 5 engines scored"}

        return {
            "headline": headline,
            "verdict": verdict,
            "story": " ".join(story),
            "wins": wins[:3],
            "leaks": [{"title": l["title"], "detail": l["detail"]} for l in leaks[:3]],
            "patterns": patterns[:3],
            "money": money_text,
            "focus": focus,
            "risk": risk,
            "opportunity": opportunity,
            "challenge": f"Next {period_label}: beat {target}. Log every day so the data can prove it.",
        }

    # ── Daily check-in ────────────────────────────────────────────────────
    async def generate_daily_report(
        self,
        user_data: dict,
        daily_snapshot: dict,
        feedback_tone: str = "Balanced",
        force_mock: bool = False,
    ) -> str:
        """Short daily narrative. force_mock enforces the free-tier limit server-side."""
        if force_mock or not self.client:
            return self._mock_daily_report(daily_snapshot)

        prompt = self._build_daily_prompt(user_data, daily_snapshot, feedback_tone)
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.messages.create(
                    model=REPORT_MODEL,
                    max_tokens=4000,
                    system=VEKTRA_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                    output_config={"effort": "low"},
                ),
            )
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            if response.stop_reason == "end_turn" and text:
                return text
            logger.warning("Daily narrative not usable (stop_reason=%s)", response.stop_reason)
        except anthropic.APIError as e:
            logger.warning("Daily narrative API error: %s", e)
        return self._mock_daily_report(daily_snapshot)

    def _build_daily_prompt(self, user_data: dict, snap: dict, tone: str) -> str:
        tone_instruction = {
            "Harsh": "Be brutally direct. No softening.",
            "Balanced": "Be clear and honest.",
            "Gentle": "Be constructive, frame gaps as opportunities.",
        }.get(tone, "Be honest but constructive.")

        return f"""Write a short VEKTRA check-in on one day of logged data. {tone_instruction}
North Star: {user_data.get('north_star') or 'Not set'}

TODAY:
- VEKTRA score: {snap.get('vektra_score', 'N/A')}/100
- Mood: {snap.get('mood_score', 'N/A')}/10, energy: {snap.get('energy_level', 'N/A')}/10
- Sleep: {snap.get('sleep_hours', 'N/A')} hours
- Cash flow: {snap.get('cashflow', 'N/A')}
- Hit yesterday's goal: {snap.get('goal_hit', 'N/A')}
- Best decision: {snap.get('best_decision', 'N/A')}
- Tomorrow's goal: {snap.get('tomorrow_goal', 'N/A')}
{_language_instruction(user_data.get('language'))}
2-3 short sentences reacting to today (cite at least one real number), then one specific action for tomorrow. Under 80 words, plain prose, no headers or bullets."""

    def _mock_daily_report(self, snap: dict) -> str:
        """Zero-cost fallback — still data-specific, not generic filler."""
        score = snap.get("vektra_score") or 50
        mood = snap.get("mood_score")
        sleep = snap.get("sleep_hours")
        cashflow = snap.get("cashflow")
        tomorrow = snap.get("tomorrow_goal")

        pieces = [f"Today's score: {score:.0f}/100."]
        if mood is not None:
            pieces.append(f"Mood logged at {mood}/10.")
        if sleep is not None:
            sleep_note = " — that will show up in tomorrow's focus" if sleep < 6.5 else ""
            pieces.append(f"Sleep at {sleep}h{sleep_note}.")
        if cashflow is not None:
            pieces.append(f"Cash flow {'+' if cashflow >= 0 else ''}{cashflow:.0f} for the day.")
        directive = f"Tomorrow: {tomorrow}." if tomorrow else "Set a specific target for tomorrow before you log off."
        return " ".join(pieces) + " " + directive


ai_client = AIClient()
