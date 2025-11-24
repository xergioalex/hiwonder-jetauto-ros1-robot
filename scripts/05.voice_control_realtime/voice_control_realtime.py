import rospy
from geometry_msgs.msg import Twist
import requests
import json
import time
import os
import signal
import sys
import asyncio
import websockets
import base64
import threading
from dotenv import load_dotenv
from parser_llm import split_into_steps

# Try to import audio libraries
try:
    import sounddevice as sd
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError as e:
    print("Warning: Audio libraries not available ({}). Voice recording will be disabled.".format(e))
    print("Install with: pip install sounddevice numpy")
    AUDIO_AVAILABLE = False
    sd = None
    np = None

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

# OpenAI API constants
OPENAI_API_BASE_URL = "https://api.openai.com/v1/responses"
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17"
OPENAI_MODEL_MOVEMENT = "gpt-5-mini"  # for movement commands
OPENAI_MODEL_UTILITY = "gpt-5-mini"   # for translation / parsing of steps

# Audio parameters for Realtime API
REALTIME_SAMPLE_RATE = 24000  # 24kHz required by Realtime API
REALTIME_CHANNELS = 1  # Mono
REALTIME_DTYPE = 'int16'  # 16-bit PCM
REALTIME_FRAME_SIZE = 480  # 20ms frames at 24kHz (24000 * 0.02 = 480)

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

# Global variables for Realtime API connection
realtime_ws = None
realtime_connected = False
realtime_transcript_queue = asyncio.Queue()
audio_stream = None

async def send_audio_loop(websocket):
    """Send audio chunks to Realtime API WebSocket"""
    global audio_stream, should_exit
    
    if not AUDIO_AVAILABLE:
        print("Error: Audio libraries not available")
        return
    
    try:
        # Open audio input stream
        audio_stream = sd.InputStream(
            samplerate=REALTIME_SAMPLE_RATE,
            channels=REALTIME_CHANNELS,
            dtype=REALTIME_DTYPE,
            blocksize=REALTIME_FRAME_SIZE
        )
        audio_stream.start()
        
        safe_print("🎤 Audio stream started, sending to Realtime API...")
        
        while not should_exit:
            # Read audio chunk
            audio_chunk, overflowed = audio_stream.read(REALTIME_FRAME_SIZE)
            
            if overflowed:
                safe_print("⚠️  Audio buffer overflow")
            
            # Convert to bytes
            audio_bytes = audio_chunk.tobytes()
            
            # Encode to base64
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            # Send to WebSocket
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                safe_print("⚠️  WebSocket connection closed during audio send")
                break
            except Exception as e:
                print("Error sending audio: {}".format(e))
                break
            
            # Small delay to match frame rate
            await asyncio.sleep(0.02)  # 20ms per frame
            
    except Exception as e:
        print("Error in audio send loop: {}".format(e))
        import traceback
        traceback.print_exc()
    finally:
        if audio_stream is not None:
            audio_stream.stop()
            audio_stream.close()
            print("Audio stream closed")

async def receive_events_loop(websocket):
    """Receive events from Realtime API WebSocket"""
    global realtime_transcript_queue, should_exit
    
    try:
        async for message in websocket:
            if should_exit:
                break
            
            try:
                event = json.loads(message)
                event_type = event.get("type")
                
                # Handle different event types
                if event_type == "input_audio_buffer.speech_started":
                    safe_print("🎤 Speech started")
                    speak("Listening")
                
                elif event_type == "input_audio_buffer.speech_stopped":
                    safe_print("✓ Speech stopped")
                
                elif event_type == "input_audio_buffer.committed":
                    # Partial transcript available
                    transcript = event.get("delta", "")
                    if transcript:
                        print("Partial: {}".format(transcript), end="\r")
                
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # Final transcript available
                    transcript = event.get("transcript", "")
                    if transcript:
                        safe_print("\n✓ Final transcript: {}".format(transcript))
                        # Put transcript in queue for processing
                        await realtime_transcript_queue.put(transcript)
                
                elif event_type == "error":
                    error = event.get("error", {})
                    print("Error from Realtime API: {}".format(error))
                
                elif event_type == "session.updated":
                    # Session configuration confirmed
                    safe_print("✓ Session configured")
                
            except json.JSONDecodeError as e:
                print("Error parsing WebSocket message: {}".format(e))
            except Exception as e:
                print("Error processing event: {}".format(e))
                
    except websockets.exceptions.ConnectionClosed:
        safe_print("⚠️  WebSocket connection closed")
    except Exception as e:
        print("Error in receive loop: {}".format(e))
        import traceback
        traceback.print_exc()

