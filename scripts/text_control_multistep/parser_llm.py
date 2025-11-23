import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def load_prompt():
    with open(os.path.join(os.path.dirname(__file__), "prompts", "multi_step_parser.txt"), "r", encoding='utf-8') as f:
        return f.read()

def split_into_steps(text):
    system_prompt = load_prompt()
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return []
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if 'choices' not in result or len(result['choices']) == 0:
            print("Error: No choices in API response")
            return []
        
        content = result['choices'][0]['message']['content']
        print("API Response: {}".format(content))  # Debug output
        
        steps = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and len(line) > 0 and line[0].isdigit():
                step = line.split(".", 1)[-1].strip()
                steps.append(step)
        
        if len(steps) == 0:
            # If no numbered steps found, treat the whole command as a single step
            print("Warning: No numbered steps found, using command as single step")
            steps = [text]
        
        return steps
    except requests.exceptions.RequestException as e:
        print("Error making API request: {}".format(e))
        return []
    except KeyError as e:
        print("Error parsing API response: {}".format(e))
        print("Response: {}".format(result if 'result' in locals() else "No response"))
        return []
    except Exception as e:
        print("Unexpected error: {}".format(e))
        import traceback
        traceback.print_exc()
        return []
