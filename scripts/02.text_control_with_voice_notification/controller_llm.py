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
    
    url = "https://api.openai.com/v1/chat/completions"
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
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a text formatter for robot voice announcements. Convert commands to clear, natural speech."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                formatted = result['choices'][0]['message']['content'].strip()
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

def speak(text):
    """Speak the given text using TTS (non-blocking)"""
    if not TTS_AVAILABLE:
        return  # TTS not available, skip voice announcement
    
    # Format command for clearer speech
    formatted_text = format_command_for_speech(text)
    
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
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {}".format(api_key)
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command}
        ]
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
        
        if 'choices' not in result or len(result['choices']) == 0:
            print("Error: No choices in API response")
            return {
                "linear": {"x": 0, "y": 0, "z": 0},
                "angular": {"x": 0, "y": 0, "z": 0},
                "metadata": {"distance_meters": None, "angle_degrees": None, "duration_seconds": 2.0}
            }
        
        content = result['choices'][0]['message']['content']
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
            print("Response content: {}".format(result.get('choices', [{}])[0].get('message', {}).get('content', 'N/A')))
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

        # Announce the command via TTS
        speak(cmd)

        twist_data = ask_llm_for_twist(cmd, system_prompt)

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
