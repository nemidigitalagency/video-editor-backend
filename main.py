import os
import asyncio
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import aiofiles
import json
import uuid
import logging
from pathlib import Path
from datetime import datetime
import shutil
from typing import Optional
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Video Editing Engine",
    description="Professional video editing with AI",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
TEMP_DIR = Path("temp")

for directory in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    directory.mkdir(exist_ok=True, parents=True)

# Store processing jobs
JOBS = {}

# Simple mock agents (no heavy dependencies)
class MockAgent:
    """Simple mock agent that works without ML libraries"""
    async def process_async(self, *args, **kwargs):
        return "processed"
    
    def get_effects_for_style(self, style):
        return {"effect1": "value1"}
    
    async def generate_async(self, *args):
        return []
    
    async def detect_scenes_async(self, *args):
        return []
    
    async def select_async(self, *args):
        return "music.mp3"
    
    async def optimize_async(self, *args):
        return {}

# Initialize mock agents
video_processor = MockAgent()
caption_generator = MockAgent()
scene_detector = MockAgent()
effect_engine = MockAgent()
music_selector = MockAgent()
viral_optimizer = MockAgent()

logger.info("✅ All mock agents initialized")

# ==========================================
# API ENDPOINTS
# ==========================================

@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "status": "🎬 AI Video Editor Backend Running",
        "version": "1.0.0",
        "message": "Backend is ready!"
    }

@app.get("/api/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "jobs_in_queue": len(JOBS)
    }

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload video file"""
    try:
        logger.info(f"📥 Uploading video: {file.filename}")
        
        # Validate file
        if not file.filename.endswith(('.mp4', '.mov', '.avi', '.mkv')):
            raise HTTPException(status_code=400, detail="Invalid video format. Use MP4, MOV, AVI, or MKV")
        
        # Create job ID
        job_id = str(uuid.uuid4())
        job_dir = UPLOAD_DIR / job_id
        job_dir.mkdir(exist_ok=True, parents=True)
        
        # Save file
        file_path = job_dir / file.filename
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"✅ Video saved: {file_path}")
        
        # Create job record
        JOBS[job_id] = {
            "id": job_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "status": "uploaded",
            "created_at": datetime.now().isoformat(),
            "progress": 0,
            "error": None,
            "output_path": None
        }
        
        return {
            "status": "success",
            "job_id": job_id,
            "filename": file.filename,
            "message": "Video uploaded successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process")
async def process_video(
    job_id: str = Form(...),
    style: str = Form("viral"),
    platform: str = Form("tiktok"),
    target_duration: float = Form(60.0),
    background_tasks: BackgroundTasks = None
):
    """Process uploaded video"""
    try:
        logger.info(f"🎬 Starting processing - Job: {job_id}")
        
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = JOBS[job_id]
        
        if job["status"] == "processing":
            raise HTTPException(status_code=400, detail="Already processing")
        
        # Update job status
        job["status"] = "processing"
        job["progress"] = 10
        
        # Start background processing
        if background_tasks:
            background_tasks.add_task(
                _process_video_background,
                job_id
            )
        
        return {
            "status": "processing",
            "job_id": job_id,
            "message": "Video processing started"
        }
    
    except Exception as e:
        logger.error(f"❌ Process error: {e}")
        if job_id in JOBS:
            JOBS[job_id]["status"] = "failed"
            JOBS[job_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

async def _process_video_background(job_id: str):
    """Background processing"""
    try:
        job = JOBS[job_id]
        video_path = job["file_path"]
        
        # Simulate processing steps
        steps = [
            ("Detecting scenes", 20),
            ("Generating captions", 35),
            ("Processing video", 50),
            ("Selecting music", 65),
            ("Applying effects", 75),
            ("Optimizing", 85),
            ("Exporting", 95)
        ]
        
        for step_name, progress in steps:
            logger.info(f"{step_name}...")
            job["progress"] = progress
            await asyncio.sleep(1)  # Simulate processing
        
        # For demo: just copy the video as output
        output_filename = f"edited_{job_id}.mp4"
        output_path = OUTPUT_DIR / output_filename
        
        # Create a dummy output file
        shutil.copy(video_path, output_path)
        
        # Update job
        job["status"] = "completed"
        job["progress"] = 100
        job["output_path"] = str(output_path)
        job["completed_at"] = datetime.now().isoformat()
        
        logger.info(f"✅ Job completed: {job_id}")
        
    except Exception as e:
        logger.error(f"❌ Background processing error: {e}")
        job["status"] = "failed"
        job["error"] = str(e)

@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Check job status"""
    try:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = JOBS[job_id]
        return {
            "job_id": job_id,
            "status": job["status"],
            "progress": job.get("progress", 0),
            "created_at": job["created_at"],
            "error": job.get("error")
        }
    except Exception as e:
        logger.error(f"❌ Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{job_id}")
async def download_video(job_id: str):
    """Download processed video"""
    try:
        if job_id not in JOBS:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = JOBS[job_id]
        
        if job["status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Video not ready. Status: {job['status']}"
            )
        
        output_path = Path(job["output_path"])
        
        if not output_path.exists():
            raise HTTPException(status_code=404, detail="Output not found")
        
        logger.info(f"📥 Downloading: {output_path}")
        
        return FileResponse(
            path=output_path,
            filename=f"edited_{job_id}.mp4",
            media_type="video/mp4"
        )
    
    except Exception as e:
        logger.error(f"❌ Download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("🚀 Backend startup")

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
