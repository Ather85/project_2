from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import agent

# Load environment variables from the .env file
load_dotenv()

app = FastAPI(
    title="Gemini Quiz Agent",
    description="A FastAPI server to receive quiz tasks and launch the ReAct agent.",
    version="1.0.0"
)

# Data Model for Request Validation
class QuizRequest(BaseModel):
    """Defines the structure of the incoming request from the professor's bot."""
    email: str
    secret: str
    url: str

# Get the secret key from the .env file (defaulting to 'elephant' for safety)
MY_SECRET = os.getenv("MY_SECRET_KEY", "elephant") 

@app.post("/quiz")
async def start_quiz(req: QuizRequest, tasks: BackgroundTasks):
    """
    This endpoint is hit by the professor's bot.
    It verifies the secret and immediately starts the agent in the background.
    """
    # 1. Security Check: Block unauthorized users
    if req.secret != MY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Secret Key. Access Denied.")
    
    # 2. Start Agent in Background (Crucial for non-blocking API response)
    # The tasks.add_task ensures the API responds immediately (HTTP 200) 
    # while the long-running quiz solving happens in parallel.
    print(f"✅ Received task for: {req.url}. Launching agent...")
    tasks.add_task(agent.run_agent_loop, req.url, req.email, req.secret)
    
    # 3. Immediate Success Response
    return {"message": "Agent task started successfully", "status": "processing"}

@app.get("/")
def health_check():
    """Simple endpoint to verify the server is running."""
    return {"status": "online", "stack": "FastAPI + Playwright + Gemini"}

if __name__ == "__main__":
    import uvicorn
    # This runs the server locally on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)