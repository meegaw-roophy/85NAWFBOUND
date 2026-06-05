import asyncio
import json
from typing import List, Optional

from app.core.config import settings


class AIClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.CLAUDE_API_KEY:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=settings.CLAUDE_API_KEY)
        return self._client

    async def summarize_snapshots(self, snapshots: List[dict], period_start=None, period_end=None) -> str:
        if not self.client:
            return self._fallback_summary(snapshots, period_start, period_end)

        system_prompt = (
            "You are VEKTRA's AI assistant. Create a concise, actionable progress report "
            "from the user's snapshot data. Highlight trends, wins, and areas needing attention. "
            "Keep under 200 words. Use bullet points for clarity."
        )
        user_message = (
            f"Period: {period_start} to {period_end}\n\n"
            f"Snapshot data ({len(snapshots)} entries):\n"
            f"{json.dumps(snapshots[:50], default=str, indent=2)}"
        )

        try:
            response = await asyncio.to_thread(
                lambda: self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=600,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
            )
            return response.content[0].text
        except Exception:
            return self._fallback_summary(snapshots, period_start, period_end)

    def _fallback_summary(self, snapshots: List[dict], period_start=None, period_end=None) -> str:
        count = len(snapshots)
        moods = [s.get("mood") for s in snapshots if s.get("mood") is not None]
        incomes = [s.get("income") for s in snapshots if s.get("income") is not None]
        expenses = [s.get("expenses") for s in snapshots if s.get("expenses") is not None]

        parts = [f"Summary of {count} snapshots"]
        if period_start and period_end:
            parts[0] += f" ({period_start} to {period_end})"
        parts.append(".")
        if moods:
            parts.append(f" Average mood: {sum(moods)/len(moods):.1f}/10.")
        if incomes:
            parts.append(f" Total income: ${sum(incomes):,.2f}.")
        if expenses:
            parts.append(f" Total expenses: ${sum(expenses):,.2f}.")
        if incomes and expenses:
            net = sum(incomes) - sum(expenses)
            parts.append(f" Net: ${net:,.2f}.")
        if not moods and not incomes:
            parts.append(" No numeric data recorded yet.")
        return "".join(parts)


ai_client = AIClient()
