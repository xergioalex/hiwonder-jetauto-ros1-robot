import rospy
from geometry_msgs.msg import Twist
import requests
import json
import time
import os
import signal
import sys
import tempfile
import threading
from dotenv import load_dotenv
from parser_llm import split_into_steps

# Try to import audio libraries
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError as e:
    print("Warning: Audio libraries not available ({}). Voice recording will be disabled.".format(e))
    print("Install with: pip install sounddevice soundfile numpy")
    AUDIO_AVAILABLE = False
    sd = None
    sf = None
    np = None

# Try to import WebRTC VAD
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError as e:
    print("Warning: WebRTC VAD not available ({}). VAD will be disabled.".format(e))
    print("Install with: pip install webrtcvad-wheels")
    VAD_AVAILABLE = False
    webrtcvad = None

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
OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_MODEL_MOVEMENT = "gpt-5-mini"  # for movement commands
OPENAI_MODEL_UTILITY = "gpt-5-mini"   # for translation / parsing of steps
OPENAI_STT_MODEL = "gpt-4o-mini-transcribe"  # for speech-to-text

# VAD parameters
VAD_SAMPLE_RATE = 16000  # 16kHz required by WebRTC VAD
VAD_FRAME_SIZE_MS = 20   # 20ms frames
VAD_FRAME_SIZE = int(VAD_SAMPLE_RATE * VAD_FRAME_SIZE_MS / 1000)  # 320 samples
VAD_AGGRESSIVENESS = 2  # 0=least aggressive, 3=most aggressive (2 is balanced)
VAD_SILENCE_THRESHOLD_MS = 500  # Stop after 500ms of silence
VAD_SILENCE_FRAMES = int(VAD_SILENCE_THRESHOLD_MS / VAD_FRAME_SIZE_MS)  # 25 frames
VAD_MAX_DURATION_SEC = 10  # Maximum recording duration (safety limit)

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
    # Initialize ROS node only if not already initialized
    try:
        rospy.init_node('llm_multi_command_controller', anonymous=True)
    except rospy.ROSException:
        # Node already initialized, continue
        pass
    
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    rate = rospy.Rate(10)  # 10Hz for smoother control
    system_prompt = load_system_prompt()

    for cmd in commands:
        if rospy.is_shutdown():
            print("ROS shutdown detected, stopping execution")
            break
            
        safe_print("Executing: {}".format(cmd))
        
        # Validate command before executing
        try:
            validation = validate_command(cmd)
            if not validation.get("valid", True):
                message = validation.get("message", "I didn't understand that command. Please provide a movement instruction.")
                safe_print("\n⚠️  {}".format(message))
                # Announce error via TTS
                speak("I didn't understand that command. Please provide a movement instruction.")
                print("")  # Empty line for readability
                continue  # Skip this command and move to next
        except Exception as e:
            print("Error validating command: {}".format(e))
            continue
        
        # Announce the command via TTS
        speak(cmd)

        try:
            twist_data = ask_llm_for_twist(cmd, system_prompt)
        except Exception as e:
            print("Error getting twist data: {}".format(e))
            import traceback
            traceback.print_exc()
            continue
        
        # Check if the command resulted in zero movement (might be invalid)
        if (twist_data['linear']['x'] == 0 and twist_data['angular']['z'] == 0 and 
            twist_data.get('metadata', {}).get('duration_seconds', 0) <= 0.1):
            # This might be an invalid command that was converted to stop
            # Double-check with validation
            try:
                validation = validate_command(cmd)
                if not validation.get("valid", True):
                    message = validation.get("message", "I didn't understand that command. Please provide a movement instruction.")
                    safe_print("\n⚠️  {}".format(message))
                    # Announce error via TTS
                    speak("I didn't understand that command. Please provide a movement instruction.")
                    print("")  # Empty line for readability
                    continue
            except Exception as e:
                print("Error in validation: {}".format(e))
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
        try:
            start_time = time.time()
            while (time.time() - start_time) < duration:
                if rospy.is_shutdown():
                    break
                pub.publish(twist)
                rate.sleep()
        except Exception as e:
            print("Error during execution: {}".format(e))
            import traceback
            traceback.print_exc()

        # Stop after each step
        try:
            pub.publish(Twist())
            time.sleep(0.2)  # Brief pause between commands for safety
        except Exception as e:
            print("Error stopping robot: {}".format(e))

