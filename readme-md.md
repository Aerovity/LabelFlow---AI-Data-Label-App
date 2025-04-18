# Label Flow - Image Labeling Application

Label Flow is a web application that processes ZIP files containing images using NVIDIA's Grounding DINO API for object detection and labeling.

## Features

- Upload ZIP files containing images
- Process images with NVIDIA Grounding DINO model
- Track processing progress in real-time
- Download processed results
- Dark/Light mode support

## Setup Instructions

### Prerequisites

- Python 3.8+
- NVIDIA API Key (set as environment variable)

### Backend Setup

1. Clone this repository
2. Make the setup script executable:
   ```bash
   chmod +x setup.sh
   ```
3. Run the setup script:
   ```bash
   ./setup.sh
   ```
4. Set your NVIDIA API key as an environment variable:
   ```bash
   export NVIDIA_PERSONAL_API_KEY="your-api-key-here"
   ```

### Running the Application

1. Start the backend server:
   ```bash
   source venv/bin/activate
   python main.py
   ```
   The backend will run on http://localhost:8000

2. Open `index.html` in your web browser to use the frontend.

## Project Structure

```
├── main.py                 # FastAPI backend
├── labelflow_labeler.py    # Image labeling script
├── requirements.txt        # Python dependencies
├── setup.sh                # Setup script
├── uploads/                # Directory for uploaded files
├── results/                # Directory for processed results
├── index.html              # Frontend HTML
├── styles.css              # Frontend CSS
└── script.js               # Frontend JavaScript
```

## API Endpoints

- `POST /process` - Upload and process a ZIP file
- `GET /status/{task_id}` - Check the status of a processing task
- `GET /download/{task_id}` - Download the processed result

## Environment Variables

- `NVIDIA_PERSONAL_API_KEY` - Your personal NVIDIA API key for the Grounding DINO model

## Troubleshooting

If you encounter any issues:

1. Make sure your NVIDIA API key is correctly set
2. Check the server logs for detailed error messages
3. Ensure the uploaded ZIP file contains valid image files (JPG, JPEG, PNG)
