"""
VEKTRA Report Insights
======================
Pure analytics over a period of snapshots — no DB, no AI. Everything a
report says is computed here first, so the AI narrative and the zero-cost
template both stand on the same real numbers, and every claim on screen
can be traced back to what the user logged.
"""

import datetime
import statistics
from typing import Dict, List, Optional

from app.services.vektra_engine import calculate_vektra_score

ENGINE_NAMES = ["Financial", "Mental", "Execution", "Body", "Growth"]
ENGINE_WEIGHTS = {"Financial": 0.25, "Mental": 0.2, "Execution": 0.2, "Body": 0.2, "Growth": 0.15}

# Inputs each engine reads. A day only counts toward an engine's average if
# the user actually logged one of these, so an empty money section shows as
# "no data" instead of the engine's neutral default dressed up as a score.
ENGINE_INPUTS = {
    "Financial": ("daily_income", "expenses", "savings_investments", "current_net_worth", "any_emergency"),
    "Mental": ("mood_score", "energy_level", "focus_level", "social_battery", "health_battery"),
    "Execution": ("target_hit_bool", "focus_hours", "tomorrow_goal", "what_i_avoided"),
    "Body": ("sleep_hours", "diet_taken", "health_battery"),
    "Growth": ("skills_learned", "new_ideas", "interactions_done", "quotes_insights", "gratitude_line"),
}

# Candidate levers for "what drives your score": (field, label, unit, phrasing)
DRIVER_FACTORS = [
    ("sleep_hours", "sleep", "h", "slept {v}"),
    ("screen_time", "screen time", "h", "had {v} of screen time"),
    ("focus_hours", "deep work", "h", "did {v} of deep work"),
    ("energy_level", "energy", "/10", "rated energy {v}"),
    ("social_battery", "social battery", "/10", "rated social battery {v}"),
    ("environment_rating", "environment", "/10", "rated your environment {v}"),
]

SNAPSHOT_FIELDS = sorted({f for fields in ENGINE_INPUTS.values() for f in fields} | {
    "screen_time", "opportunity_cost", "uncomfortable_moments", "emergency_amount",
    "current_capital", "funny_line", "environment_rating", "vektra_score",
})

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _avg(values) -> Optional[float]:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 1) if clean else None


