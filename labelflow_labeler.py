import os
import sys
import uuid
import zipfile
import time
import requests
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

nvai_url = "https://ai.api.nvidia.com/v1/cv/nvidia/nv-grounding-dino"
nvai_polling_url = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/"

# Constants
UPLOAD_ASSET_TIMEOUT = 300  # Timeout (in secs) to upload asset
MAX_RETRIES = 5  # Max num of retries while polling
DELAY_BTW_RETRIES = 1  # adding 1s delay between each polls

def _upload_asset(input_data, description):
    """Upload an asset to NVIDIA API"""
    try:
        api_key = os.environ.get('NVIDIA_PERSONAL_API_KEY')
        if not api_key:
            logger.error("NVIDIA_PERSONAL_API_KEY environment variable is not set")
            raise ValueError("NVIDIA API key is required but not found in environment")

        header_auth = f"Bearer {api_key}"
        assets_url = "https://api.nvcf.nvidia.com/v2/nvcf/assets"

        headers = {
            "Authorization": header_auth,
            "Content-Type": "application/json",
            "accept": "application/json",
        }

        s3_headers = {
            "x-amz-meta-nvcf-asset-description": description,
            "content-type": "image/jpeg",  # Changed to image/jpeg since we're processing images
        }

        payload = {"contentType": "image/jpeg", "description": description}

        response = requests.post(assets_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        asset_url = response.json()["uploadUrl"]
        asset_id = response.json()["assetId"]

        response = requests.put(
            asset_url,
            data=input_data,
            headers=s3_headers,
            timeout=UPLOAD_ASSET_TIMEOUT,
        )

        response.raise_for_status()
        return uuid.UUID(asset_id)
    except Exception as e:
        logger.error(f"Error in _upload_asset: {str(e)}")
        raise

def process_image(prompt, input_path, output_dir):
    """Process a single image using the NVIDIA API"""
    try:
        logger.info(f"Processing image: {input_path}")
        api_key = os.environ.get('NVIDIA_PERSONAL_API_KEY')
        if not api_key:
            raise ValueError("NVIDIA API key is required but not found in environment")
        
        header_auth = f"Bearer {api_key}"
        
        # Create output directory if it doesn't exist
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Upload the image as an asset
        with open(input_path, "rb") as f:
            asset_id = _upload_asset(f.read(), "Input Image")
        
        # Prepare the request
        inputs = {
            "model": "Grounding-Dino",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "media_url",
                            "media_url": {
                                "url": f"data:image/jpeg;asset_id,{asset_id}"
                            }
                        }
                    ]
                }
            ],
            "threshold": 0.3
        }

        asset_list = f"{asset_id}"

        headers = {
            "Content-Type": "application/json",
            "NVCF-INPUT-ASSET-REFERENCES": asset_list,
            "NVCF-FUNCTION-ASSET-IDS": asset_list,
            "Authorization": header_auth,
        }

        response = requests.post(nvai_url, headers=headers, json=inputs)

        zip_file_path = f"{output_dir}.zip"
        if response.status_code == 200:  # evaluation complete, output ready
            with open(zip_file_path, "wb") as out:
                out.write(response.content)
            
        elif response.status_code == 202:  # pending evaluation
            logger.info("Pending evaluation...")
            nvcf_reqid = response.headers['NVCF-REQID']
            polling_url = nvai_polling_url + nvcf_reqid

            # Polling to check if the response is ready
            retries_left = MAX_RETRIES
            while retries_left > 0:
                logger.info('Polling...')
                headers_polling = {"accept": "application/json", "Authorization": header_auth}
                response_polling = requests.get(polling_url, headers=headers_polling)
                
                if response_polling.status_code == 202:  # evaluation pending
                    logger.info('Result is not yet ready.')
                    retries_left -= 1
                    time.sleep(DELAY_BTW_RETRIES)
                    continue
                elif response_polling.status_code == 200:  # evaluation complete
                    logger.info('Result ready!')
                    with open(zip_file_path, "wb") as out:
                        out.write(response_polling.content)
                    break
                else:
                    logger.error(f"Unexpected response status: {response_polling.status_code}")
                    raise Exception(f"Unexpected response status: {response_polling.status_code}")
            
            if retries_left <= 0:
                raise Exception("Max retries reached while polling for results")
        else:
            logger.error(f"Unexpected initial response status: {response.status_code}")
            raise Exception(f"Unexpected initial response status: {response.status_code}")

        # Extract the ZIP file
        try:
            with zipfile.ZipFile(zip_file_path, "r") as z:
                z.extractall(output_dir)
            logger.info(f"Output saved to {output_dir}")
            
            # For debugging, list the extracted files
            files = os.listdir(output_dir)
            logger.info(f"Extracted files: {files}")
            
            # Clean up the zip file
            os.remove(zip_file_path)
            
            return True
        except zipfile.BadZipFile:
            logger.error(f"Bad zip file: {zip_file_path}")
            # Try to read the content as error message
            with open(zip_file_path, "r") as f:
                try:
                    error_content = f.read()
                    logger.error(f"Error content: {error_content}")
                except:
                    pass
            raise Exception("Failed to extract results - bad zip file")
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        # Create a basic error.txt file in the output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        with open(output_path / "error.txt", "w") as f:
            f.write(f"Error processing image:\n{str(e)}")
        return False

if __name__ == "__main__":
    """
    Process an image using the NVIDIA Grounding Dino Object Detection model.
    
    Usage: python labelflow_labeler.py <prompt> <input_image> <output_dir>
    
    Args:
        prompt: Text prompt for object detection
        input_image: Path to the input image
        output_dir: Directory to save the output
    """
    try:
        if len(sys.argv) != 4:
            print("Usage: python labelflow_labeler.py <prompt> <input_image> <output_dir>")
            sys.exit(1)

        prompt = sys.argv[1]
        input_image = sys.argv[2]
        output_dir = sys.argv[3]
        
        success = process_image(prompt, input_image, output_dir)
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        sys.exit(1)