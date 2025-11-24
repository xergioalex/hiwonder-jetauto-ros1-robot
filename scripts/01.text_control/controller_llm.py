import rospy
from geometry_msgs.msg import Twist
import requests
import json
import time
import os
import signal
import sys
from dotenv import load_dotenv
from parser_llm import split_into_steps

# Global flag for clean exit
should_exit = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global should_exit
    print("\n\nCtrl+C detected - Stopping controller...")
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
    Expects the standard format:
      result["output"][0]["content"][0]["text"]
    """
    try:
        return result["output"][0]["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        print("Error extracting text from Responses API result: {}".format(e))
        return None

def safe_print(message):
    """Print message safely, handling Unicode encoding errors"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: remove non-ASCII characters
        print(message.encode('ascii', 'ignore').decode('ascii'))

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
            print("")  # Empty line for readability
            continue  # Skip this command and move to next
        
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
    print("Robot Text Controller - Continuous Mode")
    print("=" * 70)
    print("Enter commands in English or Spanish")
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
                break

            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'salir', 'terminar', 'cerrar']:
                print("\nExiting robot controller...")
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
                break

            print("\nSequence completed!")
            print("-" * 70)
            print("")

    except KeyboardInterrupt:
        print("\n\nCtrl+C detected - Stopping controller...")
        print("Goodbye!")
    except Exception as e:
        print("\nError: {}".format(e))
        import traceback
        traceback.print_exc()
    finally:
        print("\nShutting down...")
        sys.exit(0)