def _has(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _day_of(snapshot) -> Optional[datetime.date]:
    log_date = getattr(snapshot, "log_date", None)
    if log_date:
        return log_date
    ts = getattr(snapshot, "timestamp", None)
    return ts.date() if ts else None


def _fmt(value: float, unit: str) -> str:
    if unit == "h":
        return f"{value:g}h"
    if unit == "/10":
        return f"{value:g}/10"
    return f"{value:g}"


def daily_rows(snapshots) -> List[dict]:
    """One row per logged day (latest entry wins), oldest first."""
    by_day: Dict[datetime.date, object] = {}
    for s in sorted(snapshots, key=lambda s: getattr(s, "timestamp", None) or datetime.datetime.min):
        day = _day_of(s)
        if day is not None:
            by_day[day] = s
    rows = []
    for day in sorted(by_day):
        s = by_day[day]
        row = {f: getattr(s, f, None) for f in SNAPSHOT_FIELDS}
        row["date"] = day
        rows.append(row)
    return rows


def engine_breakdown(rows: List[dict]) -> Dict[str, dict]:
    """Average of each day's engine score, only over days with that engine's inputs."""
    per_engine = {name: [] for name in ENGINE_NAMES}
    for row in rows:
        result = calculate_vektra_score(row)
        scores = {
            "Financial": result.financial_score, "Mental": result.mental_score,
            "Execution": result.execution_score, "Body": result.body_score,
            "Growth": result.growth_score,
        }
        for name, inputs in ENGINE_INPUTS.items():
            if any(_has(row.get(f)) for f in inputs):
                per_engine[name].append(scores[name])

    n = len(rows)
    income = sum(r["daily_income"] or 0 for r in rows)
    spent = sum(r["expenses"] or 0 for r in rows)
    emergencies = sum(1 for r in rows if r.get("any_emergency"))
    goals_set = sum(1 for r in rows if _has(r.get("tomorrow_goal")))
    goals_hit = sum(1 for r in rows if r.get("target_hit_bool") is True)
    growth_days = sum(1 for r in rows if any(_has(r.get(f)) for f in ("skills_learned", "new_ideas")))

    details = {
        "Financial": (
            (f"Kept {round((income - spent) / income * 100)}% of what came in" if income >= spent
             else f"Spent {round((spent - income) / income * 100)}% more than came in")
            if income > 0 else "No income logged" if spent else ""
        ) + (f" · {emergencies} emergenc{'y' if emergencies == 1 else 'ies'}" if emergencies else ""),
        "Mental": " · ".join(p for p in [
            f"Mood {_avg(r['mood_score'] for r in rows)}" if _avg(r['mood_score'] for r in rows) is not None else "",
            f"Energy {_avg(r['energy_level'] for r in rows)}" if _avg(r['energy_level'] for r in rows) is not None else "",
            f"Focus {_avg(r['focus_level'] for r in rows)}" if _avg(r['focus_level'] for r in rows) is not None else "",
        ] if p),
        "Execution": " · ".join(p for p in [
            f"Hit {goals_hit}/{goals_set} goals" if goals_set else "",
            f"{_avg(r['focus_hours'] for r in rows)}h deep work/day" if _avg(r['focus_hours'] for r in rows) is not None else "",
        ] if p),
        "Body": " · ".join(p for p in [
            f"Sleep {_avg(r['sleep_hours'] for r in rows)}h" if _avg(r['sleep_hours'] for r in rows) is not None else "",
            f"Screen {_avg(r['screen_time'] for r in rows)}h/day" if _avg(r['screen_time'] for r in rows) is not None else "",
        ] if p),
        "Growth": f"Learned or built something on {growth_days} of {n} days" if n else "",
    }
    return {
        name: {
            "score": round(sum(vals) / len(vals)) if vals else None,
            "days": len(vals),
            "detail": details[name].strip(" ·") or "Nothing logged here yet",
        }
        for name, vals in per_engine.items()
    }


def trend(rows: List[dict], period_days: int = 7) -> Optional[dict]:
    """Direction of the score inside the period, plus where next period lands at this pace.

    The projection uses half the fitted slope and moves at most 15 points:
    a week of daily scores is too noisy to extrapolate at full strength.
    """
    points = [(r["date"], r["vektra_score"]) for r in rows if r.get("vektra_score") is not None]
    if len(points) < 4:
        return None
    half = len(points) // 2
    first = sum(s for _, s in points[:half]) / half
    second = sum(s for _, s in points[half:]) / (len(points) - half)
    delta = round(second - first, 1)

    origin = points[0][0]
    xs = [(d - origin).days for d, _ in points]
    ys = [s for _, s in points]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var_x if var_x else 0.0
    current = sum(ys) / len(ys)
    change = max(-15.0, min(15.0, slope * period_days * 0.5))
    projection = max(0, min(100, current + change))

    return {
        "direction": "climbing" if delta >= 3 else "sliding" if delta <= -3 else "holding",
        "first_half_avg": round(first, 1),
        "second_half_avg": round(second, 1),
        "delta": delta,
        "per_week": round(slope * 7, 1),
        "projection_next": round(projection),
    }


# +1: more is better, -1: less is better. Used so a best day is explained by
# what went right that day and a worst day by what went wrong.
STANDOUT_FACTORS = [
    ("sleep_hours", "h", "slept {v}", 1),
    ("screen_time", "h", "had {v} of screen time", -1),
    ("focus_hours", "h", "did {v} of deep work", 1),
    ("mood_score", "/10", "rated mood {v}", 1),
    ("energy_level", "/10", "rated energy {v}", 1),
]


def _standout(row: dict, rows: List[dict], good: bool) -> List[str]:
    """What was unusually good (or bad) about one day versus the period average."""
    notes = []
    for field, unit, phrase, polarity in STANDOUT_FACTORS:
        value, avg = row.get(field), _avg(r.get(field) for r in rows)
        if value is None or not avg:
            continue
        gap = (value - avg) / avg
        if abs(gap) >= 0.15 and (gap * polarity > 0) == good:
            notes.append((abs(gap), f"{phrase.format(v=_fmt(value, unit))} (avg {_fmt(avg, unit)})"))
    if good and row.get("target_hit_bool") is True:
        notes.append((0.1, "hit your goal"))
    elif not good and row.get("target_hit_bool") is False:
        notes.append((0.1, "missed your goal"))
    return [text for _, text in sorted(notes, reverse=True)[:2]]


def best_and_worst(rows: List[dict]) -> dict:
    scored = [r for r in rows if r.get("vektra_score") is not None]
    if len(scored) < 3:
        return {}
    best = max(scored, key=lambda r: r["vektra_score"])
    worst = min(scored, key=lambda r: r["vektra_score"])
    if best is worst:
        return {}
    pack = lambda r, good: {
        "date": r["date"].isoformat(),
        "weekday": WEEKDAYS[r["date"].weekday()],
        "score": round(r["vektra_score"]),
        "why": _standout(r, rows, good),
    }
    return {"best_day": pack(best, True), "worst_day": pack(worst, False)}


def drivers(rows: List[dict], limit: int = 3) -> List[dict]:
    """Which logged habits line up with the user's best days."""
    found = []
    for field, label, unit, _ in DRIVER_FACTORS:
        pairs = [(r[field], r["vektra_score"]) for r in rows
                 if r.get(field) is not None and r.get("vektra_score") is not None]
        if len(pairs) < 4:
            continue
        cut = statistics.median(v for v, _ in pairs)
        high = [s for v, s in pairs if v >= cut]
        low = [s for v, s in pairs if v < cut]
        if len(high) < 2 or len(low) < 2:
            continue
        hi, lo = sum(high) / len(high), sum(low) / len(low)
        diff = hi - lo
        if abs(diff) < 4:
            continue
        threshold = _fmt(round(cut, 1), unit)
        if diff > 0:
            text = f"On days with {threshold}+ {label}, your score averaged {hi:.0f}. On the rest: {lo:.0f}."
        else:
            text = f"On days with under {threshold} {label}, your score averaged {lo:.0f}. Above that: {hi:.0f}."
        found.append({
            "factor": field, "label": label, "threshold": threshold,
            "better_when": "higher" if diff > 0 else "lower",
            "with": round(max(hi, lo)), "without": round(min(hi, lo)),
            "gap": round(abs(diff)), "text": text,
        })
    return sorted(found, key=lambda d: d["gap"], reverse=True)[:limit]


def weekday_pattern(rows: List[dict]) -> Optional[dict]:
    by_day: Dict[int, list] = {}
    for r in rows:
        if r.get("vektra_score") is not None:
            by_day.setdefault(r["date"].weekday(), []).append(r["vektra_score"])
    usable = {d: sum(v) / len(v) for d, v in by_day.items() if len(v) >= 2}
    if len(rows) < 10 or len(usable) < 4:
        return None
    best, worst = max(usable, key=usable.get), min(usable, key=usable.get)
    if usable[best] - usable[worst] < 5:
        return None
    return {
        "best": WEEKDAYS[best], "best_avg": round(usable[best]),
        "worst": WEEKDAYS[worst], "worst_avg": round(usable[worst]),
    }


def consistency(rows: List[dict], period_days: int) -> dict:
    days = [r["date"] for r in rows]
    longest = current = 0
    run = 0
    for i, day in enumerate(days):
        run = run + 1 if i and (day - days[i - 1]).days == 1 else 1
        longest = max(longest, run)
    current = run if days else 0
    logged = len(days)
    return {
        "logged": logged,
        "period_days": period_days,
        "rate": round(logged / period_days * 100) if period_days else 0,
        "longest_streak": longest,
        "current_streak": current,
    }


def money(rows: List[dict]) -> Optional[dict]:
    money_rows = [r for r in rows if r.get("daily_income") is not None or r.get("expenses") is not None]
    if not money_rows:
        return None
    income = sum(r["daily_income"] or 0 for r in money_rows)
    spent = sum(r["expenses"] or 0 for r in money_rows)
    biggest = max(money_rows, key=lambda r: r["expenses"] or 0)
    net = income - spent
    return {
        "income": round(income, 2),
        "spent": round(spent, 2),
        "net": round(net, 2),
        "savings_rate": round(net / income * 100) if income > 0 else None,
        "avg_daily_spend": round(spent / len(money_rows), 2),
        "biggest_spend": {
            "date": biggest["date"].isoformat(),
            "weekday": WEEKDAYS[biggest["date"].weekday()],
            "amount": round(biggest["expenses"] or 0, 2),
        } if (biggest["expenses"] or 0) > 0 else None,
        # Per logged day x 30. Two names, not one "pace": a single field let the
        # narrative call the net figure a spending pace.
        "monthly_net_pace": round(net / len(money_rows) * 30, 2),
        "monthly_spend_pace": round(spent / len(money_rows) * 30, 2),
        "emergencies": sum(1 for r in money_rows if r.get("any_emergency")),
    }


def composite_score(engines: Dict[str, dict]) -> Optional[float]:
    """The period's headline score: engine averages, weighted over engines with data."""
    scored = {k: v["score"] for k, v in engines.items() if v.get("score") is not None}
    weight = sum(ENGINE_WEIGHTS[k] for k in scored)
    return round(sum(v * ENGINE_WEIGHTS[k] for k, v in scored.items()) / weight, 1) if weight else None


def headline_numbers(rows: List[dict], engines: Optional[Dict[str, dict]] = None) -> dict:
    goals_set = sum(1 for r in rows if _has(r.get("tomorrow_goal")))
    goals_hit = sum(1 for r in rows if r.get("target_hit_bool") is True)
    net = sum((r["daily_income"] or 0) - (r["expenses"] or 0) for r in rows)
    score_history = [r.get("vektra_score") for r in rows if r.get("vektra_score") is not None]
    return {
        "score": composite_score(engines if engines is not None else engine_breakdown(rows)),
        "mood": _avg(r.get("mood_score") for r in rows),
        "sleep": _avg(r.get("sleep_hours") for r in rows),
        "net_cash_flow": round(net, 2),
        "goal_hit_rate": round(goals_hit / goals_set * 100) if goals_set else None,
        "days_logged": len(rows),
        "score_history": score_history,
    }


def versus_previous(current: dict, previous_rows: List[dict]) -> Optional[dict]:
    if not previous_rows:
        return None
    previous = headline_numbers(previous_rows)
    out = {"previous": previous, "delta": {}}
    for key in ("score", "mood", "sleep", "net_cash_flow", "goal_hit_rate", "days_logged"):
        a, b = current.get(key), previous.get(key)
        out["delta"][key] = round(a - b, 1) if a is not None and b is not None else None
    return out


def build_insights(snapshots, previous_snapshots=None, period_days: int = 7) -> dict:
    rows = daily_rows(snapshots)
    if not rows:
        return {}
    engines = engine_breakdown(rows)
    current = headline_numbers(rows, engines)
    return {
        "engines": engines,
        "trend": trend(rows, period_days),
        **best_and_worst(rows),
        "drivers": drivers(rows),
        "weekday": weekday_pattern(rows) if period_days > 7 else None,
        "consistency": consistency(rows, period_days),
        "money": money(rows),
        "current": current,
        "vs_previous": versus_previous(current, daily_rows(previous_snapshots or [])),
    }
