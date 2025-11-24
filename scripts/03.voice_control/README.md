# Voice Control - Push-to-Talk Mode

This script provides voice control for the JetAuto robot using a push-to-talk interface. Users can control the robot by either typing commands or using voice input with a simple push-to-talk mechanism.

## Features

- **Dual Input Modes**: 
  - Text input (type commands and press ENTER)
  - Voice input (press ENTER twice for push-to-talk recording)
  
- **Push-to-Talk Voice Recording**:
  - First ENTER press: Start recording
  - Second ENTER press: Stop recording
  - Automatic transcription using OpenAI Speech-to-Text API
  
- **Full Integration**:
  - Uses GPT-5 Responses API for command interpretation
  - Multi-step command parsing
  - TTS voice announcements
  - Complete ROS integration

## Requirements

### System Dependencies

```bash
# Install audio system libraries (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y portaudio19-dev libsndfile1 espeak espeak-data libespeak-dev

# Install Python dependencies
pip install -r requirements.txt
```

### Python Dependencies

See `requirements.txt` for full list:
- `requests>=2.20.0` - HTTP requests for OpenAI API
- `python-dotenv>=0.19.0` - Environment variable management
- `pyttsx3==2.7` - Text-to-speech
- `sounddevice>=0.4.6` - Audio recording
- `soundfile>=0.12.1` - Audio file I/O
- `numpy>=1.19.0` - Numerical operations

### Environment Variables

Create a `.env` file in the repository root (not in this script directory) with:

```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Basic Usage

```bash
# Make sure ROS master is running
roscore

# Run the voice controller
cd scripts/03.voice_control
python voice_control_push_to_talk.py
```

### Input Methods

#### Text Input
1. Type your command (e.g., "move forward 1 meter")
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

**Spanish:**
- "avanza un metro"
- "gira 90 grados a la izquierda"
- "retrocede medio metro y luego gira a la derecha"

### Exit

Type `exit`, `quit`, or `salir` to stop the controller, or press Ctrl+C.

## How It Works

1. **Recording**: When user presses ENTER (first time), the script starts recording audio from the microphone at 16kHz mono.

2. **Transcription**: When user presses ENTER (second time), recording stops and the audio is sent to OpenAI's Speech-to-Text API (`gpt-4o-mini-transcribe`) for transcription.

3. **Command Processing**: The transcribed text is:
   - Announced via TTS ("I heard: [transcription]")
   - Passed to `split_into_steps()` for multi-step parsing
   - Each step is validated and converted to ROS Twist commands via GPT-5

4. **Execution**: Commands are executed sequentially with TTS announcements before each action.

## Audio Configuration

The script uses the following audio settings:
- **Sample Rate**: 16,000 Hz (required by OpenAI STT)
- **Channels**: Mono (1 channel)
- **Format**: 16-bit PCM (int16)
- **File Format**: WAV

## Troubleshooting

### Audio Not Working

If you see "Audio libraries not available":
```bash
# Install system dependencies
sudo apt-get install portaudio19-dev libsndfile1

# Reinstall Python packages
pip install --upgrade sounddevice soundfile
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

## File Structure

```
03.voice_control/
├── voice_control_push_to_talk.py  # Main controller script
├── parser_llm.py                   # Multi-step command parser
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── prompts/
    ├── system.txt                  # GPT-5 system prompt for movement commands
    └── multi_step_parser.txt       # GPT-5 prompt for command splitting
```

## Notes

- Audio files are temporarily saved during transcription and automatically cleaned up
- The script gracefully degrades if audio libraries are not available (text input still works)
- TTS announcements are non-blocking and run in separate threads
- All commands support both English and Spanish
- The robot automatically adds a "stop" command at the end of multi-step sequences for safety

## Next Steps

For more advanced voice control options, see:
- Script 04: Voice Activity Detection (VAD) - automatic voice detection
- Script 05: Realtime API - streaming voice recognition

