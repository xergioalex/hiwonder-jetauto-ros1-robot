import rospy
from geometry_msgs.msg import Twist
import requests
import json
import time
import os
import signal
import sys
import re
from dotenv import load_dotenv
from parser_llm import split_into_steps
import threading

# Try to import pyttsx3, but make it optional
try:
    import pyttsx3
    TTS_AVAILABLE = True
except (ImportError, SyntaxError) as e:
    print("Warning: pyttsx3 not available ({}). Voice notifications will be disabled.".format(e))
    print("Commands will still work, but without voice announcements.")
    TTS_AVAILABLE = False
    pyttsx3 = None

# Global flag for clean exit
should_exit = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global should_exit
    print("\n\nCtrl+C detected - Stopping controller...")
    speak("Deteniendo")
    print("Goodbye!")
    should_exit = True
    sys.exit(0)

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
      - result["output"][0]
      - result["text"]
    """
    try:
        # Try standard format first
        if "output" in result and len(result["output"]) > 0:
            output_item = result["output"][0]
            # Check if it has "content" array
            if "content" in output_item and len(output_item["content"]) > 0:
                content_item = output_item["content"][0]
                if "text" in content_item:
                    return content_item["text"]
                # If content item is directly a string
                if isinstance(content_item, str):
                    return content_item
            # Check if output item has "text" directly
            if "text" in output_item:
                return output_item["text"]
            # If output item is directly a string
            if isinstance(output_item, str):
                return output_item
        # Try direct "text" field
        if "text" in result:
            return result["text"]
        # Debug: print the actual structure
        print("Debug: Unexpected response structure: {}".format(json.dumps(result, indent=2)[:500]))
        return None
    except (KeyError, IndexError, TypeError) as e:
        print("Error extracting text from Responses API result: {}".format(e))
        print("Debug: Response structure: {}".format(str(result)[:500]))
        return None

def safe_print(message):
    """Print message safely, handling Unicode encoding errors"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: remove non-ASCII characters
        print(message.encode('ascii', 'ignore').decode('ascii'))

# Initialize TTS engine (global to avoid reinitializing on each call)
tts_engine = None
tts_lock = threading.Lock()

def init_tts():
    """Initialize the TTS engine with proper settings"""
    global tts_engine
    if not TTS_AVAILABLE or pyttsx3 is None:
        return None
    if tts_engine is None:
        try:
            tts_engine = pyttsx3.init()
            # Set properties
            tts_engine.setProperty('rate', 150)  # Speed of speech
            tts_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
            print("TTS engine initialized successfully")
        except Exception as e:
            print("Warning: Could not initialize TTS engine: {}".format(e))
            print("Commands will be printed but not spoken")
            tts_engine = None
    return tts_engine

def format_command_for_speech(command):
    """Format command text to be clearer when spoken by TTS using OpenAI"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return command  # Return original if no API key
    
    url = OPENAI_API_BASE_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    
    prompt = """Convert this robot command into a clear, natural-sounding announcement for text-to-speech.
Make it sound like a robot is announcing what it's about to do.
Keep it short and clear. Use present continuous tense (e.g., "Moving forward", "Turning right").
If there are numbers, convert small ones to words (1->one, 2->two, etc.) for better speech.
Translate to English if the command is in another language.
Only return the formatted announcement, nothing else.

Examples:
- "move forward 1 meter" -> "Moving forward one meter"
- "gira 90 grados a la derecha" -> "Turning right ninety degrees"
- "avanza hacia adelante" -> "Moving forward"
- "stop" -> "Stopping"

