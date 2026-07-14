from app.worker import celery_app
from app.db.session import SessionLocal
from app.crud import update_snapshot_metrics
from app.services.vektra_engine import calculate_vektra_score

@celery_app.task(name="worker.tasks.calculate_snapshot_metrics")
def calculate_snapshot_metrics(snapshot_id, snapshot_data, prev_dict):
    """
    Background task to run heavy math calculations.
    """
    score_result = calculate_vektra_score(snapshot_data, prev_dict)
    
    # Use a synchronous session for the task
    with SessionLocal() as db:
        update_snapshot_metrics(db, snapshot_id, score_result)
        db.commit()
    
    return {"status": "success", "snapshot_id": snapshot_id}
