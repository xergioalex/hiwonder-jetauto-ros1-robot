# Text Control Multi-Step

Robot control system using natural language text commands with OpenAI. The system allows executing complex multi-step commands that are automatically broken down and converted into ROS movement commands.

## Description

This script uses OpenAI GPT to:
1. **Parse complex commands**: Splits multi-step commands into individual instructions
2. **Convert to ROS commands**: Transforms each instruction into velocity commands (`geometry_msgs/Twist`) that are published to the `/cmd_vel` topic

The system supports commands in **English and Spanish**, and is designed for robots with mecanum wheels that move in 2D.

## Requirements

- **ROS 1** (Noetic or Melodic recommended)
- **Python 3.6+**
- **OpenAI API Key** (you can get it at [platform.openai.com](https://platform.openai.com))

## Installation

### 1. Install System Dependencies (for TTS)

On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install espeak espeak-data libespeak-dev
```

### 2. Install Python Dependencies

```bash
cd scripts/02.text_control_with_voice_notification
pip install -r requirements.txt
```

Or install manually:

```bash
pip install requests python-dotenv pyttsx3
```

### 3. Configure OpenAI API Key

Create a `.env` file in the **repository root** (not in this script directory) with your API key:

```bash
# From the repository root
cp .env.example .env
# Edit .env and add your key
echo "OPENAI_API_KEY=your_api_key_here" > .env
```

**Important**: The `.env` file is global for all scripts and is located at the repository root. It's in `.gitignore` and will not be uploaded to the repository.

### 4. Verify ROS is Configured

Make sure you have ROS configured in your environment:

```bash
source /opt/ros/noetic/setup.bash  # Adjust according to your ROS version
```

## Usage

### Running the Script

1. Make sure ROS is running (roscore):

```bash
roscore
```

2. In another terminal, run the script:

```bash
cd scripts/02.text_control_with_voice_notification
python controller_llm.py
```

3. The script will run in **continuous mode** - you can enter multiple commands:

```
======================================================================
🤖 Robot Text Controller with Voice Notifications - Continuous Mode
======================================================================
Enter commands in English or Spanish
The robot will announce each action before executing

Type 'exit', 'quit', or 'salir' to stop
Press Ctrl+C to force exit
======================================================================

🎤 Enter command: Avanza un metro, luego gira a la derecha

📝 Processing: Avanza un metro, luego gira a la derecha
📋 Steps: ['Avanza un metro', 'Gira a la derecha', 'stop']
Executing: Avanza un metro
[Robot speaks: "Avanza un metro"]
...
✅ Sequence completed!
----------------------------------------------------------------------

🎤 Enter command: Gira 180 grados

📝 Processing: Gira 180 grados
[Robot speaks: "Gira 180 grados"]
...
✅ Sequence completed!
----------------------------------------------------------------------

🎤 Enter command: exit
👋 Exiting robot controller...
[Robot speaks: "Adiós"]
```

**To exit:**
- Type: `exit`, `quit`, `salir`, `terminar`, or `cerrar`
- Press: `Ctrl+C`

### Command Examples

**In Spanish:**
- "Avanza un metro, luego gira a la derecha y después avanza otro medio metro"
- "Gira a la izquierda lentamente y luego da una vuelta completa"
- "Retrocede rápido, gira 90 grados y avanza"

**In English:**
- "Turn left, move forward 2 meters and then stop"
- "Go forward slowly, then turn right and go back"
- "Rotate 180 degrees, then move forward 1 meter"

## Features

- ✅ **Multi-step command parsing**: Automatically breaks down complex instructions
- ✅ **Bilingual support**: Works with English and Spanish commands
- ✅ **Voice announcements**: Robot announces each command before executing (TTS)
- ✅ **Precise timing**: Calculates execution time based on distances and angles
- ✅ **Smart velocity scaling**: Adjusts speed based on command modifiers (slow/fast)

## How It Works

1. **Parser (`parser_llm.py`)**:
   - Receives the complete command from the user
   - Uses OpenAI to split it into individual steps
   - Returns a list of simple commands

2. **Controller (`controller_llm.py`)**:
   - Takes each step from the list
   - **Announces the command via TTS** (Text-to-Speech)
   - Uses OpenAI to convert each command into a ROS `Twist` message with metadata
   - Publishes the command to `/cmd_vel`
   - Executes for the calculated duration based on distance/angle
   - Stops the robot before the next step

## File Structure

```
02.text_control_with_voice_notification/
├── controller_llm.py          # Main controller
├── parser_llm.py              # Multi-step command parser
├── requirements.txt           # Python dependencies
├── .env                       # API key (not included in git)
├── .gitignore                # Ignores .env
├── README.md                  # This file
└── prompts/
    ├── system.txt             # System prompt for Twist conversion
    └── multi_step_parser.txt  # Prompt for splitting commands
```

## Customization

### Changing the OpenAI Model

By default, `gpt-4o-mini` is used. To change the model, edit:

- `controller_llm.py` line 20: `model='gpt-4o-mini'`
- `parser_llm.py` line 16: `model="gpt-4o-mini"`

Available models: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`, etc.

### Adjusting Speed and Timing

In `controller_llm.py`:
- Line 48: `time.sleep(2)` - Execution time for each command
- Line 34: `rospy.Rate(1)` - Publication frequency

## Troubleshooting

### Error: "OPENAI_API_KEY not found"
- Verify that the `.env` file exists in the `02.text_control_with_voice_notification/` directory
- Verify that the variable is named exactly `OPENAI_API_KEY`

### Error: "No module named 'rospy'"
- Make sure you have ROS installed and configured
- Run `source /opt/ros/[version]/setup.bash` before running the script

### TTS not working (no voice)
- Install espeak: `sudo apt-get install espeak espeak-data libespeak-dev`
- Check if espeak works: `espeak "test"`
- Install pyttsx3: `pip install pyttsx3`
- If errors persist, the script will continue without TTS (commands will only be printed)

### Robot doesn't move
- Verify that the `/cmd_vel` topic is being listened to by the robot
- Verify that ROS is running (`roscore`)
- Check error messages in the console

## Notes

- The script runs in **continuous mode** - you can enter multiple commands without restarting
- The script publishes velocity commands with calculated durations based on distance/angle
- Each command executes for the calculated duration, then the robot stops before the next step
- The system is designed for robots with mecanum wheels in 2D (only uses `linear.x` and `angular.z`)
- **Voice announcements**: The robot speaks each command before executing it
