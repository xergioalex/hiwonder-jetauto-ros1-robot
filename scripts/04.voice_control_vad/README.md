# Voice Control - Voice Activity Detection (VAD) Mode

This script provides hands-free voice control for the JetAuto robot using WebRTC Voice Activity Detection (VAD). The robot continuously listens for voice commands and automatically detects when you start and stop speaking.

## Features

- **Automatic Voice Detection**: 
  - Continuously listens for voice activity
  - Automatically starts recording when speech is detected
  - Automatically stops recording when silence is detected (500ms threshold)
  
- **WebRTC VAD Integration**:
  - Local voice activity detection (no cloud processing for detection)
  - Efficient 20ms frame processing
  - Configurable aggressiveness level
  - Maximum duration safety limit (10 seconds)
  
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
- `webrtcvad-wheels>=2.0.10` - WebRTC Voice Activity Detection

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

# Run the VAD voice controller
cd scripts/04.voice_control_vad
python voice_control_vad.py
```

### How It Works

1. **Continuous Listening**: The script starts listening immediately and waits for voice activity.

2. **Voice Detection**: When you start speaking, WebRTC VAD detects speech and begins recording automatically.

3. **Silence Detection**: When you stop speaking, the script waits for 500ms of silence, then stops recording.

4. **Transcription**: The captured audio is sent to OpenAI's Speech-to-Text API for transcription.

5. **Command Processing**: The transcribed text is:
   - Announced via TTS ("I heard: [transcription]")
   - Passed to `split_into_steps()` for multi-step parsing
   - Each step is validated and converted to ROS Twist commands via GPT-5

6. **Execution**: Commands are executed sequentially with TTS announcements before each action.

7. **Loop**: The script returns to listening mode and waits for the next command.

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

Press Ctrl+C to stop the controller.

## VAD Configuration

The script uses the following VAD settings (configurable in code):

- **Sample Rate**: 16,000 Hz (required by WebRTC VAD)
- **Frame Size**: 20ms (320 samples)
- **Aggressiveness**: 2 (balanced - 0=least, 3=most aggressive)
- **Silence Threshold**: 500ms (stops after 500ms of silence)
- **Max Duration**: 10 seconds (safety limit)

### Adjusting VAD Sensitivity

You can modify the aggressiveness level in `voice_control_vad.py`:

```python
VAD_AGGRESSIVENESS = 2  # Change to 0-3
```

- **0**: Least aggressive (only very clear speech)
- **1**: Less aggressive (good for quiet environments)
- **2**: Balanced (default, good for most environments)
- **3**: Most aggressive (catches more speech, may include noise)

### Adjusting Silence Threshold

Modify the silence detection time:

```python
VAD_SILENCE_THRESHOLD_MS = 500  # Change to desired milliseconds
```

- Lower values (300-400ms): Stops recording faster after you finish speaking
- Higher values (600-800ms): Waits longer before stopping (good for slow speakers)

## Troubleshooting

### VAD Not Detecting Speech

1. **Check microphone**: Ensure microphone is working and not muted
2. **Increase aggressiveness**: Try setting `VAD_AGGRESSIVENESS = 3`
3. **Check environment noise**: VAD may struggle in very noisy environments
4. **Speak clearly**: Try speaking louder and more clearly
5. **Check audio device**: Verify correct input device is selected

### Too Many False Positives

1. **Decrease aggressiveness**: Try setting `VAD_AGGRESSIVENESS = 1` or `0`
2. **Reduce background noise**: Move to quieter environment
3. **Adjust microphone sensitivity**: Lower microphone gain in system settings

### Audio Not Working

If you see "Audio libraries not available":
```bash
# Install system dependencies
sudo apt-get install portaudio19-dev libsndfile1

# Reinstall Python packages
pip install --upgrade sounddevice soundfile
```

### VAD Library Issues

If you see "WebRTC VAD not available":
```bash
# Install WebRTC VAD
pip install webrtcvad-wheels

# For Python 3.6 (JetAuto), you may need to use a specific version
pip install webrtcvad-wheels==2.0.10
```

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

### High CPU Usage

The VAD processing is efficient, but if you experience high CPU:
- Ensure you're using the latest versions of `sounddevice` and `webrtcvad-wheels`
- Check that audio device is properly configured
- Consider increasing `VAD_FRAME_SIZE_MS` (though 20ms is optimal)

## File Structure

```
04.voice_control_vad/
├── voice_control_vad.py      # Main controller script with VAD
├── parser_llm.py             # Multi-step command parser
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── prompts/
    ├── system.txt             # GPT-5 system prompt for movement commands
    └── multi_step_parser.txt  # GPT-5 prompt for command splitting
```

## Technical Details

### State Machine

The VAD implementation uses a simple state machine:

1. **IDLE**: Waiting for speech to begin
2. **RECORDING**: Actively recording speech frames
3. **ENDING**: Silence detected, finishing recording

### Audio Processing

- Frames are processed in 20ms chunks (320 samples at 16kHz)
- Each frame is analyzed by VAD to detect speech
- Speech frames are accumulated until silence threshold is reached
- Audio is saved as 16-bit PCM WAV file for transcription

### Performance Considerations

- VAD processing is very lightweight (minimal CPU usage)
- Audio recording uses efficient callback-based streaming
- Temporary WAV files are automatically cleaned up after transcription
- The script handles sensor noise gracefully through VAD filtering

## Comparison with Other Scripts

- **Script 03 (Push-to-Talk)**: Requires manual button presses (ENTER key)
- **Script 04 (VAD)**: Fully hands-free, automatic detection
- **Script 05 (Realtime API)**: Streaming recognition with lower latency

## Notes

- The script continuously listens - no need to press any buttons
- Speak naturally - the robot will detect when you start and stop
- Maximum recording duration is 10 seconds (safety limit)
- All commands support both English and Spanish
- The robot automatically adds a "stop" command at the end of multi-step sequences for safety
- TTS announcements are non-blocking and run in separate threads

## Next Steps

For even more advanced voice control:
- Script 05: Realtime API - streaming voice recognition with lower latency

