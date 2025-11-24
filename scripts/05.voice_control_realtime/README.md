# Voice Control - Realtime API Mode

This script provides real-time streaming voice control for the JetAuto robot using OpenAI's Realtime API. It offers the lowest latency voice recognition by processing audio streams in real-time via WebSocket.

## Features

- **Streaming Recognition**: 
  - Real-time audio streaming to OpenAI Realtime API
  - Low-latency transcription (no need to wait for speech to end)
  - Automatic speech start/stop detection
  
- **WebSocket Architecture**:
  - Persistent WebSocket connection to OpenAI
  - Async/await architecture for efficient I/O
  - Auto-reconnection on connection loss
  - Two concurrent tasks: audio sending and event receiving
  
- **Full Integration**:
  - Uses GPT-5 Responses API for command interpretation
  - Multi-step command parsing
  - TTS voice announcements
  - Complete ROS integration

## Requirements

### Python Version

⚠️ **IMPORTANT**: This script requires **Python 3.9 or higher**.

- JetAuto runs Python 3.6, so this script may not work directly on the robot
- **Solution**: Run this script on a laptop/computer with Python 3.9+ and send commands to the robot via ROS topics or HTTP

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
- `numpy>=1.19.0` - Numerical operations
- `websockets>=10.0` - WebSocket client for Realtime API

### Environment Variables

Create a `.env` file in the repository root (not in this script directory) with:

```
OPENAI_API_KEY=your_openai_api_key_here
```

## Usage

### Basic Usage (On Laptop/Computer with Python 3.9+)

```bash
# Make sure ROS master is running (can be on robot or laptop)
export ROS_MASTER_URI=http://robot_ip:11311  # If robot is remote

# Run the Realtime API voice controller
cd scripts/05.voice_control_realtime
python voice_control_realtime.py
```

### Running on Robot (Python 3.6)

If you need to run on the robot directly, you have two options:

1. **Upgrade Python** (if possible):
   ```bash
   # Install Python 3.9+ on JetAuto
   sudo apt-get install python3.9 python3.9-venv
   python3.9 voice_control_realtime.py
   ```

2. **Use Alternative Scripts**:
   - Script 03 (Push-to-Talk) - Works with Python 3.6
   - Script 04 (VAD) - Works with Python 3.6

### How It Works

1. **WebSocket Connection**: Script connects to OpenAI Realtime API via WebSocket.

2. **Session Configuration**: Configures the session for audio transcription using `gpt-4o-mini-transcribe`.

3. **Audio Streaming**: 
   - Opens audio input stream at 24kHz
   - Sends audio chunks (20ms frames) continuously to WebSocket
   - Audio is base64-encoded before sending

4. **Event Processing**:
   - Receives events from WebSocket in real-time
   - Handles `speech_started`, `speech_stopped` events
   - Processes partial transcripts as they arrive
   - Processes final transcripts when speech completes

5. **Command Execution**:
   - Final transcripts are queued for processing
   - Commands are parsed and executed via ROS
   - TTS announcements before each action

6. **Auto-Reconnection**: If connection is lost, automatically reconnects with exponential backoff.

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

## Architecture

### Async Tasks

The script runs three concurrent async tasks:

1. **`send_audio_loop()`**: 
   - Reads audio from microphone
   - Encodes to base64
   - Sends to WebSocket continuously

2. **`receive_events_loop()`**:
   - Receives events from WebSocket
   - Processes transcription events
   - Queues final transcripts

3. **`process_transcripts_loop()`**:
   - Processes transcripts from queue
   - Executes commands via ROS
   - Handles command parsing and execution

### Audio Configuration

- **Sample Rate**: 24,000 Hz (required by Realtime API)
- **Channels**: Mono (1 channel)
- **Format**: 16-bit PCM (int16)
- **Frame Size**: 480 samples (20ms at 24kHz)

## Troubleshooting

### Python Version Error

If you see "Python 3.9+ required":
- Upgrade Python to 3.9+ on your system
- Or use Script 03 or 04 which work with Python 3.6
- Or run on a different machine and connect to robot via ROS