def listen_for_utterance_vad():
    """
    Listen for voice activity using WebRTC VAD.
    State machine: IDLE -> RECORDING -> ENDING
    Returns the path to the saved WAV file, or None if failed.
    """
    if not AUDIO_AVAILABLE or not VAD_AVAILABLE:
        print("Error: Audio or VAD libraries not available.")
        return None
    
    # Initialize VAD
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
    
    # State machine states
    IDLE = 0
    RECORDING = 1
    ENDING = 2
    
    # Use a class-like structure with mutable state for callback
    class VADState:
        def __init__(self):
            self.state = IDLE
            self.frames = []
            self.silence_frames = 0
            self.frame_count = 0
            self.max_frames = int(VAD_MAX_DURATION_SEC * VAD_SAMPLE_RATE / VAD_FRAME_SIZE)
            self.should_stop = False
    
    vad_state = VADState()
    
    def audio_callback(indata, frames_count, time_info, status):
        """Callback for audio stream processing"""
        if status:
            print("Audio status: {}".format(status))
        
        # Convert to int16 bytes for VAD
        frame_bytes = (indata * 32767).astype(np.int16).tobytes()
        
        # Check if frame contains speech
        is_speech = vad.is_speech(frame_bytes, VAD_SAMPLE_RATE)
        
        vad_state.frame_count += 1
        
        if vad_state.state == IDLE:
            if is_speech:
                # Speech detected, start recording
                vad_state.state = RECORDING
                vad_state.frames = [indata.copy()]
                vad_state.silence_frames = 0
                safe_print("🎤 Speech detected, recording...")
        elif vad_state.state == RECORDING:
            vad_state.frames.append(indata.copy())
            
            if is_speech:
                vad_state.silence_frames = 0  # Reset silence counter
            else:
                vad_state.silence_frames += 1
                # Check if we've had enough silence to end
                if vad_state.silence_frames >= VAD_SILENCE_FRAMES:
                    vad_state.state = ENDING
                    safe_print("✓ Silence detected, ending recording...")
            
            # Safety: check max duration
            if vad_state.frame_count >= vad_state.max_frames:
                safe_print("⚠️  Maximum duration reached ({} seconds)".format(VAD_MAX_DURATION_SEC))
                vad_state.state = ENDING
        elif vad_state.state == ENDING:
            # Collect a few more frames for smooth ending
            vad_state.frames.append(indata.copy())
            # Add small buffer frames then signal stop
            if len(vad_state.frames) >= vad_state.frame_count + 3:
                vad_state.should_stop = True
    
    try:
        safe_print("👂 Listening for voice...")
        speak("Listening")
        
        # Open audio input stream
        stream = sd.InputStream(samplerate=VAD_SAMPLE_RATE, 
                               channels=1, 
                               dtype='float32',
                               blocksize=VAD_FRAME_SIZE,
                               callback=audio_callback)
        stream.start()
        
        # Wait until recording is complete
        while vad_state.state != ENDING and vad_state.frame_count < vad_state.max_frames and not vad_state.should_stop:
            time.sleep(0.01)  # Small sleep to avoid CPU spinning
            if should_exit:
                stream.stop()
                stream.close()
                return None
        
        # Wait a bit more for ending frames
        if vad_state.state == ENDING:
            time.sleep(0.1)
        
        stream.stop()
        stream.close()
        
        if not vad_state.frames:
            safe_print("⚠️  No audio captured.")
            return None
        
        # Concatenate all frames
        audio_data = np.concatenate(vad_state.frames, axis=0)
        
        # Trim leading silence (optional)
        # Find first non-zero sample
        non_zero_indices = np.where(np.abs(audio_data) > 0.01)[0]
        if len(non_zero_indices) > 0:
            start_index = max(0, non_zero_indices[0] - int(0.1 * VAD_SAMPLE_RATE))  # Keep 100ms before
            audio_data = audio_data[start_index:]
        
        if len(audio_data) == 0:
            safe_print("⚠️  No audio data after trimming.")
            return None
        
        # Convert to int16 for saving
        audio_int16 = (audio_data * 32767).astype(np.int16)
        
        # Create temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_path = temp_file.name
        temp_file.close()
        
        # Save audio to WAV file
        sf.write(temp_path, audio_int16, VAD_SAMPLE_RATE)
        duration = len(audio_int16) / VAD_SAMPLE_RATE
        safe_print("✓ Audio captured: {:.2f} seconds".format(duration))
        
        return temp_path
        
    except Exception as e:
        print("Error during VAD recording: {}".format(e))
        import traceback
        traceback.print_exc()
        return None

