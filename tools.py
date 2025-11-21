import json
import sys
import io
import pandas as pd
import pdfplumber
import requests
from playwright.async_api import Page

# --- 1. Python Execution Tool ---
# This is a key capability: allowing the LLM to write and run code for complex analysis.
def execute_python_code(code: str, text_input: str = None) -> str:
    """Runs python code dynamically to analyze data using Pandas or regular expressions."""
    print(f"⚡ [EXECUTOR] Running code...")
    
    # Define the execution scope for safety and utility
    local_scope = {"pd": pd, "text_input": text_input, "json": json}
    
    # Capture stdout to return 'print()' statements as the result
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    
    try:
        # Execute the LLM-generated code
        exec(code, {}, local_scope)
        sys.stdout = old_stdout
        return redirected_output.getvalue()
    except Exception as e:
        sys.stdout = old_stdout
        # Return the error so the LLM can fix its code
        return f"Error executing code: {e}"

# --- 2. Async Browser Tool ---
async def scrape_page(page: Page, url: str) -> str:
    """Visits URL and returns visible text content."""
    try:
        print(f"🌐 [BROWSER] Visiting {url}")
        await page.goto(url, timeout=60000) # 60s timeout for stability
        await page.wait_for_load_state("networkidle") # Wait for JavaScript to finish loading
        
        # Extract only the visible text content from the body
        text = await page.evaluate("document.body.innerText")
        return text[:30000] # Truncate to save LLM context tokens
    except Exception as e:
        return f"Error scraping page: {e}"

# --- 3. File Download Tool ---
async def download_file(url: str, filename: str = "downloaded_data") -> str:
    """Downloads a file using the requests library."""
    try:
        print(f"⬇️ [DOWNLOAD] Downloading {url}")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, verify=False)
        
        # Infer extension if the LLM didn't provide one
        if "." not in filename:
            content_type = response.headers.get('content-type', '')
            if 'pdf' in content_type: filename += ".pdf"
            elif 'csv' in content_type: filename += ".csv"
            else: filename += ".txt"

        with open(filename, 'wb') as f:
            f.write(response.content)
        
        return f"Success. File saved to {filename}"
    except Exception as e:
        return f"Error downloading: {e}"

# --- 4. PDF Reading Tool ---
def read_pdf(filename: str) -> str:
    """Extracts text from a local PDF file using pdfplumber."""
    try:
        text = ""
        with pdfplumber.open(filename) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text[:10000] # Truncate for LLM
    except Exception as e:
        return f"Error reading PDF: {e}"

# --- 5. Quiz Submission Tool ---
async def submit_quiz(submit_url: str, payload: dict) -> dict:
    """Submits the final answer to the quiz API endpoint."""
    print(f"🚀 [SUBMIT] Posting to {submit_url}")
    try:
        res = requests.post(submit_url, json=payload)
        # Try to parse JSON response
        try:
            return res.json()
        except:
            # If not JSON, return status and raw text
            return {"status": res.status_code, "text": res.text}
    except Exception as e:
        return {"error": str(e)}