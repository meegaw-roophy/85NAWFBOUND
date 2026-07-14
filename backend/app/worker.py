import os
from celery import Celery

# Initialize Celery
celery_app = Celery(
    "worker",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

# Optional: configure task routes
celery_app.conf.task_routes = {
    "worker.tasks.calculate_snapshot_metrics": {"queue": "math"}
}