def transcribe_audio(file_path, language_hint="es"):
    """
    Transcribe audio file using OpenAI Speech-to-Text API.
    
    Args:
        file_path: Path to the audio file (WAV format)
        language_hint: Language hint for transcription ("es" for Spanish, "en" for English)
    
    Returns:
        Transcribed text string, or None if transcription failed
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        return None
    
    if not os.path.exists(file_path):
        print("Error: Audio file not found: {}".format(file_path))
        return None
    
    url = OPENAI_STT_URL
    headers = {
        "Authorization": "Bearer {}".format(api_key)
    }
    
    # Prepare multipart form data
    try:
        with open(file_path, 'rb') as audio_file:
            files = {
                'file': (os.path.basename(file_path), audio_file, 'audio/wav')
            }
            data = {
                'model': OPENAI_STT_MODEL,
                'language': language_hint,
                'response_format': 'text'
            }
            
            safe_print("📤 Sending audio for transcription...")
            response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                transcript = response.text.strip()
                safe_print("✓ Transcription: {}".format(transcript))
                return transcript
            else:
                print("Error: Transcription failed with status code: {}".format(response.status_code))
                try:
                    error_data = response.json()
                    print("Error details: {}".format(error_data))
                except:
                    print("Error response: {}".format(response.text))
                return None
                
    except requests.exceptions.RequestException as e:
        print("Error making transcription request: {}".format(e))
        return None
    except Exception as e:
        print("Error during transcription: {}".format(e))
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up temporary file
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                print("Cleaned up temporary audio file")
        except:
            pass

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 70)
    print("Robot Voice Controller - Voice Activity Detection (VAD) Mode")
    print("=" * 70)
    print("The robot will continuously listen for voice commands.")
    print("Speak naturally - the robot will detect when you start and stop speaking.")
    print("")
    print("Press Ctrl+C to exit")
    print("=" * 70)
    print("")

    # Initialize TTS and greet user
    print("Initializing robot controller...")
    init_tts()
    time.sleep(0.5)  # Give TTS time to initialize
    
    # Check audio and VAD availability
    if not AUDIO_AVAILABLE:
        safe_print("⚠️  Error: Audio libraries not available.")
        print("   Install with: pip install sounddevice soundfile numpy")
        sys.exit(1)
    
    if not VAD_AVAILABLE:
        safe_print("⚠️  Error: WebRTC VAD not available.")
        print("   Install with: pip install webrtcvad-wheels")
        sys.exit(1)
    
    # Greet user with voice announcement
    greeting = "Voice activity detection ready. Listening for commands."
    print(greeting)
    speak(greeting)
    time.sleep(1.5)  # Wait for greeting to finish speaking
    print("")

    try:
        while not should_exit:
            # Listen for voice using VAD
            audio_file = listen_for_utterance_vad()
            
            if not audio_file:
                if should_exit:
                    break
                # Continue listening if no audio captured
                time.sleep(0.5)
                continue
            
            # Transcribe audio
            speak("Processing")
            transcript = transcribe_audio(audio_file, language_hint="es")
            
            if transcript:
                # Announce recognized command
                safe_print("\n✓ Recognized: {}".format(transcript))
                speak("I heard: {}".format(transcript))
                time.sleep(0.5)
                
                # Process command
                safe_print("\nProcessing: {}".format(transcript))
                steps = split_into_steps(transcript)
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
            else:
                safe_print("\n⚠️  Could not transcribe audio. Continuing to listen...")
                print("")
            
            # Small delay before next listening cycle
            time.sleep(0.3)

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

