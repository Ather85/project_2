import os
import json
import asyncio
import google.generativeai as genai
from playwright.async_api import async_playwright
import tools

# --- CONFIGURATION ---
# Load the API key from the .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# We use Gemini Flash (Free & Fast) and force JSON output for reliable tool calling
model = genai.GenerativeModel('gemini-1.5-flash', 
    generation_config={"response_mime_type": "application/json"})

async def run_agent_loop(start_url: str, email: str, secret: str):
    """The main execution loop for the Quiz Solving Agent."""
    print(f"🤖 [AGENT] Starting Task for {start_url}")
    
    # Initialize Playwright browser
    async with async_playwright() as p:
        # Launch Chromium in headless mode (no visible browser window)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        current_url = start_url
        history = [] # Short-term memory of actions and results
        
        # Main Loop: We set a limit to 10 steps to prevent infinite loops on complex problems
        for step in range(10): 
            
            # 1. Construct the Prompt (The Agent's System Instruction)
            # This is where we define the agent's role, goal, and available tools.
            system_msg = f"""
            You are an automated agent solving a data quiz. 
            Your Goal: Solve the quiz at {current_url} and get the next URL or the final success message.
            
            TOOLS AVAILABLE:
            1. SCRAPE(url): Get text from page. Default url is {current_url}.
            2. DOWNLOAD(url, filename): Download a file found in the text.
            3. READ_PDF(filename): Read text from a local PDF.
            4. PYTHON(code): Run python code (pandas/re). The code MUST print() the final result (the answer to the quiz question).
            5. SUBMIT(url, answer): Submit final answer. The 'url' should be the endpoint found on the quiz page.
            
            HISTORY (Last 3 actions/results):
            {json.dumps(history[-3:])} 
            
            INSTRUCTIONS:
            - Analyze the current page content (or last result) and decide the NEXT logical step.
            - Return a JSON object with ONE action: {{ "tool": "NAME", "args": {{...}} }}
            - If you need to manipulate data, use the PYTHON tool.
            - If you have the quiz answer, use SUBMIT.
            - Always use the URL extracted from the page for the SUBMIT tool.
            """
            
            try:
                # 2. Ask Gemini what to do (The Reasoning Step)
                print(f"🤔 [AGENT] Thinking (Step {step})...")
                
                # Gemini will return a structured JSON response based on the prompt
                response = model.generate_content(system_msg)
                action = json.loads(response.text)
                print(f"👉 [AGENT] Action: {action.get('tool')}")
                
                # 3. Execute the Tool (The Action Step)
                result = ""
                tool = action.get('tool', '').upper()
                args = action.get('args', {})

                if tool == "SCRAPE":
                    target = args.get('url', current_url)
                    result = await tools.scrape_page(page, target)
                
                elif tool == "DOWNLOAD":
                    result = await tools.download_file(args.get('url'), args.get('filename', 'data_file'))
                    
                elif tool == "READ_PDF":
                    result = tools.read_pdf(args.get('filename'))
                    
                elif tool == "PYTHON":
                    # Pass previous result as context for the Python code
                    last_text = history[-1]['result'] if history else ""
                    result = tools.execute_python_code(args.get('code'), text_input=last_text)
                    print(f"🐍 [PYTHON OUTPUT] {result[:200].strip()}...")
                    
                elif tool == "SUBMIT":
                    payload = {
                        "email": email,
                        "secret": secret,
                        "url": current_url,
                        "answer": args.get('answer')
                    }
                    submit_url = args.get('url') # The LLM must find this URL
                    submit_res = await tools.submit_quiz(submit_url, payload)
                    print(f"✅ [SUBMIT RESULT] {submit_res}")
                    
                    # Check submission result
                    if submit_res.get('correct') == True:
                        new_url = submit_res.get('url')
                        if new_url:
                            print(f"🎉 Correct! Moving to next quiz: {new_url}")
                            current_url = new_url
                            history = [] # Reset history for the new challenge
                            continue # Skip history update for next step
                        else:
                            print("🏆 QUIZ FINISHED SUCCESSFULLY!")
                            break # Agent done
                    else:
                        result = f"Submission failed. Reason: {submit_res.get('reason')}"
                
                # 4. Update History (Observation Step)
                history.append({"step": step, "tool": tool, "result": str(result)[:800]}) 
                
            except Exception as e:
                print(f"❌ [AGENT ERROR] {e}")
                history.append({"error": str(e)})

        await browser.close()