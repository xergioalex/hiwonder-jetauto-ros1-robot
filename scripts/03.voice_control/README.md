# Voice Control - Push-to-Talk Mode

This script provides voice control for the JetAuto robot using a push-to-talk interface. Users can control the robot by either typing commands or using voice input with a simple push-to-talk mechanism.

## Overview

This script implements a complete voice-to-robot-control pipeline that:
1. Records audio when user presses ENTER (push-to-talk)
2. Transcribes speech to text using OpenAI STT API
3. Parses multi-step commands using GPT-5 Responses API
4. Executes robot movements via ROS with TTS announcements
5. **Always returns steps in English** regardless of input language
6. **Always speaks in English** via TTS translation

## Features

### Dual Input Modes
- **Text Input**: Type commands and press ENTER
- **Voice Input**: Press ENTER twice for push-to-talk recording
  - First ENTER: Start recording
  - Second ENTER: Stop recording

### Voice Processing Pipeline
- **Speech-to-Text**: OpenAI `gpt-4o-mini-transcribe` model
- **Multi-step Parsing**: GPT-5 Responses API with advanced prompt engineering
- **Automatic Translation**: Commands in Spanish are automatically translated to English
- **Step Extraction**: Complex commands are split into atomic, sequential steps

### Robot Control
- **GPT-5 Integration**: Uses `gpt-5-mini` for movement command interpretation
- **ROS Integration**: Publishes `geometry_msgs/Twist` to `/cmd_vel` topic
- **Multi-step Execution**: Executes commands sequentially with safety stops
- **Error Handling**: Robust error handling prevents silent failures

### Voice Announcements (TTS)
- **Non-blocking TTS**: Uses `pyttsx3` with `espeak` backend
- **Automatic Translation**: All TTS output is translated to English
- **Command Announcements**: Robot announces each command before execution
- **Status Messages**: Announces "Recording", "Processing", "I heard: [transcript]", etc.

## Requirements

### System Dependencies

```bash
# Install audio system libraries (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y portaudio19-dev libsndfile1 espeak espeak-data libespeak-dev
```

### Python Dependencies

