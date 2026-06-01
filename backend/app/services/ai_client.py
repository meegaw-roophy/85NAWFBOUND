import asyncio
from anthropic import Anthropic
from typing import List
from app.core.config import settings


class AIClient:
    def __init__(self):
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY) if settings.CLAUDE_API_KEY else None

    async def summarize_snapshots(self, snapshots: List[dict], period_start=None, period_end=None) -> str:
        if not self.client:
            return "AI report generation disabled; set CLAUDE_API_KEY in .env."

        prompt = (
            "You are an AI assistant that creates a concise progress report. "
            "Summarize the user's snapshot history below, include actionable observations, "
            "and keep the response under 200 words.\n\n"
            f"Period start: {period_start}\n"
            f"Period end: {period_end}\n"
            f"Snapshots: {snapshots}\n"
        )
        response = await asyncio.to_thread(
            lambda: self.client.completions.create(
                model="claude-2.1",
                prompt=prompt,
                max_tokens=600,
                temperature=0.7,
            )
        )
        return response.get("completion", "")


ai_client = AIClient()
