"""
VEKTRA Score Engine — V2.0 Production
======================================
Calculates the master VEKTRA trajectory score (0-100) from a daily snapshot.

Architecture:
    5 sub-engines → weighted combination → master score

Sub-engines:
    Financial   30%  — cash flow, savings, net worth, runway
    Mental      25%  — mood, energy, focus, social/health battery
    Execution   25%  — goals, focus hours, procrastination, screen time
    Body        10%  — sleep, diet, health
    Growth      10%  — skills, ideas, interactions, quotes

Key improvements in V2:
    - Weighted pillars inside each sub-engine (fixed weights, no variable averaging)
    - Anti-gaming: text entropy checks prevent spam inputs
    - Tier-aware: free/tier1/tier2 get different calculation depths
    - Emergency penalty against capital not income
    - Net worth variance dampened for small balances
    - Geometric mean option for tier2 (punishes imbalanced engines)
    - Shadow score shows unrealized potential
    - Coaching tips based on anomaly detection
"""

import math
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


# ─────────────────────────────────────────────
#  RESULT CONTAINER
# ─────────────────────────────────────────────
@dataclass
class VektraScoreResult:
    """All computed scores returned by the engine."""
    financial_score: float = 50.0
    mental_score: float = 50.0
    execution_score: float = 50.0
    body_score: float = 50.0
    growth_score: float = 50.0

    vektra_score: float = 50.0
    shadow_score: float = 50.0
    confidence: float = 1.0

    burn_rate: Optional[float] = None
    net_worth_variance: Optional[float] = None
    resilience_score: Optional[float] = None
    survival_runway: Optional[float] = None
    procrastination_delta: Optional[float] = None
    leverage_score: Optional[float] = None
    system_leak: Optional[float] = None
    opportunity_cost_score: Optional[float] = None

    coaching_tip: Optional[str] = None
    system_flags: List[str] = field(default_factory=list)

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
            return f"I just hit {self.vektra_score} on VEKTRA while you were scrolling. We are not the same. 📈"
        elif self.vektra_score >= 70:
            return f"VEKTRA score: {self.vektra_score}. Building in silence. 🏛️"
        elif self.vektra_score >= 50:
            return f"Hit {self.vektra_score}/100 on VEKTRA today. Consistency beats talent. 🛠️"
        else:
            return f"Reset day ({self.vektra_score}/100). Recalibrating trajectory. ⚙️"


