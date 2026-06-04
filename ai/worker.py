import asyncio
import logging
from anthropic import Anthropic
from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeWorker:
    def __init__(self):
        self.client = Anthropic(api_key=settings.CLAUDE_API_KEY) if settings.CLAUDE_API_KEY else None

    async def generate_report(self, user_snapshot: dict) -> str:
        """Generate a text report from user snapshot using Claude (Anthropic).

        This is a minimal async wrapper; expand to batch processing, retries,
        caching, and cost controls for production.
        """
        if not self.client:
            logger.warning("CLAUDE_API_KEY not configured; skipping AI report generation")
            return ""

        prompt = f"Generate a concise weekly report for the following data: {user_snapshot}"
        try:
            resp = await asyncio.to_thread(
                lambda: self.client.completions.create(model="claude-2", prompt=prompt, max_tokens=800)
            )
        except Exception as exc:
            logger.error("Claude API call failed: %s", exc)
            return ""

        if isinstance(resp, dict):
            return resp.get("completion", "")
        return getattr(resp, "completion", "")


worker = ClaudeWorker()

if __name__ == '__main__':
    sample = {"mood": 7, "income": 100}
    print(asyncio.run(worker.generate_report(sample)))
