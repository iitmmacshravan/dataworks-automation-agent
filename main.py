import os
import openai
import subprocess
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import subprocess
import tempfile
import uvicorn
app = FastAPI()

# Load AI Proxy Token from environment variable
openai_api_base = os.getenv("OPENAI_API_BASE", "https://aiproxy.sanand.workers.dev/openai/v1")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Define request model
class TaskRequest(BaseModel):
    task: str

@app.post("/run")
def run_task(task: str):
    """Processes a task using LLM, saves code to a temp file, and executes it using uv."""
    try:
        # Query AI Proxy (GPT-4o-Mini) for Python code
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI assistant. ONLY return Python code. Do NOT include explanations, markdown formatting, or text before/after the code."},
                {"role": "user", "content": task}
            ]
        )

        # Extract AI-generated Python code
        ai_code = response["choices"][0]["message"]["content"].strip()
        if ai_code.startswith("```python"):
            ai_code = ai_code.split("```python")[1].strip()
        if ai_code.endswith("```"):
            ai_code = ai_code[:-3].strip()
        
        # Write the AI-generated code to a temporary Python file
        with open('temp.py', 'w') as temp_file:
            temp_file.write(ai_code)
            temp_filepath = temp_file.name  # Save file path

        # Run the code using uv subprocess
        print(temp_filepath)
        try:
            result = subprocess.run(
                ["uv", "run", temp_filepath],  # Execute Python file
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            error = result.stderr.strip()
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Execution timeout (10s limit exceeded)."}

        return {
            "status": "success",
            "output": output if output else "No output"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read")
async def read(path: str):
    try:
        with open(path, "r") as f:
            content = f.read()
        return content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {path} not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
