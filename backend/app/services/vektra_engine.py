"""
VEKTRA Score Engine — V1
========================
Calculates the master VEKTRA trajectory score (0-100) from a daily snapshot.

Architecture:
    5 sub-engines → weighted combination → master score

Sub-engines:
    Financial   30%  — money flow, savings, net worth direction
    Mental      25%  — mood, energy, focus, social/health battery
    Execution   25%  — goals hit, focus hours, procrastination, screen time
    Body        10%  — sleep, diet, weight trend
    Growth      10%  — skills, ideas, interactions, quotes

NOTE: This is V1. Formulas will grow in complexity as:
    - More snapshots compile (historical averages become available)
    - Mathematical knowledge deepens (polynomial models, regression etc)
    - Real user data reveals what actually predicts success
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class VektraScoreResult:
    """All computed scores returned by the engine."""
    # sub-engine scores (0-100 each)
    financial_score: float = 50.0
    mental_score: float = 50.0
    execution_score: float = 50.0
    body_score: float = 50.0
    growth_score: float = 50.0

    # master score
    vektra_score: float = 50.0

    # computed financial metrics
    burn_rate: Optional[float] = None          # daily spend rate
    net_worth_variance: Optional[float] = None # % change vs previous
    resilience_score: Optional[float] = None   # months survivable at 0 income
    survival_runway: Optional[float] = None    # days survivable at current burn

    # computed behavioral metrics
    procrastination_delta: Optional[float] = None  # % tasks avoided
    leverage_score: Optional[float] = None         # output per unit time+energy
    system_leak: Optional[float] = None            # planned vs actual focus gap
    opportunity_cost_score: Optional[float] = None # % time on low value tasks
    
    # coaching tip
    coaching_tip: Optional[str] = None

    @property
    def shareable_summary(self) -> str:
        if self.vektra_score >= 80:
            return f"VEKTRA Peak: {self.vektra_score}/100. Unstoppable."
        elif self.vektra_score >= 50:
            return f"VEKTRA Level: {self.vektra_score}/100. Momentum building."
        else:
            return f"VEKTRA Status: {self.vektra_score}/100. Resetting trajectory."

    @property
    def viral_caption(self) -> str:
        if self.vektra_score >= 90:
            return f"I just hit a {self.vektra_score} on my VEKTRA scale while you were scrolling TikTok. We are not the same. [UPWARD TREND]"
        elif self.vektra_score >= 70:
            return f"My VEKTRA score is a {self.vektra_score}. Building an empire, one day at a time. [TEMPLE]"
        elif self.vektra_score >= 50:
            return f"Hit {self.vektra_score}/100 on VEKTRA today. Consistency beats talent every single time. [WRENCH]"
        else:
            return f"Today was a reset day ({self.vektra_score}/100). Recalibrating trajectory for a massive bounceback tomorrow. [GEAR]"

    # confidence (0-1) — how many inputs were actually logged
    confidence: float = 1.0


def get_coaching_tip(result: VektraScoreResult) -> str:
    """Generates an AI-driven actionable insight based on the score."""
    if result.vektra_score >= 80:
        return "You're in the flow state. Keep your routine tight and scale your output."
    
    if result.execution_score < 40:
        return "Execution is dipping. Pick one high-value task for tomorrow and ignore everything else."
    
    if result.financial_score < 40:
        return "Financial discipline needs attention. Review your daily burn and look for one leakage point."
    
    if result.mental_score < 50:
        return "Mental battery low. Prioritize 30 minutes of intentional rest before bed tonight."
    
    return "Refine your focus. What is the one thing that will compound most for tomorrow?"


def _safe(value, default=None):
    """Return value if not None, else default."""
    return value if value is not None else default


def _clamp(value: float, min_val=0.0, max_val=100.0) -> float:
    """Keep score within 0-100 range."""
    return max(min_val, min(max_val, value))


def _scale_slider(value: Optional[int], weight: float = 1.0) -> Optional[float]:
    """
    Convert a 1-10 slider input to 0-100 score.
    Returns None if input not logged (null = no data, not penalized).
    """
    if value is None:
        return None
    # 1-10 → 0-100, with slight curve favoring higher values
    return _clamp((value - 1) / 9 * 100 * weight)


# ─────────────────────────────────────────────
#  SUB-ENGINE 1: FINANCIAL (30%)
# ─────────────────────────────────────────────
def calculate_financial_score(
    daily_income: Optional[float],
    expenses: Optional[float],
    savings_investments: Optional[float],
    current_net_worth: Optional[float],
    previous_net_worth: Optional[float],  # from previous snapshot
    current_capital: Optional[float],
    emergency_amount: Optional[float],
) -> dict:
    """
    Financial engine — scores money flow and wealth direction.

    Logic:
        - Positive cash flow (income > expenses) → good
        - Savings ratio (savings / income) → rewards discipline
        - Net worth going up → trajectory bonus
        - Emergency hitting → penalty

    Returns dict with score + computed financial metrics.
    """
    scores = []
    metrics = {}

    # ── Cash flow score ──────────────────────
    if daily_income is not None and expenses is not None:
        if daily_income == 0 and expenses == 0:
            scores.append(50)  # neutral — nothing happened
        elif daily_income > 0:
            # cash flow ratio: how much of income is left after expenses
            flow_ratio = (daily_income - expenses) / daily_income
            # -1 (spending 2x income) to 1 (spending nothing) → 0 to 100
            cash_flow_score = _clamp((flow_ratio + 1) / 2 * 100)
            scores.append(cash_flow_score)
        elif expenses > 0:
            # spending with no income — penalty proportional to amount
            scores.append(20)
    # null income AND null expenses → no data, skip

    # ── Savings ratio score ──────────────────
    if savings_investments is not None and daily_income is not None and daily_income > 0:
        savings_ratio = savings_investments / daily_income  # 0 to 1+
        savings_score = _clamp(savings_ratio * 150)  # 150 so 67% savings = 100
        scores.append(savings_score)

    # ── Net worth direction ──────────────────
    if current_net_worth is not None and previous_net_worth is not None and previous_net_worth != 0:
        variance_pct = (current_net_worth - previous_net_worth) / abs(previous_net_worth) * 100
        metrics['net_worth_variance'] = round(variance_pct, 4)
        # +10% or more = 100, -10% or more = 0, linear between
        nw_score = _clamp(50 + variance_pct * 5)
        scores.append(nw_score)

    # ── Burn rate + survival runway ──────────
    if expenses is not None and expenses > 0:
        metrics['burn_rate'] = round(expenses, 2)  # daily burn
        if current_capital is not None and current_capital > 0:
            runway_days = current_capital / expenses
            metrics['survival_runway'] = round(runway_days, 1)
            # 365+ days runway = 100, 0 days = 0
            runway_score = _clamp(runway_days / 365 * 100)
            scores.append(runway_score)

    # ── Resilience score ─────────────────────
    if current_capital is not None and expenses is not None and expenses > 0:
        months_survivable = (current_capital / expenses) / 30
        metrics['resilience_score'] = round(months_survivable, 2)

    # ── Emergency penalty ────────────────────
    if emergency_amount is not None and emergency_amount > 0:
        # emergency hits reduce score — scale by severity vs daily income
        if daily_income and daily_income > 0:
            emergency_ratio = emergency_amount / daily_income
            penalty = _clamp(emergency_ratio * 30, 0, 30)
            scores = [max(0, s - penalty) for s in scores]

    # ── Final financial score ────────────────
    if scores:
        financial_score = sum(scores) / len(scores)
    else:
        financial_score = 50.0  # neutral when no financial data logged

    return {
        'score': _clamp(financial_score),
        'metrics': metrics,
        'inputs_logged': len(scores),
    }


# ─────────────────────────────────────────────
#  SUB-ENGINE 2: MENTAL (25%)
# ─────────────────────────────────────────────
def calculate_mental_score(
    mood_score: Optional[int],
    energy_level: Optional[int],
    focus_level: Optional[int],
    social_battery: Optional[int],
    health_battery: Optional[int],
    uncomfortable_moments: Optional[str],
) -> dict:
    """
    Mental engine — scores emotional and cognitive state.

    Weights within mental engine:
        focus_level     35%  — most predictive of productive output
        energy_level    25%  — physical energy drives everything
        mood_score      20%  — emotional baseline
        health_battery  12%  — overall physical feel
        social_battery   8%  — interaction energy (lowest weight)
    """
    weighted_scores = []
    weights = []

    focus = _scale_slider(focus_level)
    if focus is not None:
        weighted_scores.append(focus * 0.35)
        weights.append(0.35)

    energy = _scale_slider(energy_level)
    if energy is not None:
        weighted_scores.append(energy * 0.25)
        weights.append(0.25)

    mood = _scale_slider(mood_score)
    if mood is not None:
        weighted_scores.append(mood * 0.20)
        weights.append(0.20)

    health = _scale_slider(health_battery)
    if health is not None:
        weighted_scores.append(health * 0.12)
        weights.append(0.12)

    social = _scale_slider(social_battery)
    if social is not None:
        weighted_scores.append(social * 0.08)
        weights.append(0.08)

    if not weighted_scores:
        return {'score': 50.0, 'inputs_logged': 0}

    # normalize by actual weights used (handles missing inputs cleanly)
    total_weight = sum(weights)
    mental_score = sum(weighted_scores) / total_weight * 100 / 100

    # bonus: if uncomfortable_moments logged → shows self-awareness (+3)
    if uncomfortable_moments and len(uncomfortable_moments) > 10:
        mental_score = min(100, mental_score + 3)

    return {
        'score': _clamp(mental_score),
        'inputs_logged': len(weighted_scores),
    }


# ─────────────────────────────────────────────
#  SUB-ENGINE 3: EXECUTION (25%)
# ─────────────────────────────────────────────
def calculate_execution_score(
    target_hit_bool: Optional[bool],
    focus_hours: Optional[float],
    screen_time: Optional[float],
    what_i_avoided: Optional[str],
    opportunity_cost: Optional[float],
    tomorrow_goal: Optional[str],
) -> dict:
    """
    Execution engine — scores actual output and discipline.

    Logic:
        - Goal hit → big bonus
        - Focus hours vs screen time ratio → leverage
        - Avoiding tasks → penalty
        - Having tomorrow's goal set → small bonus (planning discipline)
    """
    scores = []
    metrics = {}

    # ── Goal hit (binary — most important execution signal) ──
    if target_hit_bool is not None:
        scores.append(100 if target_hit_bool else 15)

    # ── Focus hours score ────────────────────
    if focus_hours is not None:
        # 8+ hours deep work = 100, 0 = 0, logarithmic feel
        import math
        if focus_hours > 0:
            focus_score = _clamp(min(100, (math.log(focus_hours + 1) / math.log(9)) * 100))
        else:
            focus_score = 0
        scores.append(focus_score)

    # ── Screen time penalty ──────────────────
    if screen_time is not None:
        # 0hrs screen = 100, 12+hrs screen = 0
        screen_score = _clamp(100 - (screen_time / 12 * 100))
        scores.append(screen_score)

    # ── Leverage score (focus vs screen time) ─
    if focus_hours is not None and screen_time is not None and screen_time > 0:
        leverage = focus_hours / screen_time
        metrics['leverage_score'] = round(leverage, 3)

    # ── Procrastination penalty ──────────────
    if what_i_avoided is not None and len(what_i_avoided) > 5:
        # Something was avoided — moderate penalty, but logging it shows awareness
        scores.append(40)  # penalty for avoidance, but not zero (awareness bonus)
        metrics['procrastination_delta'] = 1.0  # flagged as procrastination day
    elif what_i_avoided is not None:
        metrics['procrastination_delta'] = 0.0  # logged but nothing avoided

    # ── Opportunity cost score ───────────────
    if opportunity_cost is not None and focus_hours is not None:
        total_available = focus_hours + opportunity_cost
        if total_available > 0:
            opp_cost_score = opportunity_cost / total_available * 100
            metrics['opportunity_cost_score'] = round(opp_cost_score, 2)

    # ── Planning bonus ───────────────────────
    if tomorrow_goal and len(tomorrow_goal) > 5:
        scores.append(75)  # setting tomorrow's goal = disciplined

    if not scores:
        return {'score': 50.0, 'inputs_logged': 0, 'metrics': metrics}

    return {
        'score': _clamp(sum(scores) / len(scores)),
        'inputs_logged': len(scores),
        'metrics': metrics,
    }


# ─────────────────────────────────────────────
#  SUB-ENGINE 4: BODY (10%)
# ─────────────────────────────────────────────
def calculate_body_score(
    sleep_hours: Optional[float],
    screen_time: Optional[float],
    diet_taken: Optional[str],
) -> dict:
    """
    Body engine — physical health and recovery signals.
    """
    scores = []

    # ── Sleep score (most important body metric) ──
    if sleep_hours is not None:
        if 7 <= sleep_hours <= 9:
            sleep_score = 100  # optimal window
        elif sleep_hours >= 6:
            sleep_score = 70   # acceptable
        elif sleep_hours >= 5:
            sleep_score = 45   # suboptimal
        elif sleep_hours > 0:
            sleep_score = 20   # poor
        else:
            sleep_score = 5    # essentially none
        scores.append(sleep_score)

    # ── Diet logged bonus ────────────────────
    if diet_taken and len(diet_taken) > 5:
        scores.append(70)  # just logging it shows awareness, not judging content yet

    # ── Screen time affects body too ─────────
    if screen_time is not None:
        body_screen_score = _clamp(100 - (screen_time / 16 * 100))
        scores.append(body_screen_score)

    if not scores:
        return {'score': 50.0, 'inputs_logged': 0}

    return {
        'score': _clamp(sum(scores) / len(scores)),
        'inputs_logged': len(scores),
    }


# ─────────────────────────────────────────────
#  SUB-ENGINE 5: GROWTH (10%)
# ─────────────────────────────────────────────
def calculate_growth_score(
    skills_learned: Optional[str],
    new_ideas: Optional[str],
    interactions_done: Optional[str],
    quotes_insights: Optional[str],
    gratitude_line: Optional[str],
    funny_line: Optional[str],
) -> dict:
    """
    Growth engine — knowledge, creativity, and human connection signals.

    Note: These are scored by presence/quality of logging, not content analysis.
    Future versions will use NLP to assess depth of reflection.
    """
    score = 0
    inputs = 0

    if skills_learned and len(skills_learned) > 10:
        score += 30
        inputs += 1

    if new_ideas and len(new_ideas) > 10:
        score += 25
        inputs += 1

    if interactions_done and len(interactions_done) > 5:
        score += 20
        inputs += 1

    if quotes_insights and len(quotes_insights) > 5:
        score += 15
        inputs += 1

    if gratitude_line and len(gratitude_line) > 3:
        score += 5
        inputs += 1

    if funny_line and len(funny_line) > 3:
        score += 5
        inputs += 1

    if inputs == 0:
        return {'score': 50.0, 'inputs_logged': 0}

    # normalize to 100 — max possible is 100 if all logged
    return {
        'score': _clamp(score),
        'inputs_logged': inputs,
    }


# ─────────────────────────────────────────────
#  MASTER VEKTRA SCORE ENGINE
# ─────────────────────────────────────────────
def calculate_vektra_score(snapshot: dict, previous_snapshot: dict = None, current_streak: int = 0) -> VektraScoreResult:
    """
    Master engine — combines all 5 sub-engines into one trajectory score.

    Args:
        snapshot: dict of all current snapshot field values
        previous_snapshot: dict of previous snapshot (for variance calculations)
        current_streak: integer representing user's current daily streak

    Returns:
        VektraScoreResult with master score + all computed metrics
    """
    prev = previous_snapshot or {}

    # ── Run all sub-engines ──────────────────
    financial = calculate_financial_score(
        daily_income=snapshot.get('daily_income'),
        expenses=snapshot.get('expenses'),
        savings_investments=snapshot.get('savings_investments'),
        current_net_worth=snapshot.get('current_net_worth'),
        previous_net_worth=prev.get('current_net_worth'),
        current_capital=snapshot.get('current_capital'),
        emergency_amount=snapshot.get('emergency_amount'),
    )

    mental = calculate_mental_score(
        mood_score=snapshot.get('mood_score'),
        energy_level=snapshot.get('energy_level'),
        focus_level=snapshot.get('focus_level'),
        social_battery=snapshot.get('social_battery'),
        health_battery=snapshot.get('health_battery'),
        uncomfortable_moments=snapshot.get('uncomfortable_moments'),
    )

    execution = calculate_execution_score(
        target_hit_bool=snapshot.get('target_hit_bool'),
        focus_hours=snapshot.get('focus_hours'),
        screen_time=snapshot.get('screen_time'),
        what_i_avoided=snapshot.get('what_i_avoided'),
        opportunity_cost=snapshot.get('opportunity_cost'),
        tomorrow_goal=snapshot.get('tomorrow_goal'),
    )

    body = calculate_body_score(
        sleep_hours=snapshot.get('sleep_hours'),
        screen_time=snapshot.get('screen_time'),
        diet_taken=snapshot.get('diet_taken'),
    )

    growth = calculate_growth_score(
        skills_learned=snapshot.get('skills_learned'),
        new_ideas=snapshot.get('new_ideas'),
        interactions_done=snapshot.get('interactions_done'),
        quotes_insights=snapshot.get('quotes_insights'),
        gratitude_line=snapshot.get('gratitude_line'),
        funny_line=snapshot.get('funny_line'),
    )

    # ── Weighted master score ────────────────
    weights = {
        'financial': 0.30,
        'mental':    0.25,
        'execution': 0.25,
        'body':      0.10,
        'growth':    0.10,
    }

    master_score = (
        financial['score'] * weights['financial'] +
        mental['score']    * weights['mental']    +
        execution['score'] * weights['execution'] +
        body['score']      * weights['body']      +
        growth['score']    * weights['growth']
    )

    # ── Streak Momentum Bonus (Scale-up viral feature) ──
    # Every day in streak gives +1% bonus up to max +20% (multiplier of 1.20)
    streak_bonus_multiplier = min(1.0 + (current_streak * 0.01), 1.20)
    master_score *= streak_bonus_multiplier

    # ── Confidence score ─────────────────────
    # How many sub-engines had real data? Affects how much we trust the score.
    engines_with_data = sum([
        financial['inputs_logged'] > 0,
        mental['inputs_logged'] > 0,
        execution['inputs_logged'] > 0,
        body['inputs_logged'] > 0,
        growth['inputs_logged'] > 0,
    ])
    confidence = engines_with_data / 5

    # ── Collect all computed metrics ─────────
    all_metrics = {}
    all_metrics.update(financial.get('metrics', {}))
    all_metrics.update(execution.get('metrics', {}))

    result = VektraScoreResult(
        financial_score=round(financial['score'], 2),
        mental_score=round(mental['score'], 2),
        execution_score=round(execution['score'], 2),
        body_score=round(body['score'], 2),
        growth_score=round(growth['score'], 2),
        vektra_score=round(_clamp(master_score), 2),
        confidence=round(confidence, 2),
        burn_rate=all_metrics.get('burn_rate'),
        net_worth_variance=all_metrics.get('net_worth_variance'),
        resilience_score=all_metrics.get('resilience_score'),
        survival_runway=all_metrics.get('survival_runway'),
        procrastination_delta=all_metrics.get('procrastination_delta'),
        leverage_score=all_metrics.get('leverage_score'),
        system_leak=all_metrics.get('system_leak'),
        opportunity_cost_score=all_metrics.get('opportunity_cost_score'),
    )
    result.coaching_tip = get_coaching_tip(result)
    return result


# ─────────────────────────────────────────────
#  QUICK TEST — run this file directly to verify
# ─────────────────────────────────────────────
if __name__ == "__main__":
    test_snapshot = {
        'mood_score': 8,
        'energy_level': 7,
        'focus_level': 9,
        'social_battery': 6,
        'health_battery': 7,
        'sleep_hours': 7.5,
        'daily_income': 500,
        'expenses': 200,
        'savings_investments': 150,
        'current_capital': 15000,
        'focus_hours': 4.5,
        'screen_time': 3.0,
        'target_hit_bool': True,
        'tomorrow_goal': 'Finish CSS navigation component',
        'skills_learned': 'Learned logarithmic discount curves and JS event listeners',
        'new_ideas': 'Real time FX conversion for net worth display',
        'gratitude_line': 'Grateful for the math brain God gave me',
        'funny_line': 'Elsy still has me saved as Roophy (elvis)',
    }

    result = calculate_vektra_score(test_snapshot, current_streak=5)

    print("\n" + "="*50)
    print("  VEKTRA SCORE ENGINE — TEST RUN (With 5-Day Streak)")
    print("="*50)
    print(f"  Financial score:  {result.financial_score}/100")
    print(f"  Mental score:     {result.mental_score}/100")
    print(f"  Execution score:  {result.execution_score}/100")
    print(f"  Body score:       {result.body_score}/100")
    print(f"  Growth score:     {result.growth_score}/100")
    print(f"  {'='*30}")
    print(f"  VEKTRA SCORE:     {result.vektra_score}/100")
    print(f"  Summary:          {result.shareable_summary}")
    print(f"  Viral Caption:    {result.viral_caption}")
    print(f"  Coach Tip:        {result.coaching_tip}")
    print(f"  Confidence:       {result.confidence*100:.0f}%")
    print(f"\n  Computed metrics:")
    print(f"  Burn rate:        {result.burn_rate}")
    print(f"  Survival runway:  {result.survival_runway} days")
    print(f"  Leverage score:   {result.leverage_score}")
    print(f"  Resilience:       {result.resilience_score} months")
    print("="*50)
