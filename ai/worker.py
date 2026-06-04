import asyncio
from app.services.ai_client import ai_client


class ClaudeWorker:
    """Thin wrapper around the shared AIClient for standalone usage."""

    async def generate_report(self, user_snapshot: dict) -> str:
        """Generate a text report from user snapshot using Claude (Anthropic)."""
        snapshots = [user_snapshot]
        return await ai_client.summarize_snapshots(snapshots)


worker = ClaudeWorker()

if __name__ == "__main__":
    sample = {"mood": 7, "income": 100}
    print(asyncio.run(worker.generate_report(sample)))