**Note**: This script is compatible with Python 3.6+ (JetAuto's default Python version).

```bash
pip install -r requirements.txt
```

Dependencies (with Python 3.6 compatibility):
- `requests>=2.20.0` - HTTP requests for OpenAI API
- `python-dotenv>=0.19.0` - Environment variable management
- `pyttsx3==2.7` - Text-to-speech
- `sounddevice>=0.4.0,<0.4.5` - Audio recording (0.4.4 is last version for Python 3.6)
- `soundfile>=0.10.0,<0.12.0` - Audio file I/O (compatible with Python 3.6)
- `numpy>=1.16.0,<1.20.0` - Numerical operations (compatible with Python 3.6)

### Environment Variables

Create a `.env` file in the **repository root** (not in this script directory) with:

```
OPENAI_API_KEY=your_openai_api_key_here
```

The script automatically loads the `.env` file from the repository root.

## Usage

### Basic Usage

```bash
# Make sure ROS master is running
roscore

# Run the voice controller
cd scripts/03.voice_control
python3 voice_control_push_to_talk.py
```

### Input Methods

#### Text Input
1. Type your command (e.g., "move forward 1 meter" or "avanza un metro")
2. Press ENTER
3. Robot executes the command

#### Voice Input (Push-to-Talk)
1. Press ENTER (first time) - starts recording
2. Speak your command (e.g., "avanza un metro y gira a la derecha")
3. Press ENTER (second time) - stops recording
4. Robot processes the transcribed command and executes it

### Example Commands

**English:**
- "move forward 2 meters"
- "turn left 90 degrees"
- "go back 1 meter, then turn right"
- "advance 50 cm, then turn right, then advance 60 cm, then turn right again, then advance diagonally to the right and finally turn left"

**Spanish:**
- "avanza un metro"
- "gira 90 grados a la izquierda"
- "retrocede medio metro y luego gira a la derecha"
- "avanza y luego retrocede"

**Note**: All commands are automatically translated to English internally, and steps are always returned in English.

### Exit

Type `exit`, `quit`, or `salir` to stop the controller, or press Ctrl+C.

## How It Works

### Complete Pipeline Flow

1. **User Input**:
   - Text: User types command and presses ENTER
   - Voice: User presses ENTER → speaks → presses ENTER again

2. **Audio Recording** (voice mode only):
   - Records at 16kHz mono, 16-bit PCM
   - Saves to temporary WAV file
   - Automatically cleaned up after transcription

3. **Speech-to-Text** (voice mode only):
   - Sends audio to OpenAI STT API (`gpt-4o-mini-transcribe`)
   - Returns transcribed text
   - Announces transcription via TTS: "I heard: [transcript]"

4. **Translation** (if needed):
   - Detects Spanish indicators: 'avanza', 'retrocede', 'gira', 'luego', etc.
   - Translates to English using GPT-5 Responses API
   - Ensures consistent English processing

5. **Multi-step Parsing**:
   - Uses GPT-5 Responses API with `multi_step_parser.txt` prompt
   - **Prompt forces English output** regardless of input language
   - Splits complex commands into numbered steps
   - Example: "Avanza y luego retrocede" → ["Move forward", "Move backward"]

6. **Command Validation**:
   - Validates each step using GPT-5
   - Skips invalid commands with error messages

7. **Movement Generation**:
   - Each step is converted to ROS Twist via GPT-5 Responses API
   - Uses `system.txt` prompt with calibration factors
   - Returns JSON with velocities and metadata (distance, angle, duration)

8. **Execution**:
   - Publishes Twist commands at 10Hz
   - Executes for calculated duration (with calibration factors)
   - Stops between commands (0.2 second pause)
   - Announces each command via TTS (translated to English)

9. **Safety**:
   - Automatically adds "stop" command at end of sequences
   - Handles errors gracefully without crashing
   - Checks ROS shutdown status

## Technical Architecture

### Key Components

1. **`voice_control_push_to_talk.py`**:
   - Main controller script
   - Handles audio recording, transcription, and ROS integration
   - Manages TTS announcements

2. **`parser_llm.py`**:
   - Multi-step command parser
   - Translation functions
   - GPT-5 Responses API integration

3. **`prompts/system.txt`**:
   - GPT-5 prompt for converting commands to ROS Twist
   - Includes calibration factors (2.5x for linear, 2.0x for angular)
   - 30+ examples for various command types

4. **`prompts/multi_step_parser.txt`**:
   - GPT-5 prompt for splitting commands into steps
   - **Forces English output** regardless of input language
   - Handles temporal connectors, conjunctions, patterns
   - 15+ example categories

### API Integration

#### OpenAI Responses API
- **Endpoint**: `https://api.openai.com/v1/responses`
- **Model**: `gpt-5-mini`
- **Format**: `instructions` + `input` (not `messages`)
- **Response Parsing**: Handles multiple response formats including metadata dicts

#### OpenAI STT API
- **Endpoint**: `https://api.openai.com/v1/audio/transcriptions`
- **Model**: `gpt-4o-mini-transcribe`
- **Format**: Multipart form data with WAV file
- **Language Hint**: "es" (Spanish) for better transcription

### Response Parsing Improvements

The `extract_text_from_responses()` function handles multiple response formats:
- Standard: `result["output"][0]["content"][0]["text"]`
- Alternative: `result["output"][0]["text"]`
- Metadata skip: Iterates through `output` array, skipping metadata dicts
- Direct text: `result["text"]`

This robust parsing handles API response variations gracefully.

## Audio Configuration

The script uses the following audio settings:
- **Sample Rate**: 16,000 Hz (required by OpenAI STT)
- **Channels**: Mono (1 channel)
- **Format**: 16-bit PCM (int16)
- **File Format**: WAV
- **Recording Method**: Blocking recording with callback-based approach

## Problems Solved & Lessons Learned

### 1. Python 3.6 Compatibility
**Problem**: `sounddevice>=0.4.6` not available for Python 3.6
**Solution**: Use `sounddevice>=0.4.0,<0.4.5` (0.4.4 is last compatible version)
**Lesson**: Always check Python version compatibility for dependencies

### 2. Unicode Encoding Errors
**Problem**: Emojis in print statements caused `UnicodeEncodeError` on systems with limited Unicode support
**Solution**: Use `safe_print()` function that handles Unicode encoding errors gracefully
**Lesson**: Always use safe printing functions for cross-platform compatibility

### 3. Responses API Parsing
**Problem**: API responses had metadata dicts in `output[0]`, causing parsing failures
**Solution**: Iterate through all `output` items, skip metadata dicts (with 'format', 'verbosity' keys)
**Lesson**: API responses can have varying structures; always handle multiple formats

### 4. JSON Braces in Prompts
**Problem**: `validate_command()` prompt had `{}` that Python interpreted as `.format()` placeholders
**Solution**: Escape braces as `{{` and `}}` in prompt strings
**Lesson**: Always escape literal braces in Python format strings

### 5. Multi-step Execution Failures
**Problem**: Only first command executed, subsequent commands failed silently
**Solution**: 
- Initialize ROS node with `anonymous=True`
- Add robust error handling with try/except
- Add `rospy.is_shutdown()` checks
- Add 0.2 second pause between commands
**Lesson**: Always handle ROS node initialization and add safety pauses

### 6. Spanish Steps in Output
**Problem**: Steps were returned in Spanish ("Avanza", "Retrocede") instead of English
**Solution**:
- Updated `multi_step_parser.txt` prompt to force English output
- Improved `translate_to_english()` to detect Spanish indicators
- Added explicit instruction: "ALL OUTPUT STEPS MUST BE IN ENGLISH"
**Lesson**: Prompt engineering is critical; be explicit about output requirements

### 7. TTS Language Consistency
**Problem**: Robot spoke in Spanish when commands were in Spanish
**Solution**: Added `translate_to_english_for_speech()` function that always translates before TTS
**Lesson**: Separate translation concerns - translate for processing AND for output

## Troubleshooting

### Audio Not Working

If you see "Audio libraries not available":
```bash
# Install system dependencies
sudo apt-get install portaudio19-dev libsndfile1

# Reinstall Python packages
pip install --upgrade sounddevice soundfile numpy
```

### No Microphone Detected

Check available audio devices:
```python
import sounddevice as sd
print(sd.query_devices())
```

Set default input device in your system audio settings.

### Transcription Errors

- Check your OpenAI API key is valid and has credits
- Ensure microphone is working and not muted
- Try speaking more clearly and closer to the microphone
- Check internet connection for API calls
- Verify audio file is being created (check `/tmp/` directory)

### ROS Connection Issues

- Ensure `roscore` is running
- Check ROS environment variables:
  ```bash
  echo $ROS_MASTER_URI
  echo $ROS_HOSTNAME
  ```
- Verify robot is connected and `/cmd_vel` topic is available:
  ```bash
  rostopic list | grep cmd_vel
  ```

### Steps Not in English

If steps are still returned in Spanish:
- Check that `multi_step_parser.txt` has the English output requirement
- Verify `translate_to_english()` is detecting Spanish correctly
- Check API response parsing is working correctly

### Validation Errors

If you see `KeyError: '"valid"'`:
- Check that `validate_command()` prompt has escaped braces (`{{` and `}}`)
- Verify API response parsing is working

### Execution Stops After First Command

If only first command executes:
- Check ROS node initialization (should use `anonymous=True`)
- Verify error handling is catching exceptions
- Check for `rospy.is_shutdown()` calls
- Ensure 0.2 second pause between commands

## File Structure

```
03.voice_control/
├── voice_control_push_to_talk.py  # Main controller script
├── parser_llm.py                   # Multi-step command parser
├── requirements.txt                # Python dependencies (Python 3.6 compatible)
├── README.md                       # This file
└── prompts/
    ├── system.txt                  # GPT-5 system prompt for movement commands
    └── multi_step_parser.txt       # GPT-5 prompt for command splitting (forces English)
```

## Key Features & Improvements

### Robustness
- ✅ Graceful degradation if audio libraries unavailable (text input still works)
- ✅ Error handling prevents silent failures
- ✅ Automatic cleanup of temporary audio files
- ✅ ROS shutdown detection
- ✅ Safe printing for Unicode compatibility

### Language Support
- ✅ Accepts commands in English and Spanish
- ✅ **Always returns steps in English**
- ✅ **Always speaks in English** (automatic translation)
- ✅ Smart translation detection (avoids unnecessary API calls)

### Multi-step Execution
- ✅ Sequential command execution
- ✅ Safety pauses between commands
- ✅ Automatic "stop" command at end
- ✅ Error recovery (continues with next command on failure)

### TTS Integration
- ✅ Non-blocking TTS (runs in separate threads)
- ✅ Automatic English translation before speaking
- ✅ Command announcements before execution
- ✅ Status messages ("Recording", "Processing", etc.)

## Performance Considerations

- **Audio Recording**: Blocking recording with callback (more reliable than pure callback)
- **API Calls**: Translation only when Spanish detected (optimization)
- **TTS**: Non-blocking to avoid blocking robot control
- **ROS Publishing**: 10Hz rate for smooth control
- **Pause Between Commands**: 0.2 seconds for safety and stability

## Calibration Factors

The movement system uses calibration factors to account for robot acceleration/deceleration:
- **Linear movements**: 2.5x time multiplier
  - Formula: `duration = (distance / abs(linear.x)) * 2.5`
  - Without this, robot only achieves ~40% of target distance
- **Angular movements**: 2.0x time multiplier
  - Formula: `duration = (abs(angle_degrees) / (abs(angular.z) * 57.3)) * 2.0`

These factors are embedded in the `system.txt` prompt.

## Next Steps

For more advanced voice control options, see:
- **Script 04**: Voice Activity Detection (VAD) - automatic voice detection without push-to-talk
- **Script 05**: Realtime API - streaming voice recognition (requires Python 3.9+)

## Development Notes

### Testing Checklist
- [x] Text input works
- [x] Voice input works (push-to-talk)
- [x] Spanish commands are translated
- [x] Steps are returned in English
- [x] TTS speaks in English
- [x] Multi-step commands execute sequentially
- [x] Error handling prevents crashes
- [x] ROS integration works correctly
- [x] Python 3.6 compatibility verified

### Known Limitations
- Push-to-talk requires two ENTER presses (not ideal for hands-free operation)
- Audio recording is blocking (could be improved with async)
- TTS uses espeak (limited voice quality, but works offline)

### Future Improvements
- Add voice activity detection (see Script 04)
- Implement streaming STT (see Script 05)
- Add command history
- Improve error messages
- Add command confirmation mode