Command: {}""".format(command)
    
    data = {
        "model": OPENAI_MODEL_UTILITY,
        "instructions": "You are a text formatter for robot voice announcements. Convert commands to clear, natural speech.",
        "input": prompt,
        "temperature": 0.3,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            formatted = extract_text_from_responses(result)
            if formatted:
                formatted = formatted.strip()
                # Remove quotes if present
                formatted = formatted.strip('"').strip("'")
                return formatted
    except:
        pass  # If formatting fails, return original
    
    # Fallback: simple formatting
    command_lower = command.lower().strip()
    replacements = {
        'move forward': 'Moving forward',
        'go forward': 'Going forward',
        'avanza': 'Moving forward',
        'advance': 'Advancing',
        'move backward': 'Moving backward',
        'go back': 'Going back',
        'retrocede': 'Moving backward',
        'reverse': 'Reversing',
        'turn left': 'Turning left',
        'gira a la izquierda': 'Turning left',
        'turn right': 'Turning right',
        'gira a la derecha': 'Turning right',
        'rotate': 'Rotating',
        'stop': 'Stopping',
        'para': 'Stopping',
    }
    
    formatted = command
    for pattern, replacement in replacements.items():
        if pattern in command_lower:
            formatted = formatted.replace(pattern, replacement)
            break
    
    return formatted

def translate_to_english_for_speech(text):
    """Translate text to English for TTS announcements"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return text  # Return original if no API key
    
    url = OPENAI_API_BASE_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    
    data = {
        "model": OPENAI_MODEL_UTILITY,
        "instructions": (
            "You are a translator. Translate the given text to English. "
            "If the text is already in English, return it unchanged. "
            "Only return the translated text, no explanations, no additional text."
        ),
        "input": text,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            translated = extract_text_from_responses(result)
            if translated:
                return translated.strip()
    except:
        pass  # If translation fails, return original
    
    return text  # Return original if translation fails

def speak(text):
    """Speak the given text using TTS (non-blocking). Always translates to English first."""
    if not TTS_AVAILABLE:
        return  # TTS not available, skip voice announcement
    
    # Always translate to English first
    english_text = translate_to_english_for_speech(text)
    
    # Format command for clearer speech
    formatted_text = format_command_for_speech(english_text)
    
    def _speak():
        with tts_lock:
            engine = init_tts()
            if engine is not None:
                try:
                    engine.say(formatted_text)
                    engine.runAndWait()
                except Exception as e:
                    print("TTS Error: {}".format(e))

    # Run TTS in a separate thread to avoid blocking
    thread = threading.Thread(target=_speak)
    thread.daemon = True
    thread.start()
    # Give it a moment to start speaking
    time.sleep(0.3)

def load_system_prompt():
    with open(os.path.join(os.path.dirname(__file__), "prompts", "system.txt"), "r", encoding='utf-8') as f:
        return f.read()

def validate_command(command):
    """Validate if command is a valid robot movement command and return response if invalid"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        return {"valid": True, "message": None}  # Skip validation if no API key
    
    url = OPENAI_API_BASE_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    
    prompt = """Determine if this is a valid robot movement command. A valid command is one that instructs a mobile robot to move, rotate, or navigate (e.g., "move forward", "turn left", "go back 2 meters", "rotate 90 degrees").

If the command is NOT a movement command (e.g., questions, general knowledge, non-robot actions), respond with JSON:
{"valid": false, "message": "I didn't understand that command. I can only execute movement instructions. Try commands like: move forward, turn left, go back, rotate 90 degrees, advance 1 meter, etc."}

If the command IS a valid movement command, respond with JSON:
{"valid": true}

Command: {}""".format(command)
    
    data = {
        "model": OPENAI_MODEL_MOVEMENT,
        "instructions": "You are a validator for robot movement commands. Respond ONLY with valid JSON, no additional text.",
        "input": prompt,
        "temperature": 0.3,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            content = extract_text_from_responses(result)
            if not content:
                return {"valid": True, "message": None}
            content = content.strip()
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            content = content.strip()
            validation_result = json.loads(content)
            return validation_result
    except:
        pass  # If validation fails, assume valid and proceed
    
    return {"valid": True, "message": None}  # Default to valid if validation fails

def ask_llm_for_twist(command, system_prompt):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return {
            "linear": {"x": 0, "y": 0, "z": 0},
            "angular": {"x": 0, "y": 0, "z": 0},
            "metadata": {"distance_meters": None, "angle_degrees": None, "duration_seconds": 2.0}
        }
    
    # Check API key format
    if not api_key.startswith('sk-'):
        print("Warning: API key doesn't start with 'sk-', might be invalid")
    
    url = OPENAI_API_BASE_URL
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    data = {
        "model": OPENAI_MODEL_MOVEMENT,
        "instructions": system_prompt,
        "input": command,
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        # Check for authentication errors
        if response.status_code == 401:
            print("Error: Authentication failed - Invalid API key")
            try:
                error_data = response.json()
                print("Error details: {}".format(error_data))
            except:
                print("Error response: {}".format(response.text))
            return {
                "linear": {"x": 0, "y": 0, "z": 0},
                "angular": {"x": 0, "y": 0, "z": 0},
                "metadata": {"distance_meters": None, "angle_degrees": None, "duration_seconds": 2.0}
            }
        elif response.status_code == 403:
            print("Error: Access forbidden - API key may not have permission")
            try:
                error_data = response.json()
                print("Error details: {}".format(error_data))
            except:
                print("Error response: {}".format(response.text))
            return {
                "linear": {"x": 0, "y": 0, "z": 0},
                "angular": {"x": 0, "y": 0, "z": 0},
                "metadata": {"distance_meters": None, "angle_degrees": None, "duration_seconds": 2.0}
            }
        elif response.status_code == 429:
            print("Error: Rate limit exceeded - Too many requests")
            return {
                "linear": {"x": 0, "y": 0, "z": 0},
                "angular": {"x": 0, "y": 0, "z": 0},
                "metadata": {"distance_meters": None, "angle_degrees": None, "duration_seconds": 2.0}
            }
        
        response.raise_for_status()
        result = response.json()
        
        content = extract_text_from_responses(result)
        if not content:
            raise ValueError("Empty content from Responses API")
        
        content = content.strip()
        
        # If the model wraps in ```json, reuse the cleanup logic
        if content.startswith('```'):
            parts = content.split('```')
            if len(parts) >= 2:
                content = parts[1].strip()
                if content.startswith('json'):
                    content = content[4:].strip()
        
        return json.loads(content)
    except requests.exceptions.RequestException as e:
        print("Error making API request: {}".format(e))
        if hasattr(e, 'response') and e.response is not None:
            print("Response status code: {}".format(e.response.status_code))
            try:
                error_data = e.response.json()
                print("Error response: {}".format(error_data))
            except:
                print("Error response text: {}".format(e.response.text))
        return {
            "linear": {"x": 0, "y": 0, "z": 0},
            "angular": {"x": 0, "y": 0, "z": 0},
            "metadata": {"distance_meters": None, "angle_degrees": None, "duration_seconds": 2.0}
        }
    except (KeyError, ValueError) as e:
        print("Error parsing API response: {}".format(e))
        if 'result' in locals():
            try:
                content = extract_text_from_responses(result)
                print("Response content: {}".format(content if content else 'N/A'))
            except:
                print("Response content: N/A")
        return {
            "linear": {"x": 0, "y": 0, "z": 0},
            "angular": {"x": 0, "y": 0, "z": 0},
            "metadata": {"distance_meters": None, "angle_degrees": None, "duration_seconds": 2.0}
        }
    except Exception as e:
        print("Unexpected error: {}".format(e))
        import traceback
        traceback.print_exc()
        return {
            "linear": {"x": 0, "y": 0, "z": 0},
            "angular": {"x": 0, "y": 0, "z": 0},
            "metadata": {"distance_meters": None, "angle_degrees": None, "duration_seconds": 2.0}
        }

def execute_sequence(commands):
    rospy.init_node('llm_multi_command_controller')
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    rate = rospy.Rate(10)  # 10Hz for smoother control
    system_prompt = load_system_prompt()

    for cmd in commands:
        safe_print("Executing: {}".format(cmd))
        
        # Validate command before executing
        validation = validate_command(cmd)
        if not validation.get("valid", True):
            message = validation.get("message", "I didn't understand that command. Please provide a movement instruction.")
            safe_print("\n⚠️  {}".format(message))
            # Announce error via TTS
            speak("I didn't understand that command. Please provide a movement instruction.")
            print("")  # Empty line for readability
            continue  # Skip this command and move to next
        
        # Announce the command via TTS
        speak(cmd)

        twist_data = ask_llm_for_twist(cmd, system_prompt)
        
        # Check if the command resulted in zero movement (might be invalid)
        if (twist_data['linear']['x'] == 0 and twist_data['angular']['z'] == 0 and 
            twist_data.get('metadata', {}).get('duration_seconds', 0) <= 0.1):
            # This might be an invalid command that was converted to stop
            # Double-check with validation
            validation = validate_command(cmd)
            if not validation.get("valid", True):
                message = validation.get("message", "I didn't understand that command. Please provide a movement instruction.")
                safe_print("\n⚠️  {}".format(message))
                # Announce error via TTS
                speak("I didn't understand that command. Please provide a movement instruction.")
                print("")  # Empty line for readability
                continue

        # Extract metadata
        metadata = twist_data.get('metadata', {})
        duration = metadata.get('duration_seconds', 2.0)
        distance = metadata.get('distance_meters')
        angle = metadata.get('angle_degrees')

        # Debug output
        print("Debug: Generated Twist - linear.x: {}, angular.z: {}".format(
            twist_data['linear']['x'], twist_data['angular']['z']))
        if distance is not None:
            print("Debug: Target distance: {} meters".format(distance))
        if angle is not None:
            print("Debug: Target angle: {} degrees".format(angle))
        print("Debug: Execution duration: {} seconds".format(duration))

        # Create and publish Twist message
        twist = Twist()
        twist.linear.x = twist_data['linear']['x']
        twist.linear.y = twist_data['linear']['y']
        twist.linear.z = twist_data['linear']['z']
        twist.angular.x = twist_data['angular']['x']
        twist.angular.y = twist_data['angular']['y']
        twist.angular.z = twist_data['angular']['z']

        # Execute for the specified duration
        start_time = time.time()
        while (time.time() - start_time) < duration:
            pub.publish(twist)
            rate.sleep()

        # Stop after each step
        pub.publish(Twist())
        # time.sleep(0.1)  # Optional pause between commands (commented for instant transitions)

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 70)
    print("Robot Text Controller with Voice Notifications - Continuous Mode")
    print("=" * 70)
    print("Enter commands in English or Spanish")
    print("The robot will announce each action before executing")
    print("")
    print("Type 'exit', 'quit', or 'salir' to stop")
    print("Press Ctrl+C to force exit")
    print("=" * 70)
    print("")

    # Initialize TTS and greet user
    print("Initializing robot controller...")
    init_tts()
    time.sleep(0.5)  # Give TTS time to initialize
    
    # Greet user with voice announcement
    greeting = "Robot ready. Waiting for commands."
    print(greeting)
    speak(greeting)
    time.sleep(1.0)  # Wait for greeting to finish speaking
    print("")

    try:
        while not should_exit:
            # Get user input
            try:
                user_input = input("Enter command: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\nInterrupted - Exiting...")
                speak("Deteniendo")
                break

            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'salir', 'terminar', 'cerrar']:
                print("\nExiting robot controller...")
                speak("Adios")
                break

            # Skip empty input
            if not user_input:
                continue

            # Process command
            safe_print("\nProcessing: {}".format(user_input))
            steps = split_into_steps(user_input)
            safe_print("Steps: {}".format(steps))

            # Execute sequence
            try:
                execute_sequence(steps)
            except (KeyboardInterrupt, rospy.ROSInterruptException):
                print("\n\nInterrupted during execution - Stopping...")
                speak("Deteniendo")
                break

            print("\nSequence completed!")
            print("-" * 70)
            print("")

    except KeyboardInterrupt:
        print("\n\nCtrl+C detected - Stopping controller...")
        speak("Deteniendo")
        print("Goodbye!")
    except Exception as e:
        print("\nError: {}".format(e))
        import traceback
        traceback.print_exc()
    finally:
        print("\nShutting down...")
        sys.exit(0)
