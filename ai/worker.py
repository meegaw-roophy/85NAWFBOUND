import os
import asyncio
from anthropic import Anthropic
from app.core.config import settings

class ClaudeWorker:
    def __init__(self):
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY)

    async def generate_report(self, user_snapshot: dict) -> str:
        """Generate a text report from user snapshot using Claude (Anthropic).

        This is a minimal async wrapper; expand to batch processing, retries,
        caching, and cost controls for production.
        """
        prompt = f"Generate a concise weekly report for the following data: {user_snapshot}"
        resp = await asyncio.to_thread(
            lambda: self.client.completions.create(model="claude-2", prompt=prompt, max_tokens=800)
        )
        return resp.get('completion', '')

worker = ClaudeWorker()

if __name__ == '__main__':
    import json
    sample = {"mood": 7, "income": 100}
    print(asyncio.run(worker.generate_report(sample)))
