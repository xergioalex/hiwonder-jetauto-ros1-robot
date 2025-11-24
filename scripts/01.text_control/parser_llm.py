import requests
import os
import json
from dotenv import load_dotenv

# Load environment variables from .env file in repo root
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(repo_root, '.env'))

# OpenAI Responses API constants
OPENAI_API_BASE_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL_MOVEMENT = "gpt-5-mini"  # for movement commands
OPENAI_MODEL_UTILITY = "gpt-5-mini"   # for translation / parsing of steps

def extract_text_from_responses(result):
    """
    Extract the main text from a Responses API response.
    Tries multiple possible response formats:
      - result["output"][0]["content"][0]["text"]
      - result["output"][0]["text"]
      - result["output"][1] (if output[0] is metadata)
      - result["output"][0] (if it's a string)
      - result["text"]
    """
    try:
        # Try standard format first
        if "output" in result and len(result["output"]) > 0:
            # Check all items in output array
            for output_item in result["output"]:
                # Skip metadata dicts (they have keys like 'format', 'verbosity', etc.)
                if isinstance(output_item, dict):
                    # Check if it has "content" array
                    if "content" in output_item and len(output_item["content"]) > 0:
                        content_item = output_item["content"][0]
                        if "text" in content_item:
                            return content_item["text"]
                        # If content item is directly a string
                        if isinstance(content_item, str):
                            return content_item
                    # Check if output item has "text" directly (and is not metadata)
                    if "text" in output_item and "format" not in output_item:
                        return output_item["text"]
                # If output item is directly a string
                elif isinstance(output_item, str):
                    return output_item
        # Try direct "text" field
        if "text" in result:
            text_value = result["text"]
            # If text is a string, return it
            if isinstance(text_value, str):
                return text_value
            # If text is a dict, try to extract from it
            if isinstance(text_value, dict):
                if "content" in text_value:
                    return str(text_value["content"])
                return str(text_value)
        # Debug: print the actual structure
        print("Debug: Unexpected response structure: {}".format(json.dumps(result, indent=2)[:500]))
        return None
    except (KeyError, IndexError, TypeError) as e:
        print("Error extracting text from Responses API result: {}".format(e))
        print("Debug: Response structure: {}".format(str(result)[:500]))
        return None

def load_prompt():
    with open(os.path.join(os.path.dirname(__file__), "prompts", "multi_step_parser.txt"), "r", encoding='utf-8') as f:
        return f.read()

def safe_print(message):
    """Print message safely, handling Unicode encoding errors"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: remove non-ASCII characters
        print(message.encode('ascii', 'ignore').decode('ascii'))

def translate_to_english(text):
    """Translate commands from any language to English for better LLM understanding"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return text  # Return original if no API key
    
    # Simple check: if text contains common non-English words, translate it
    # This helps avoid unnecessary API calls for English commands
    english_indicators = ['move', 'go', 'turn', 'rotate', 'forward', 'backward', 'left', 'right', 
                         'meter', 'meters', 'degree', 'degrees', 'then', 'and', 'stop']
    text_lower = text.lower()
    has_english = any(indicator in text_lower for indicator in english_indicators)
    
    # If it looks like English already, skip translation
    if has_english and len([w for w in text_lower.split() if w in english_indicators]) >= 2:
        return text  # Likely already in English
    
    url = OPENAI_API_BASE_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    data = {
        "model": OPENAI_MODEL_UTILITY,
        "instructions": (
            "You are a translator. Translate robot movement commands from any "
            "language to English. Keep the meaning and structure exactly the same. "
            "Only return the translated text, no explanations, no additional text."
        ),
        "input": text,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        if response.status_code == 200:
            result = response.json()
            translated = extract_text_from_responses(result)
            if translated:
                translated = translated.strip()
                safe_print("Debug: Translated to English: {}".format(translated))
                return translated
    except:
        pass  # If translation fails, return original text
    
    return text  # Return original if translation fails

def split_into_steps(text):
    # Translate to English first for better LLM understanding
    english_text = translate_to_english(text)
    safe_print("Debug: Starting split_into_steps with text: {}".format(english_text))
    
    # Check if .env file exists
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        print("Debug: .env file found at: {}".format(env_path))
    else:
        print("Warning: .env file not found at: {}".format(env_path))
    
    system_prompt = load_prompt()
    print("Debug: System prompt loaded, length: {}".format(len(system_prompt)))
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        print("Debug: Make sure .env file exists and contains: OPENAI_API_KEY=your_key_here")
        return []
    
    # Check API key format (should start with sk-)
    if not api_key.startswith('sk-'):
        print("Warning: API key doesn't start with 'sk-', might be invalid")
    else:
        print("Debug: API key format looks correct (starts with sk-)")
    print("Debug: API key length: {} characters".format(len(api_key)))
    print("Debug: Making request to OpenAI Responses API...")
    
    url = OPENAI_API_BASE_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    data = {
        "model": OPENAI_MODEL_UTILITY,
        "instructions": system_prompt,
        "input": english_text,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        print("Debug: Response status code: {}".format(response.status_code))
        
        # Check for authentication errors
        if response.status_code == 401:
            print("Error: Authentication failed - Invalid API key")
            print("Debug: Check if your API key is correct in .env file")
            try:
                error_data = response.json()
                print("Error details: {}".format(error_data))
            except:
                print("Error response: {}".format(response.text))
            return []
        elif response.status_code == 403:
            print("Error: Access forbidden - API key may not have permission")
            try:
                error_data = response.json()
                print("Error details: {}".format(error_data))
            except:
                print("Error response: {}".format(response.text))
            return []
        elif response.status_code == 429:
            print("Error: Rate limit exceeded - Too many requests")
            return []
        
        response.raise_for_status()
        result = response.json()
        print("Debug: Response received successfully")
        
        # Debug: print raw response structure (first 500 chars)
        print("Debug: Raw response keys: {}".format(list(result.keys()) if isinstance(result, dict) else "Not a dict"))
        if isinstance(result, dict) and "output" in result:
            print("Debug: Output type: {}, length: {}".format(
                type(result["output"]), 
                len(result["output"]) if isinstance(result["output"], list) else "N/A"
            ))
        
        content = extract_text_from_responses(result)
        if not content:
            print("Error: Empty content from Responses API")
            print("Debug: Full response structure: {}".format(json.dumps(result, indent=2)[:1000]))
            return []
        
        safe_print("API Response: {}".format(content))
        
        steps = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and len(line) > 0 and line[0].isdigit():
                step = line.split(".", 1)[-1].strip()
                steps.append(step)
        
        if len(steps) == 0:
            # If no numbered steps found, treat the whole command as a single step
            print("Warning: No numbered steps found, using command as single step")
            steps = [english_text]

        # ALWAYS add a stop command at the end for safety
        if steps and steps[-1].lower() not in ['stop', 'para', 'alto', 'detente', 'halt', 'freeze']:
            steps.append('stop')
            print("Debug: Added automatic 'stop' command at the end")

        return steps
    except requests.exceptions.RequestException as e:
        print("Error making API request: {}".format(e))
        if hasattr(e, 'response') and e.response is not None:
            print("Response status code: {}".format(e.response.status_code))
            try:
                error_data = e.response.json()
                print("Error response: {}".format(error_data))
            except:
                print("Error response text: {}".format(e.response.text))
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
