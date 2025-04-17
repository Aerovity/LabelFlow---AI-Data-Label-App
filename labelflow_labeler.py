import os
import sys
import uuid
import zipfile
import time
import requests

nvai_url="https://ai.api.nvidia.com/v1/cv/nvidia/nv-grounding-dino"
nvai_polling_url = "https://api.nvcf.nvidia.com/v2/nvcf/pexec/status/"
header_auth = f"Bearer {os.getenv('NVIDIA_PERSONAL_API_KEY')}"

UPLOAD_ASSET_TIMEOUT = 300 # Timeout (in secs) to upload asset
MAX_RETRIES = 5 # Max num of retries while polling
DELAY_BTW_RETRIES = 1 # adding 1s delay between each polls



def _upload_asset(input, description):
    assets_url = "https://api.nvcf.nvidia.com/v2/nvcf/assets"

    headers = {
        "Authorization": header_auth,
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    s3_headers = {
        "x-amz-meta-nvcf-asset-description": description,
        "content-type": "video/mp4",
    }

    payload = {"contentType": "video/mp4", "description": description}

    response = requests.post(assets_url, headers=headers, json=payload, timeout=60)

    response.raise_for_status()

    asset_url = response.json()["uploadUrl"]
    asset_id = response.json()["assetId"]

    response = requests.put(
        asset_url,
        data=input,
        headers=s3_headers,
        timeout=UPLOAD_ASSET_TIMEOUT,
    )

    response.raise_for_status()
    return uuid.UUID(asset_id)


if __name__ == "__main__":
    """Uploads a video or image of your choosing to the NVCF API and sends a
    request to the Grounding Dino Object Detection model. The response is saved to a
    local directory.

    Note: You must set up an environment variable, NGC_PERSONAL_API_KEY.
    """

    if len(sys.argv) != 4:
        print("Usage: python test.py <prompt> <input_video> <output_dir>")
        sys.exit(1)

    asset_id = _upload_asset(open(sys.argv[2], "rb"), "Input Video")

    inputs = { "model": "Grounding-Dino",
        "messages": [
          {
            "role": "user",
            "content": [
                {
                  "type": "text",
                  "text": f"{sys.argv[1]}"
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

    if response.status_code == 200: # evaluation complete, output video ready
        with open(f"{sys.argv[3]}.zip", "wb") as out:
            out.write(response.content)
        with zipfile.ZipFile(f"{sys.argv[3]}.zip", "r") as z:
            z.extractall(sys.argv[3])

    elif response.status_code == 202: # pending evaluation
        print("Pending evaluation ...")
        nvcf_reqid = response.headers['NVCF-REQID']
        nvai_polling_url = nvai_polling_url + nvcf_reqid

        # Polling to check if the response is ready
        while( MAX_RETRIES ):
            print(f'Polling ...')
            headers_polling = { "accept": "application/json", "Authorization": header_auth }
            response_polling = requests.get(nvai_polling_url, headers=headers_polling)
            if response_polling.status_code == 202: # evaluation pending
                print('Result is not yet ready.')
                MAX_RETRIES -= 1
                time.sleep(DELAY_BTW_RETRIES)
                continue
            elif response_polling.status_code == 200: # evaluation complete, output video ready
                print('Result ready!')
                with open(f"{sys.argv[3]}.zip", "wb") as out:
                    out.write(response_polling.content)
                break
            else:
                print(f"Unexpected response status: {response_polling.status_code}")

        with zipfile.ZipFile(f"{sys.argv[3]}.zip", "r") as z:
            z.extractall(sys.argv[3])

    print(f"Output saved to {sys.argv[3]}")
    print(os.listdir(sys.argv[3]))