async def process_transcripts_loop():
    """Process transcripts from the queue and execute commands"""
    global should_exit
    
    while not should_exit:
        try:
            # Wait for transcript with timeout
            transcript = await asyncio.wait_for(
                realtime_transcript_queue.get(),
                timeout=1.0
            )
            
            if transcript:
                # Announce recognized command
                safe_print("\n✓ Recognized: {}".format(transcript))
                speak("I heard: {}".format(transcript))
                await asyncio.sleep(0.5)
                
                # Process command in a thread to avoid blocking
                def process_command():
                    safe_print("\nProcessing: {}".format(transcript))
                    steps = split_into_steps(transcript)
                    safe_print("Steps: {}".format(steps))
                    
                    # Execute sequence
                    try:
                        execute_sequence(steps)
                    except (KeyboardInterrupt, rospy.ROSInterruptException):
                        print("\n\nInterrupted during execution - Stopping...")
                        speak("Deteniendo")
                
                # Run in thread pool to avoid blocking async loop
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, process_command)
                
                print("\nSequence completed!")
                print("-" * 70)
                print("")
                
        except asyncio.TimeoutError:
            # No transcript received, continue waiting
            continue
        except Exception as e:
            print("Error processing transcript: {}".format(e))
            import traceback
            traceback.print_exc()

async def connect_realtime_api():
    """Connect to OpenAI Realtime API and handle reconnection"""
    global realtime_ws, realtime_connected, should_exit
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return
    
    max_retries = 5
    retry_delay = 2
    
    while not should_exit:
        try:
            print("Connecting to OpenAI Realtime API...")
            
            # Connect to WebSocket with authentication
            headers = {
                "Authorization": "Bearer {}".format(api_key),
                "OpenAI-Beta": "realtime=v1"
            }
            
            async with websockets.connect(
                OPENAI_REALTIME_URL,
                extra_headers=headers
            ) as websocket:
                realtime_ws = websocket
                realtime_connected = True
                safe_print("✓ Connected to Realtime API")
                
                # Configure session for transcription
                session_config = {
                    "type": "session.update",
                    "session": {
                        "input_audio_transcription": {
                            "model": "gpt-4o-mini-transcribe"
                        }
                    }
                }
                await websocket.send(json.dumps(session_config))
                
                # Start audio sending and event receiving tasks
                send_task = asyncio.create_task(send_audio_loop(websocket))
                receive_task = asyncio.create_task(receive_events_loop(websocket))
                process_task = asyncio.create_task(process_transcripts_loop())
                
                # Wait for any task to complete (or fail)
                done, pending = await asyncio.wait(
                    [send_task, receive_task, process_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                
                realtime_connected = False
                
                if should_exit:
                    break
                
                safe_print("⚠️  Connection lost, reconnecting in {} seconds...".format(retry_delay))
                await asyncio.sleep(retry_delay)
                
        except websockets.exceptions.InvalidStatusCode as e:
            print("Error: Invalid status code - {}".format(e))
            if e.status_code == 401:
                print("Authentication failed - Check your API key")
                break
            elif e.status_code == 403:
                print("Access forbidden - API key may not have permission")
                break
        except Exception as e:
            print("Error connecting to Realtime API: {}".format(e))
            import traceback
            traceback.print_exc()
            
            if should_exit:
                break
            
            max_retries -= 1
            if max_retries <= 0:
                print("Max retries reached. Exiting.")
                break
            
            print("Retrying in {} seconds... ({} retries left)".format(retry_delay, max_retries))
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30)  # Exponential backoff, max 30s

def run_async_main():
    """Run the async main function"""
    try:
        asyncio.run(connect_realtime_api())
    except KeyboardInterrupt:
        print("\n\nInterrupted - Exiting...")
    except Exception as e:
        print("Error in async main: {}".format(e))
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 70)
    print("Robot Voice Controller - Realtime API Mode")
    print("=" * 70)
    print("Using OpenAI Realtime API for streaming voice recognition")
    print("Speak naturally - the robot will process your commands in real-time")
    print("")
    safe_print("⚠️  NOTE: This script requires Python 3.9+")
    print("   If running on JetAuto (Python 3.6), consider running on a laptop")
    print("   and sending commands to the robot via ROS topics or HTTP")
    print("")
    print("Press Ctrl+C to exit")
    print("=" * 70)
    print("")

    # Check Python version
    if sys.version_info < (3, 9):
        safe_print("⚠️  WARNING: Python 3.9+ required for Realtime API")
        print("   Current version: {}.{}.{}".format(
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro
        ))
        print("   The script may not work correctly.")
        print("   Consider using Script 03 (Push-to-Talk) or Script 04 (VAD) instead.")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
        print("")

    # Initialize TTS and greet user
    print("Initializing robot controller...")
    init_tts()
    time.sleep(0.5)  # Give TTS time to initialize
    
    # Check audio availability
    if not AUDIO_AVAILABLE:
        safe_print("⚠️  Error: Audio libraries not available.")
        print("   Install with: pip install sounddevice numpy")
        sys.exit(1)
    
    # Greet user with voice announcement
    greeting = "Realtime voice recognition ready. Listening for commands."
    print(greeting)
    speak(greeting)
    time.sleep(1.5)  # Wait for greeting to finish speaking
    print("")

    try:
        # Run async main
        run_async_main()
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
        should_exit = True
        sys.exit(0)

