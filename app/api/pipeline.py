from fastapi import APIRouter, BackgroundTasks

from app.pipelines.etl import run_pipeline

router = APIRouter(tags=["Pipeline"])


@router.post("/run-pipeline")
def trigger_pipeline(
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(run_pipeline)

    return {
        "message": "Pipeline triggered successfully. Running in background."
    }