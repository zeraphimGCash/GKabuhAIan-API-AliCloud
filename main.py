from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn

# Initialize FastAPI app
app = FastAPI(
    title="GKabuhAIan API",
    description="A sample API for generating captions and images",
    version="1.0.0"
)

# Request and response models
class CaptionRequest(BaseModel):
    image_url: str
    max_length: Optional[int] = 100

class CaptionResponse(BaseModel):
    caption: str
    confidence: float

class ImageGenerationRequest(BaseModel):
    prompt: str
    width: Optional[int] = 512
    height: Optional[int] = 512
    num_inference_steps: Optional[int] = 50

class ImageGenerationResponse(BaseModel):
    image_url: str
    seed: int

# Routes
@app.get("/")
async def root():
    """Root endpoint that returns a welcome message"""
    return {"message": "Welcome to GKabuhAIan API! Use /docs to see the API documentation."}

@app.post("/generate_caption", response_model=CaptionResponse)
async def generate_caption(request: CaptionRequest):
    """
    Generate a caption for the provided image URL
    """
    try:
        caption = f"A sample caption for the image at {request.image_url}"
        confidence = 0.95
        
        return CaptionResponse(caption=caption, confidence=confidence)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating caption: {str(e)}")

@app.post("/generate_image", response_model=ImageGenerationResponse)
async def generate_image(request: ImageGenerationRequest):
    """
    Generate an image based on the provided text prompt
    """
    try:
        # Simulated response for sample
        image_url = f"https://example.com/generated_image_{hash(request.prompt) % 1000}.png"
        seed = hash(request.prompt) % 10000
        
        return ImageGenerationResponse(image_url=image_url, seed=seed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating image: {str(e)}")

# For local development
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)