import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def load_prompt():
    with open(os.path.join(os.path.dirname(__file__), "prompts", "multi_step_parser.txt"), "r") as f:
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
        content = result['choices'][0]['message']['content']
        steps = []
        for line in content.strip().split("\n"):
            if line.strip() and line[0].isdigit():
                step = line.split(".", 1)[-1].strip()
                steps.append(step)
        return steps
    except:
        return []
