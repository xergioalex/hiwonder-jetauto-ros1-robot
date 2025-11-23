import rospy
from geometry_msgs.msg import Twist
import requests
import json
import time
import os
from dotenv import load_dotenv
from parser_llm import split_into_steps
import pyttsx3
import threading

# Load environment variables from .env file in repo root
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv(os.path.join(repo_root, '.env'))

# Initialize TTS engine (global to avoid reinitializing on each call)
tts_engine = None
tts_lock = threading.Lock()

def init_tts():
    """Initialize the TTS engine with proper settings"""
    global tts_engine
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

def speak(text):
    """Speak the given text using TTS (non-blocking)"""
    def _speak():
        with tts_lock:
            engine = init_tts()
            if engine is not None:
                try:
                    engine.say(text)
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
        print("Executing: {}".format(cmd))

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
    user_input = input("Enter a multi-step command (English or Spanish): ")
    steps = split_into_steps(user_input)
    print("Steps: {}".format(steps))
    execute_sequence(steps)
