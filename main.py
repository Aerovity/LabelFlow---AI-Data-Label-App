from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import uuid
import zipfile
import shutil
import tempfile
import subprocess
from pathlib import Path
import logging
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Label Flow API")

# Add CORS middleware to allow the frontend to call our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories for uploads and results if they don't exist
UPLOAD_DIR = Path("uploads")
RESULTS_DIR = Path("results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Dictionary to track processing status
processing_tasks = {}

@app.get("/")
async def root():
    return {"message": "Label Flow API is running"}

@app.post("/process")
async def process_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    prompt: str = Form("Find all objects"),
):
    # Validate the file
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted")
    
    # Validate the prompt
    if not prompt or len(prompt.strip()) == 0:
        prompt = "Find all objects"
    
    # Generate a unique ID for this processing task
    task_id = str(uuid.uuid4())
    
    # Create task-specific directories
    task_upload_dir = UPLOAD_DIR / task_id
    task_results_dir = RESULTS_DIR / task_id
    task_upload_dir.mkdir(exist_ok=True)
    task_results_dir.mkdir(exist_ok=True)
    
    # Save the uploaded file
    zip_path = task_upload_dir / "input.zip"
    try:
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Error saving uploaded file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving uploaded file: {str(e)}")
    
    # Extract images to a temp directory
    extract_dir = task_upload_dir / "extracted"
    extract_dir.mkdir(exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Store task metadata including the prompt
        metadata = {
            "prompt": prompt,
            "original_filename": file.filename,
            "timestamp": str(task_id),
            "status": "processing"
        }
        
        # Save metadata
        with open(task_upload_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)
        
        # Update task status
        processing_tasks[task_id] = {
            "status": "processing", 
            "progress": 0,
            "prompt": prompt
        }
        
        # Process the images in the background
        background_tasks.add_task(
            process_images,
            task_id=task_id,
            extract_dir=extract_dir,
            results_dir=task_results_dir,
            prompt=prompt
        )
        
        return {
            "task_id": task_id,
            "status": "processing",
            "prompt": prompt,
            "message": "File uploaded and being processed"
        }
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

def process_images(task_id: str, extract_dir: Path, results_dir: Path, prompt: str):
    """Process each image in the extracted directory using the labeler."""
    try:
        # Get list of image files
        image_files = []
        for ext in ('*.jpg', '*.jpeg', '*.png'):
            image_files.extend(list(extract_dir.glob(f'**/{ext}')))
        
        total_images = len(image_files)
        if total_images == 0:
            processing_tasks[task_id] = {
                "status": "error", 
                "message": "No image files found in ZIP",
                "prompt": prompt
            }
            return
        
        # Check for NVIDIA API key
        if not os.environ.get('NVIDIA_PERSONAL_API_KEY'):
            logger.error("NVIDIA_PERSONAL_API_KEY is not set in environment")
            processing_tasks[task_id] = {
                "status": "error", 
                "message": "API key for image processing is not configured",
                "prompt": prompt
            }
            return
        
        # Create a results directory for each image
        image_results_dir = results_dir / "images"
        image_results_dir.mkdir(exist_ok=True)
        
        # Create a readme file with processing details
        with open(results_dir / "README.txt", "w") as readme:
            readme.write(f"Label Flow Processing Results\n")
            readme.write(f"=========================\n\n")
            readme.write(f"Prompt used: {prompt}\n")
            readme.write(f"Total images processed: {total_images}\n")
            readme.write(f"Processing date: {task_id}\n\n")
            readme.write(f"Files included in this package:\n")
        
        for i, image_path in enumerate(image_files):
            try:
                # Update progress
                progress = int((i / total_images) * 100)
                processing_tasks[task_id] = {
                    "status": "processing", 
                    "progress": progress,
                    "prompt": prompt
                }
                
                # Output filename based on original image name
                output_name = image_results_dir / f"labeled_{image_path.stem}"
                
                # Run the labeler script on each image
                try:
                    # Create a clean environment copy with the API key
                    env = os.environ.copy()
                    
                    cmd = [
                        "python", 
                        "labelflow_labeler.py", 
                        prompt,  # Use the provided prompt
                        str(image_path), 
                        str(output_name)
                    ]
                    
                    result = subprocess.run(
                        cmd, 
                        env=env, 
                        check=True, 
                        capture_output=True, 
                        text=True,
                        timeout=60  # Set a timeout for the process
                    )
                    
                    # Append processing details to readme
                    with open(results_dir / "README.txt", "a") as readme:
                        readme.write(f"- {image_path.name} -> labeled_{image_path.stem}\n")
                    
                except subprocess.SubprocessError as e:
                    logger.error(f"Subprocess error for {image_path}: {str(e)}")
                    with open(results_dir / "README.txt", "a") as readme:
                        readme.write(f"- ERROR processing {image_path.name}: Subprocess error\n")
                
            except Exception as e:
                logger.error(f"Error processing image {image_path}: {str(e)}")
                # Append error to readme
                with open(results_dir / "README.txt", "a") as readme:
                    readme.write(f"- ERROR processing {image_path.name}: {str(e)}\n")
        
        # Create a summary file with the prompt and other metadata
        with open(results_dir / "summary.json", "w") as summary_file:
            summary = {
                "prompt": prompt,
                "total_images": total_images,
                "processed_images": len(image_files),
                "task_id": task_id
            }
            json.dump(summary, summary_file, indent=2)
        
        # Create a ZIP file with all processed results
        output_zip_path = RESULTS_DIR / f"{task_id}.zip"
        shutil.make_archive(str(output_zip_path.with_suffix('')), 'zip', results_dir)
        
        # Update task status
        processing_tasks[task_id] = {
            "status": "completed",
            "result_file": str(output_zip_path),
            "prompt": prompt
        }
        
    except Exception as e:
        logger.error(f"Error in process_images: {str(e)}")
        processing_tasks[task_id] = {
            "status": "error", 
            "message": str(e),
            "prompt": prompt
        }

@app.get("/status/{task_id}")
async def get_status(task_id: str):
    """Check the status of a processing task."""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return processing_tasks[task_id]

@app.get("/download/{task_id}")
async def download_result(task_id: str):
    """Download the processed file."""
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = processing_tasks[task_id]
    if task_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="Processing not completed yet")
    
    result_file = task_info["result_file"]
    if not os.path.exists(result_file):
        raise HTTPException(status_code=404, detail="Result file not found")
    
    # Get prompt from task info for filename
    prompt_snippet = task_info.get("prompt", "").replace(" ", "_")[:20]
    if not prompt_snippet:
        prompt_snippet = "labeled"
    
    return FileResponse(
        result_file, 
        media_type="application/zip",
        filename=f"{prompt_snippet}_images.zip"
    )

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Label Flow API")
    # Check for NVIDIA API key at startup
    if not os.environ.get('NVIDIA_PERSONAL_API_KEY'):
        logger.warning("NVIDIA_PERSONAL_API_KEY environment variable is not set. Object detection functionality will be limited.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)