import os
import uuid
from typing import Literal, Optional, Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from src.pipeline import VideoAutopilotPipeline

app = FastAPI(
    title="Video Autopilot API",
    description="Autonomous AI Video Production & YouTube Publishing Pipeline",
    version="1.0.0"
)

tasks_db: Dict[str, Dict[str, Any]] = {}
pipeline = VideoAutopilotPipeline()

class GenerateRequest(BaseModel):
    topic: str
    format_type: Literal["short", "long"] = "short"
    upload_to_youtube: bool = True

def process_video_task(task_id: str, topic: str, format_type: str, upload: bool):
    tasks_db[task_id]["status"] = "processing"
    try:
        result = pipeline.run(topic=topic, format_type=format_type, upload_to_youtube=upload)
        tasks_db[task_id]["status"] = "completed"
        tasks_db[task_id]["result"] = result
    except Exception as e:
        tasks_db[task_id]["status"] = "failed"
        tasks_db[task_id]["error"] = str(e)

@app.get("/")
def root():
    return {
        "service": "Video Autopilot API",
        "status": "online",
        "endpoints": {
            "generate": "POST /api/generate",
            "task_status": "GET /api/tasks/{task_id}",
            "history": "GET /api/history"
        }
    }

@app.post("/api/generate")
def create_video(req: GenerateRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())[:8]
    tasks_db[task_id] = {
        "task_id": task_id,
        "topic": req.topic,
        "format": req.format_type,
        "status": "queued"
    }
    background_tasks.add_task(
        process_video_task,
        task_id=task_id,
        topic=req.topic,
        format_type=req.format_type,
        upload=req.upload_to_youtube
    )
    return {
        "task_id": task_id,
        "status": "queued",
        "message": f"Video generation started for topic: '{req.topic}'"
    }

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="Task not found")
    return tasks_db[task_id]

@app.get("/api/history")
def get_history():
    history_file = pipeline.uploader.history_file
    if history_file.exists():
        import json
        with open(history_file, "r") as f:
            return json.load(f)
    return {"uploads": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