### WebSocket Connection Errors

**401 Unauthorized**:
- Check your OpenAI API key is correct
- Verify API key has access to Realtime API (may require beta access)

**403 Forbidden**:
- Your API key may not have permission for Realtime API
- Check OpenAI account for beta access status

**Connection Closed**:
- Script will automatically reconnect
- Check internet connection
- Verify OpenAI API is accessible

### Audio Issues

**No audio detected**:
```bash
# Check audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Set default input device in system settings
```

**Audio buffer overflow**:
- Reduce system load
- Close other audio applications
- Check microphone is working properly

### ROS Connection Issues

**If running on laptop, connecting to remote robot**:
```bash
# Set ROS master URI
export ROS_MASTER_URI=http://robot_ip:11311
export ROS_HOSTNAME=your_laptop_ip

# Verify connection
rostopic list
```

**If robot is local**:
```bash
# Ensure roscore is running
roscore

# Verify /cmd_vel topic exists
rostopic list | grep cmd_vel
```

### High Latency

Realtime API should have low latency, but if you experience delays:
- Check internet connection speed
- Verify WebSocket connection is stable
- Check for network firewall blocking WebSocket connections
- Ensure audio stream is running smoothly

## Comparison with Other Scripts

| Feature | Script 03 (Push-to-Talk) | Script 04 (VAD) | Script 05 (Realtime) |
|---------|-------------------------|-----------------|---------------------|
| **Latency** | Medium | Medium | **Lowest** |
| **Hands-free** | No (requires ENTER) | Yes | Yes |
| **Python Version** | 3.6+ | 3.6+ | **3.9+** |
| **Internet Required** | Yes (for STT) | Yes (for STT) | Yes (always) |
| **Complexity** | Low | Medium | **High** |
| **Best For** | Manual control | Automatic detection | Real-time streaming |

## File Structure

```
05.voice_control_realtime/
├── voice_control_realtime.py  # Main controller script with Realtime API
├── parser_llm.py              # Multi-step command parser
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── prompts/
    ├── system.txt              # GPT-5 system prompt for movement commands
    └── multi_step_parser.txt   # GPT-5 prompt for command splitting
```

## Technical Details

### WebSocket Protocol

The script uses OpenAI's Realtime API WebSocket protocol:

- **Connection**: `wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview-2024-12-17`
- **Headers**: Authorization and OpenAI-Beta headers required
- **Session Config**: Sent immediately after connection
- **Audio Format**: Base64-encoded PCM audio chunks
- **Events**: JSON messages for transcription and status

### Event Types Handled

- `session.updated` - Session configuration confirmed
- `input_audio_buffer.speech_started` - Speech detected
- `input_audio_buffer.speech_stopped` - Speech ended
- `input_audio_buffer.committed` - Partial transcript
- `conversation.item.input_audio_transcription.completed` - Final transcript
- `error` - Error events

### Reconnection Logic

- Automatic reconnection on connection loss
- Exponential backoff (2s, 4s, 8s, up to 30s)
- Maximum 5 retry attempts
- Graceful handling of authentication errors

## Notes

- ⚠️ **Requires Python 3.9+** - May not work on JetAuto (Python 3.6)
- Streaming recognition provides lowest latency
- Requires stable internet connection
- WebSocket connection must remain open
- All commands support both English and Spanish
- The robot automatically adds a "stop" command at the end of multi-step sequences for safety
- TTS announcements are non-blocking and run in separate threads

## Alternative: Running on Laptop, Controlling Robot Remotely

If you want to run this script on a laptop and control the robot remotely:

1. **On Robot**: Ensure ROS master is running and accessible
2. **On Laptop**: 
   ```bash
   export ROS_MASTER_URI=http://robot_ip:11311
   export ROS_HOSTNAME=your_laptop_ip
   python voice_control_realtime.py
   ```
3. Commands will be sent to robot via ROS topics

## Future Enhancements

Potential improvements:
- Support for bidirectional audio (robot speaking back)
- Integration with robot's camera for visual context
- Multi-language support with automatic language detection
- Custom wake word detection
- Voice command history and learning