# ─────────────────────────────────────────────
#  CORE UTILITIES
# ─────────────────────────────────────────────
def _clamp(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    return max(min_val, min(max_val, value))


def _scale_slider(value: Optional[int]) -> Optional[float]:
    """Convert 1-10 slider to 0-100 score."""
    if value is None:
        return None
    return _clamp((value - 1) / 9 * 100)


def _text_entropy(text: Optional[str]) -> float:
    """
    Shannon entropy check to prevent spam/gaming.
    Returns 0.0 for empty/repetitive text, higher for genuine reflection.
    'banana banana banana' scores ~1.0
    A real sentence scores 3.5+
    """
    if not text or len(text.strip()) < 8:
        return 0.0
    clean = text.strip().lower()
    words = clean.split()
    if len(words) < 2:
        return 0.0
    # Lexical diversity check
    diversity = len(set(words)) / len(words)
    if diversity < 0.35:
        return 0.5  # Repetitive — penalized
    # Shannon entropy on characters
    freq: Dict[str, int] = {}
    for ch in clean:
        freq[ch] = freq.get(ch, 0) + 1
    entropy = 0.0
    total = len(clean)
    for count in freq.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def _text_is_genuine(text: Optional[str], min_entropy: float = 2.8) -> bool:
    """Returns True if text passes anti-gaming check."""
    return _text_entropy(text) >= min_entropy


def _geometric_mean(scores: List[float]) -> float:
    """Geometric mean — punishes imbalanced engines heavily."""
    cleaned = [max(1.0, s) for s in scores]
    return math.exp(sum(math.log(s) for s in cleaned) / len(cleaned))


# ─────────────────────────────────────────────
#  SUB-ENGINE 1: FINANCIAL (30%)
# ─────────────────────────────────────────────
def calculate_financial_score(
    daily_income: Optional[float],
    expenses: Optional[float],
    savings_investments: Optional[float],
    current_net_worth: Optional[float],
    previous_net_worth: Optional[float],
    current_capital: Optional[float],
    emergency_amount: Optional[float],
    any_emergency: Optional[str] = None,
    user_tier: str = 'free',
) -> dict:
    """
    Financial engine with 4 fixed-weight pillars:
        Cash Flow      40%
        Savings        25%
        Net Worth      20%
        Runway         15%
    Emergency penalty applied against capital (not income).
    """
    metrics = {}
    flags = []

    # ── Pillar 1: Cash Flow (40%) ─────────────────────────
    income = max(0.0, daily_income) if daily_income is not None else None
    exp = max(0.0, expenses) if expenses is not None else None
    capital = max(0.0, current_capital) if current_capital is not None else 0.0

    if income is not None and exp is not None:
        if income == 0 and exp == 0:
            cf_score = 50.0
        elif income > 0:
            flow_ratio = (income - exp) / income
            cf_score = _clamp((flow_ratio + 1) / 2 * 100)
            # Magnitude anchor: tiny income shouldn't score perfectly
            magnitude_factor = _clamp(income / 300.0, 0.2, 1.0)
            cf_score = cf_score * magnitude_factor + 50 * (1 - magnitude_factor)
        else:
            # Expenses with zero income — check capital buffer
            if capital > 0:
                danger_ratio = exp / capital
                cf_score = _clamp(40.0 - (danger_ratio * 100.0))
                if danger_ratio > 0.1:
                    flags.append('CAPITAL_BLEED')
            else:
                cf_score = 5.0
                flags.append('NO_INCOME_NO_CAPITAL')
    else:
        cf_score = 50.0  # No data — neutral

    # ── Pillar 2: Savings Discipline (25%) ────────────────
    if savings_investments is not None and income is not None and income > 0:
        savings_ratio = savings_investments / income
        # Non-linear: 30% savings = 75, 67% = 100, over 100% = capped
        sv_score = _clamp((1.0 - math.exp(-savings_ratio * 2.5)) * 115)
    elif savings_investments is not None and savings_investments > 0 and capital > 0:
        sv_score = 70.0  # Saving from capital reserves — credit
    else:
        sv_score = 0.0 if (income is not None and income > 0) else 50.0

    # ── Pillar 3: Net Worth Direction (20%) ───────────────
    if current_net_worth is not None and previous_net_worth is not None and previous_net_worth != 0:
        raw_variance = (current_net_worth - previous_net_worth) / abs(previous_net_worth) * 100
        metrics['net_worth_variance'] = round(raw_variance, 4)
        # Dampen percentage swings for small balances
        balance_scale = _clamp(math.log10(max(10.0, abs(previous_net_worth))) / 5.0, 0.1, 1.0)
        adjusted_variance = raw_variance * balance_scale
        nw_score = _clamp(50.0 + adjusted_variance * 4.0)
    else:
        nw_score = 50.0

    # ── Pillar 4: Survival Runway (15%) ───────────────────
    if exp is not None and exp > 0:
        metrics['burn_rate'] = round(exp, 2)
        if capital > 0:
            runway_days = capital / exp
            metrics['survival_runway'] = round(runway_days, 1)
            metrics['resilience_score'] = round(runway_days / 30.4, 2)
            # Logarithmic runway score: 365 days = 100, 30 days = 50, 0 = 0
            rw_score = _clamp((math.log10(max(1.0, runway_days)) / math.log10(365.0)) * 100.0)
        else:
            rw_score = 0.0
            flags.append('ZERO_RUNWAY')
            metrics['survival_runway'] = 0.0
            metrics['resilience_score'] = 0.0
    else:
        rw_score = 50.0  # No expenses logged — neutral

    # ── Leverage score ─────────────────────────────────────
    if income is not None and exp is not None and exp > 0:
        metrics['leverage_score'] = round(income / exp, 2)

    # ── Emergency penalty against capital ─────────────────
    emergency_penalty = 0.0
    if emergency_amount is not None and emergency_amount > 0:
        if capital > 0:
            risk_ratio = emergency_amount / capital
            emergency_penalty = _clamp(risk_ratio * 60.0, 0.0, 40.0)
        else:
            emergency_penalty = 35.0
        flags.append('EMERGENCY_HIT')
    elif any_emergency and _text_is_genuine(any_emergency):
        emergency_penalty = 8.0  # Text emergency with no amount — small signal

    # ── Weighted composite ─────────────────────────────────
    raw_score = (
        cf_score * 0.40 +
        sv_score * 0.25 +
        nw_score * 0.20 +
        rw_score * 0.15
    )
    final_score = _clamp(raw_score - emergency_penalty)

    inputs = sum([
        daily_income is not None,
        expenses is not None,
        current_net_worth is not None,
    ])

    return {
        'score': round(final_score, 2),
        'metrics': metrics,
        'flags': flags,
        'inputs_logged': inputs,
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
    user_tier: str = 'free',
) -> dict:
    """
    Mental engine — weighted slider composite.
    Focus is weighted at 20% here (not 35%) to avoid double-counting with Execution.
    Imbalance between metrics triggers a small penalty.
    """
    flags = []
    weighted = []
    weights = []

    mood   = _scale_slider(mood_score)
    energy = _scale_slider(energy_level)
    focus  = _scale_slider(focus_level)
    health = _scale_slider(health_battery)
    social = _scale_slider(social_battery)

    W = {'mood': 0.30, 'energy': 0.25, 'focus': 0.20, 'health': 0.15, 'social': 0.10}

    sliders = []
    for val, key in [(mood, 'mood'), (energy, 'energy'), (focus, 'focus'),
                     (health, 'health'), (social, 'social')]:
        if val is not None:
            weighted.append(val * W[key])
            weights.append(W[key])
            sliders.append(val)

    if not weighted:
        return {'score': 50.0, 'inputs_logged': 0, 'flags': []}

    base = sum(weighted) / sum(weights)

    # Imbalance penalty: high variance between slider values
    if len(sliders) >= 3:
        mean = sum(sliders) / len(sliders)
        std = math.sqrt(sum((x - mean) ** 2 for x in sliders) / len(sliders))
        if std > 25.0:
            imbalance_penalty = (std - 25.0) * 0.3
            base = max(0.0, base - imbalance_penalty)
            flags.append('MENTAL_IMBALANCE')

    # Self-awareness bonus for genuine reflection
    if _text_is_genuine(uncomfortable_moments):
        base = min(100.0, base + 4.0)

    return {
        'score': round(_clamp(base), 2),
        'inputs_logged': len(weighted),
        'flags': flags,
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
    user_tier: str = 'free',
    current_streak: int = 0,
) -> dict:
    """
    Execution engine — 4 fixed-weight pillars:
        Outcome        40%
        Effort         35%
        Discipline     15%
        Efficiency     10%
    """
    metrics = {}
    flags = []

    f_hrs = max(0.0, focus_hours) if focus_hours is not None else 0.0
    scr = max(0.0, screen_time) if screen_time is not None else 0.0
    opp = max(0.0, opportunity_cost) if opportunity_cost is not None else 0.0

    # ── Pillar 1: Outcome (40%) ───────────────────────────
    if target_hit_bool is not None:
        outcome = 100.0 if target_hit_bool else 15.0
        # Streak bonus on success
        if target_hit_bool and current_streak > 0:
            outcome = min(100.0, outcome + current_streak * 0.5)
    else:
        outcome = 50.0

    # ── Pillar 2: Effort — focus hours (35%) ──────────────
    if f_hrs > 0:
        effort = _clamp((math.log(f_hrs + 1) / math.log(9)) * 100)
        # Opportunity cost dilutes effort
        if opp > 0:
            total = f_hrs + opp
            dilution = f_hrs / total
            effort = effort * dilution
            metrics['opportunity_cost_score'] = round((opp / total) * 100, 2)
    else:
        effort = 0.0

    # ── Pillar 3: Discipline (15%) ────────────────────────
    discipline_parts = []
    if what_i_avoided is not None:
        if _text_is_genuine(what_i_avoided):
            discipline_parts.append(35.0)  # Real avoidance logged — penalty
            metrics['procrastination_delta'] = 1.0
            flags.append('PROCRASTINATION_LOGGED')
        else:
            discipline_parts.append(100.0)  # Nothing avoided
            metrics['procrastination_delta'] = 0.0
    else:
        metrics['procrastination_delta'] = 0.0

    if tomorrow_goal and _text_is_genuine(tomorrow_goal, min_entropy=2.0):
        discipline_parts.append(90.0)  # Planning discipline credit
    elif tomorrow_goal and len(tomorrow_goal) > 5:
        discipline_parts.append(75.0)

    discipline = sum(discipline_parts) / len(discipline_parts) if discipline_parts else 50.0

    # ── Pillar 4: Efficiency — focus vs screen time (10%) ─
    if scr > 0:
        leverage = f_hrs / scr if f_hrs > 0 else 0.0
        metrics['leverage_score'] = round(leverage, 3)
        efficiency = _clamp(leverage * 100)
        if leverage < 0.25:
            flags.append('LOW_FOCUS_RATIO')
    elif f_hrs > 0:
        efficiency = 100.0  # Pure focus, no distracting screen
    else:
        efficiency = 50.0

    # ── System leak ────────────────────────────────────────
    target_focus = 6.0  # Ideal deep work hours
    metrics['system_leak'] = round(max(0.0, target_focus - f_hrs), 2)

    raw = (
        outcome    * 0.40 +
        effort     * 0.35 +
        discipline * 0.15 +
        efficiency * 0.10
    )

    inputs = sum([target_hit_bool is not None, focus_hours is not None, screen_time is not None])

    return {
        'score': round(_clamp(raw), 2),
        'metrics': metrics,
        'flags': flags,
        'inputs_logged': inputs,
    }


# ─────────────────────────────────────────────
#  SUB-ENGINE 4: BODY (10%)
# ─────────────────────────────────────────────
def calculate_body_score(
    sleep_hours: Optional[float],
    diet_taken: Optional[str],
    health_battery: Optional[int],
    screen_time: Optional[float] = None,
    user_tier: str = 'free',
) -> dict:
    """
    Body engine — physical recovery and health signals.
    Sleep uses a parabolic curve centered at 8 hours.
    """
    flags = []
    parts = []
    weights = []

    # ── Sleep (50%) ────────────────────────────────────────
    if sleep_hours is not None:
        s = max(0.0, sleep_hours)
        if 7.0 <= s <= 9.0:
            sleep_score = 100.0
        elif 6.0 <= s < 7.0 or 9.0 < s <= 10.0:
            sleep_score = 75.0
        elif 5.0 <= s < 6.0:
            sleep_score = 45.0
            flags.append('LOW_SLEEP')
        elif s > 0:
            sleep_score = 15.0
            flags.append('CRITICAL_SLEEP_DEBT')
        else:
            sleep_score = 5.0
        parts.append(sleep_score * 0.50)
        weights.append(0.50)

    # ── Health battery (30%) ───────────────────────────────
    health = _scale_slider(health_battery)
    if health is not None:
        parts.append(health * 0.30)
        weights.append(0.30)

    # ── Diet (15%) ─────────────────────────────────────────
    if diet_taken and len(diet_taken.strip()) > 5:
        clean = diet_taken.lower()
        toxic = ['soda', 'fries', 'pizza', 'burger', 'beer', 'alcohol', 'junk', 'chips', 'sugar']
        fuel  = ['chicken', 'rice', 'eggs', 'greens', 'vegetables', 'fruit', 'protein', 'oats', 'fish', 'water']
        tox_hits  = sum(1 for t in toxic if t in clean)
        fuel_hits = sum(1 for f in fuel  if f in clean)
        diet_score = _clamp(60.0 + fuel_hits * 10.0 - tox_hits * 15.0, 10.0, 100.0)
        parts.append(diet_score * 0.15)
        weights.append(0.15)

    # ── Screen time effect on body (5%) ───────────────────
    if screen_time is not None:
        body_screen = _clamp(100 - (screen_time / 16 * 100))
        parts.append(body_screen * 0.05)
        weights.append(0.05)

    if not parts:
        return {'score': 50.0, 'inputs_logged': 0, 'flags': []}

    total_weight = sum(weights)
    score = sum(parts) / total_weight

    return {
        'score': round(_clamp(score), 2),
        'inputs_logged': len(parts),
        'flags': flags,
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
    user_tier: str = 'free',
) -> dict:
    """
    Growth engine — knowledge, creativity, connection signals.
    Anti-gaming: text entropy filters block spam entries.
    Free tier: binary (logged or not).
    Tier1/2: quality-weighted by entropy score.
    """
    flags = []
    score = 0.0
    inputs = 0

    fields = [
        (skills_learned,    30.0, 2.8, 'skills'),
        (new_ideas,         25.0, 2.8, 'ideas'),
        (interactions_done, 20.0, 2.5, 'social'),
        (quotes_insights,   15.0, 2.5, 'quotes'),
        (gratitude_line,     5.0, 2.0, 'gratitude'),
        (funny_line,         5.0, 1.5, 'funny'),
    ]

    for text, max_pts, min_ent, label in fields:
        if not text or len(text.strip()) < 4:
            continue
        inputs += 1
        entropy = _text_entropy(text)
        if user_tier == 'free':
            score += max_pts  # Binary: logged = full points
        else:
            if entropy >= min_ent:
                score += max_pts  # Genuine reflection — full points
            elif entropy > 0.5:
                score += max_pts * 0.4  # Low quality — partial
            else:
                score += max_pts * 0.1  # Spam detected
                flags.append(f'GROWTH_SPAM_{label.upper()}')

    if inputs == 0:
        return {'score': 50.0, 'inputs_logged': 0, 'flags': []}

    # Saturation: bonus for logging multiple fields
    saturation = 1.0 if inputs >= 4 else (0.5 + inputs * 0.125)
    final = _clamp(score * saturation)

    return {
        'score': round(final, 2),
        'inputs_logged': inputs,
        'flags': flags,
    }


# ─────────────────────────────────────────────
#  COACHING ENGINE
# ─────────────────────────────────────────────
def get_coaching_tip(
    result: 'VektraScoreResult',
    flags: List[str],
) -> str:
    if 'CRITICAL_SLEEP_DEBT' in flags:
        return "CRITICAL: Sleep debt is collapsing your cognitive function. Everything else suffers. Fix sleep first."
    if 'ZERO_RUNWAY' in flags:
        return "FINANCIAL EMERGENCY: Zero survival runway. Freeze all non-essential spending immediately."
    if 'CAPITAL_BLEED' in flags:
        return "CAPITAL BLEED ALERT: Expenses are eating into your reserves. Find one income source today."
    if 'LOW_FOCUS_RATIO' in flags:
        return "DOOMSCROLL DETECTED: Screen time overwhelms focus hours. Close all tabs and lock in."
    if result.execution_score < 40:
        return "Execution has collapsed. Pick ONE task for tomorrow and protect it like your life depends on it."
    if result.financial_score < 40:
        return "Financial engine weak. Review daily burn rate and find the leak."
    if result.mental_score < 50:
        return "Mental battery low. 30 minutes of intentional rest before sleep. No screens."
    if result.vektra_score >= 80:
        return "You are in the zone. Protect the routine. Scale the output."
    return "Identify your weakest engine. One focused improvement compounds everything else."


# ─────────────────────────────────────────────
#  MASTER VEKTRA SCORE ENGINE
# ─────────────────────────────────────────────
def calculate_vektra_score(
    snapshot: dict,
    previous_snapshot: dict = None,
    current_streak: int = 0,
    user_tier: str = 'free',
) -> VektraScoreResult:
    """
    Master engine — combines all 5 sub-engines into one trajectory score.

    Free tier:   Arithmetic mean of 5 engines
    Tier 1:      Arithmetic mean + streak bonus
    Tier 2:      70% Geometric Mean + 30% Arithmetic Mean (punishes imbalance)
                 + streak bonus + cross-engine penalties
    """
    prev = previous_snapshot or {}
    all_flags = []

    # ── Run all sub-engines ──────────────────────────────
    financial = calculate_financial_score(
        daily_income=snapshot.get('daily_income'),
        expenses=snapshot.get('expenses'),
        savings_investments=snapshot.get('savings_investments'),
        current_net_worth=snapshot.get('current_net_worth'),
        previous_net_worth=prev.get('current_net_worth'),
        current_capital=snapshot.get('current_capital'),
        emergency_amount=snapshot.get('emergency_amount'),
        any_emergency=snapshot.get('any_emergency'),
        user_tier=user_tier,
    )

    mental = calculate_mental_score(
        mood_score=snapshot.get('mood_score'),
        energy_level=snapshot.get('energy_level'),
        focus_level=snapshot.get('focus_level'),
        social_battery=snapshot.get('social_battery'),
        health_battery=snapshot.get('health_battery'),
        uncomfortable_moments=snapshot.get('uncomfortable_moments'),
        user_tier=user_tier,
    )

    execution = calculate_execution_score(
        target_hit_bool=snapshot.get('target_hit_bool'),
        focus_hours=snapshot.get('focus_hours'),
        screen_time=snapshot.get('screen_time'),
        what_i_avoided=snapshot.get('what_i_avoided'),
        opportunity_cost=snapshot.get('opportunity_cost'),
        tomorrow_goal=snapshot.get('tomorrow_goal'),
        user_tier=user_tier,
        current_streak=current_streak,
    )

    body = calculate_body_score(
        sleep_hours=snapshot.get('sleep_hours'),
        diet_taken=snapshot.get('diet_taken'),
        health_battery=snapshot.get('health_battery'),
        screen_time=snapshot.get('screen_time'),
        user_tier=user_tier,
    )

    growth = calculate_growth_score(
        skills_learned=snapshot.get('skills_learned'),
        new_ideas=snapshot.get('new_ideas'),
        interactions_done=snapshot.get('interactions_done'),
        quotes_insights=snapshot.get('quotes_insights'),
        gratitude_line=snapshot.get('gratitude_line'),
        funny_line=snapshot.get('funny_line'),
        user_tier=user_tier,
    )

    # Collect all flags
    for eng in [financial, mental, execution, body, growth]:
        all_flags.extend(eng.get('flags', []))

    # ── Weights ──────────────────────────────────────────
    W = {
        'financial': 0.30,
        'mental':    0.25,
        'execution': 0.25,
        'body':      0.10,
        'growth':    0.10,
    }

    scores = [
        financial['score'],
        mental['score'],
        execution['score'],
        body['score'],
        growth['score'],
    ]

    # ── Master score calculation ─────────────────────────
    arithmetic = sum(s * w for s, w in zip(scores, W.values()))

    if user_tier == 'tier2':
        # 70% Geometric + 30% Arithmetic for Tier 2
        geo = _geometric_mean(scores)
        master = geo * 0.70 + arithmetic * 0.30
    else:
        master = arithmetic

    # ── Cross-engine penalties (tier1+) ─────────────────
    if user_tier in ['tier1', 'tier2']:
        if body['score'] < 40:
            master *= 0.93  # Physical drag on output
            all_flags.append('PHYSIOLOGICAL_DRAG')
        if financial['score'] < 35:
            master *= 0.96  # Financial stress dampener
            all_flags.append('FINANCIAL_STRESS')

    # ── Streak bonus (capped at +5 points) ───────────────
    streak_bonus = min(5.0, current_streak * 0.25)
    master = _clamp(master + streak_bonus)

    # ── Shadow score (unrealized potential) ──────────────
    # What you could score if execution was at 100%
    shadow = _clamp(
        financial['score'] * W['financial'] +
        mental['score']    * W['mental']    +
        100.0              * W['execution'] +  # Max execution
        body['score']      * W['body']      +
        growth['score']    * W['growth']    +
        streak_bonus
    )
    if shadow <= master:
        shadow = min(100.0, master + 5.0)

    # ── Confidence ────────────────────────────────────────
    engines_with_data = sum([
        financial['inputs_logged'] > 0,
        mental['inputs_logged'] > 0,
        execution['inputs_logged'] > 0,
        body['inputs_logged'] > 0,
        growth['inputs_logged'] > 0,
    ])
    confidence = engines_with_data / 5.0

    # ── Collect metrics ───────────────────────────────────
    all_metrics = {}
    all_metrics.update(financial.get('metrics', {}))
    all_metrics.update(execution.get('metrics', {}))

    result = VektraScoreResult(
        financial_score=round(financial['score'], 2),
        mental_score=round(mental['score'], 2),
        execution_score=round(execution['score'], 2),
        body_score=round(body['score'], 2),
        growth_score=round(growth['score'], 2),
        vektra_score=round(master, 2),
        shadow_score=round(shadow, 2),
        confidence=round(confidence, 2),
        burn_rate=all_metrics.get('burn_rate'),
        net_worth_variance=all_metrics.get('net_worth_variance'),
        resilience_score=all_metrics.get('resilience_score'),
        survival_runway=all_metrics.get('survival_runway'),
        procrastination_delta=all_metrics.get('procrastination_delta'),
        leverage_score=all_metrics.get('leverage_score'),
        system_leak=all_metrics.get('system_leak'),
        opportunity_cost_score=all_metrics.get('opportunity_cost_score'),
        system_flags=list(set(all_flags)),
    )
    result.coaching_tip = get_coaching_tip(result, all_flags)
    return result


# ─────────────────────────────────────────────
#  TEST RUN
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
        'current_net_worth': 15500,
        'focus_hours': 4.5,
        'screen_time': 3.0,
        'target_hit_bool': True,
        'tomorrow_goal': 'Finish the VEKTRA engine and deploy to production',
        'skills_learned': 'Learned logarithmic discount curves and weighted pillar scoring systems',
        'new_ideas': 'Real time FX conversion for net worth display across currencies',
        'gratitude_line': 'Grateful for the mathematical brain God gave me',
        'funny_line': 'Hotel lady gave me free food and saved the day',
        'uncomfortable_moments': 'Jehovah witnesses interrupted my deployment session',
        'what_i_avoided': None,
    }

    prev = {'current_net_worth': 15000}

    for tier in ['free', 'tier1', 'tier2']:
        result = calculate_vektra_score(test_snapshot, prev, current_streak=5, user_tier=tier)
        print(f"\n{'='*55}")
        print(f"  VEKTRA ENGINE V2.0 — TIER: {tier.upper()}")
        print(f"{'='*55}")
        print(f"  Financial:   {result.financial_score}/100")
        print(f"  Mental:      {result.mental_score}/100")
        print(f"  Execution:   {result.execution_score}/100")
        print(f"  Body:        {result.body_score}/100")
        print(f"  Growth:      {result.growth_score}/100")
        print(f"  {'─'*40}")
        print(f"  VEKTRA:      {result.vektra_score}/100")
        print(f"  SHADOW:      {result.shadow_score}/100")
        print(f"  Confidence:  {result.confidence*100:.0f}%")
        print(f"  Flags:       {result.system_flags}")
        print(f"  Coach:       {result.coaching_tip}")
        print(f"  Summary:     {result.shareable_summary}")