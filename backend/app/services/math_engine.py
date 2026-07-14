from datetime import datetime, timedelta

def calculate_correlations(snapshots):
    """
    Analyzes historical data to find hidden patterns.
    Looks for correlations with time lags.
    """
    if len(snapshots) < 5:
        return []

    insights = []
    
    # Sort snapshots by date
    sorted_snaps = sorted(snapshots, key=lambda x: x.timestamp)
    
    # Example: Sleep Debt (T-2) -> Performance/Mood (T)
    # Iterate from index 2 onwards
    for i in range(2, len(sorted_snaps)):
        prev_prev = sorted_snaps[i-2]
        current = sorted_snaps[i]
        
        # Rule: Low sleep 2 days ago correlated with low mood/focus today
        if prev_prev.sleep_hours and prev_prev.sleep_hours < 6:
            if current.mood_score and current.mood_score < 5:
                insights.append({
                    "type": "silent_killer",
                    "text": f"Your mood today ({current.mood_score}/10) is linked to the lack of sleep 48 hours ago ({prev_prev.sleep_hours}h). You are paying for past debt.",
                    "severity": "high"
                })
        
        # Rule: High spending (T-1) -> Low focus (T)
        if prev_prev.expenses and prev_prev.expenses > 100:
            if current.focus_hours and current.focus_hours < 2:
                insights.append({
                    "type": "finance_distraction",
                    "text": "Your focus is low. Recent spikes in expenses tend to correlate with your inability to get deep work done. Financial stress is bleeding into your execution.",
                    "severity": "medium"
                })

    # Return unique insights (last 3)
    return insights[-3:]
