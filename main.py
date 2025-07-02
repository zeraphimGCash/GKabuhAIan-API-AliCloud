from fastapi import FastAPI, HTTPException, Header, Request
from typing import Optional
import httpx
import os
from dotenv import load_dotenv
import uuid
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get environment variables
EAS_ENDPOINT = os.getenv("EAS_ENDPOINT")
EAS_TOKEN = os.getenv("EAS_TOKEN")
ALI_CLOUD_ENDPOINT = os.getenv("ALI_CLOUD_ENDPOINT")
ALI_CLOUD_TOKEN = os.getenv("ALI_CLOUD_TOKEN")

# Validate environment variables
if not EAS_ENDPOINT or not EAS_TOKEN:
    raise ValueError("EAS_ENDPOINT and EAS_TOKEN must be set in the .env file")

if not ALI_CLOUD_ENDPOINT or not ALI_CLOUD_TOKEN:
    raise ValueError("ALI_CLOUD_ENDPOINT and ALI_CLOUD_TOKEN must be set in the .env file")

# Ensure URLs have proper protocol
if EAS_ENDPOINT and not (EAS_ENDPOINT.startswith("http://") or EAS_ENDPOINT.startswith("https://")):
    EAS_ENDPOINT = f"https://{EAS_ENDPOINT}"

if ALI_CLOUD_ENDPOINT and not (ALI_CLOUD_ENDPOINT.startswith("http://") or ALI_CLOUD_ENDPOINT.startswith("https://")):
    ALI_CLOUD_ENDPOINT = f"https://{ALI_CLOUD_ENDPOINT}"

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {EAS_TOKEN}"
}

ALI_HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ALI_CLOUD_TOKEN}"
}

@app.post("/generate_caption")
async def generate_text(prompt: Optional[str] = Header(None), auth: Optional[str] = Header(None)):
    # Verify authentication
    if auth != "zeraphim_made_this":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt header missing")
        
    payload = {
        "prompt": prompt,
        "top_p": 0.8,
        "temperature": 0.95
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(EAS_ENDPOINT, headers=HEADERS, json=payload)
            response.raise_for_status()
            result = response.json()
            return {"response": result.get("output", result)}
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"EAS call failed: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/generate_image")
async def generate_image(request: Request):
    # Verify authentication
    auth = request.headers.get("auth")
    if auth != "zeraphim_made_this":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    owner_image = request.headers.get("owner_image")
    product_image = request.headers.get("product_image")
    if not owner_image or not product_image:
        raise HTTPException(status_code=400, detail="Missing owner_image or product_image in headers.")
    
    prompt = f"Combine the two images so that the owner from this image: {owner_image} is holding the product from this image: {product_image} for a social media post. Make it visually appealing and suitable for online sharing."
    
    # Use /tmp for serverless environments like Vercel
    images_dir = os.environ.get("IMAGES_DIR", "/tmp/images")
    os.makedirs(images_dir, exist_ok=True)
    output_file = f"{images_dir}/{uuid.uuid4()}.png"
    
    payload = {
        "prompt": prompt,
        "negative_prompt": "low quality, bad anatomy, distorted, blurry",
        "width": 768,
        "height": 768,
        "num_inference_steps": 50,
        "guidance_scale": 7.5
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(ALI_CLOUD_ENDPOINT, headers=ALI_HEADERS, json=payload)
            response.raise_for_status()
            
            # Save the image bytes to a file
            image_bytes = response.content
            with open(output_file, "wb") as f:
                f.write(image_bytes)
            
            image_size = len(image_bytes)
            
            # Build the image URL based on the request
            base_url = str(request.base_url).rstrip('/')
            # Return a special endpoint for /tmp images
            image_url = f"{base_url}/get_tmp_image/{os.path.basename(output_file)}"
            
            return {
                "message": f"Created output image using {image_size} bytes",
                "image_url": image_url
            }
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"Ali Cloud call failed: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/get_tmp_image/{filename}", include_in_schema=True)
async def get_tmp_image(filename: str):
    file_path = os.path.join("/tmp/images", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path, media_type="image/png")