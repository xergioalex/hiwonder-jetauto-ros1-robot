# Claude AI Assistant - Project Context

This document provides context about the Hiwonder JetAuto ROS1 Robot project for AI assistants working on this codebase.

## ⚠️ CRITICAL: Language Requirement

**ALL code, documentation, comments, variable names, function names, and any text in this project MUST be written in ENGLISH ONLY.**

- Code comments must be in English
- Documentation must be in English
- Variable and function names must be in English
- Error messages must be in English
- README files must be in English
- Code docstrings must be in English

**Exception:** User-facing prompts and system prompts that support multiple languages (English/Spanish) for robot commands are acceptable, but all code and documentation must remain in English.

## Project Overview

This is a ROS1 (Melodic) robotics project for controlling a **Hiwonder JetAuto 4WD robot** running on a **Jetson Orin Nano** with Ubuntu 18.04.

### Key Technologies
- **ROS1 Melodic** - Robot Operating System
- **Python 3.6+** - Primary scripting language
- **OpenAI API** - For natural language control (GPT-4o-mini)
- **pyttsx3 + espeak** - Text-to-Speech for voice announcements
- **Jetson Orin Nano** - NVIDIA embedded computing platform
- **Ubuntu 18.04** - Operating system

## Project Structure

```
hiwonder-jetauto-ros1-robot/
├── JETAUTO_GUIDE.md          # Complete technical guide
├── README.md                 # Main project README
├── CLAUDE.md                 # This file
├── .cursorrules              # Cursor IDE rules
├── .env                      # OpenAI API key (not in git, global for all scripts)
├── .env.example              # Example environment file
├── .gitignore                # Git ignore rules (includes .env)
└── scripts/
    ├── 01.text_control/                          # Basic text control (no voice)
    │   ├── controller_llm.py                     # Main controller using OpenAI
    │   ├── parser_llm.py                         # Multi-step command parser
    │   ├── requirements.txt                      # Python dependencies
    │   ├── README.md                             # Script documentation
    │   └── prompts/
    │       ├── system.txt                        # Twist conversion with metadata
    │       └── multi_step_parser.txt             # Command splitting prompt
    │
    └── 02.text_control_with_voice_notification/ # Text control with TTS
        ├── controller_llm.py                     # Controller with OpenAI + TTS
        ├── parser_llm.py                         # Multi-step command parser
        ├── requirements.txt                      # Dependencies (includes pyttsx3)
        ├── README.md                             # Script documentation
        └── prompts/
            ├── system.txt                        # Twist conversion with metadata
            └── multi_step_parser.txt             # Command splitting prompt
```

## Robot Hardware

### Physical Components
- **4WD Mecanum wheels** - Omnidirectional movement capability
- **RPLIDAR A1** - 360° LiDAR sensor (USB port: `/dev/ttyUSB1`, baudrate: 115200)
- **Astra Pro Plus** - RGB-D camera
- **IMU** - Inertial measurement unit
- **Motor encoders** - Wheel position feedback

### Movement Constraints
- **2D ground robot** - No vertical movement
- **Movement axes:**
  - `linear.x` - Forward/backward movement
  - `angular.z` - Left/right rotation
  - All other Twist fields should be 0

## ROS Architecture

### Workspace
- **Location:** `~/jetauto_ws`
- **Standard ROS workspace structure:** `src/`, `devel/`, `build/`

### Key ROS Packages
- `jetauto_bringup` - System initialization
- `jetauto_driver` - Hardware drivers
- `jetauto_slam` - SLAM and mapping
- `jetauto_navigation` - Autonomous navigation
- `rplidar_ros` - LiDAR driver
- `orbbec_camera` - Camera driver
- `robot_localization` - Sensor fusion

### Important ROS Topics
- `/cmd_vel` - Velocity commands (geometry_msgs/Twist)
- `/scan` - LiDAR data (sensor_msgs/LaserScan)
- `/ros_robot_controller/battery` - Battery status
- `/map` - Occupancy grid map
- `/odom` - Odometry data

### ROS Nodes
- `llm_multi_command_controller` - Main controller node from `controller_llm.py`

## Code Patterns

### OpenAI Integration
- Uses OpenAI API via `requests` library
- API key stored in `.env` file (not in git)
- Model used: `gpt-4o-mini` (can be changed to `gpt-4o`, `gpt-3.5-turbo`, etc.)
- Environment variables loaded using `python-dotenv`
- Returns JSON with velocities + metadata (distance, angle, duration)

### Text-to-Speech Integration
- Uses `pyttsx3` library with `espeak` backend
- Thread-safe implementation with `threading.Lock`
- Non-blocking speech (runs in separate thread)
- Graceful degradation: continues without TTS if unavailable
- Configurable rate (150 words/min) and volume (0.9)

### File Path Handling
- Always use `os.path.dirname(__file__)` for relative paths
- Prompts stored in `prompts/` subdirectory within each script folder
- **`.env` file is GLOBAL** - stored in repository root, not in script directories
- Scripts calculate repo root: `repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))`
- Load .env from root: `load_dotenv(os.path.join(repo_root, '.env'))`

### Error Handling
- JSON parsing errors return zero-velocity Twist with default metadata
- Graceful degradation on API failures
- TTS errors are logged but don't stop execution

## Language Support

The system supports **both English and Spanish** for:
- Natural language commands
- Multi-step command parsing
- Movement instructions
- Voice announcements (TTS synthesizes both languages)

## Development Guidelines

### When Adding Features
1. Follow ROS1 conventions (Melodic)
2. Use relative paths with `os.path.dirname(__file__)`
3. Store API keys in `.env` files (never commit)
4. Add dependencies to `requirements.txt`
5. Update relevant README files

### When Modifying OpenAI Integration
- Check both `controller_llm.py` and `parser_llm.py`
- Update model names if changing OpenAI models
- Ensure prompts in `prompts/` directory are compatible
- Test with both English and Spanish commands

### When Working with ROS
- Always check ROS master is running (`roscore`)
- Verify topic names match robot configuration
- Use `geometry_msgs/Twist` for velocity commands
- Follow ROS node naming conventions

## Common Tasks

### Adding a New Script
1. Create in appropriate `scripts/` subdirectory
2. Use `rospy` for ROS integration
3. Publish to `/cmd_vel` for movement
4. Add to documentation if user-facing

### Modifying Movement Logic
- Remember: only `linear.x` and `angular.z` are used
- All other Twist fields must be 0
- Commands execute for duration specified in metadata (calculated from distance/angle)
- Robot stops briefly between multi-step commands
- Voice announcements happen before each command execution

### Debugging
- Check ROS topics: `rostopic list`, `rostopic echo /cmd_vel`
- Verify LiDAR: `rostopic echo /scan`
- Check battery: `rostopic echo /ros_robot_controller/battery`
- Kill stuck processes: `killall -9 roscore rosmaster roslaunch`

## Environment Variables

### Required
- `OPENAI_API_KEY` - Stored in **repository root** `.env` file (shared by all scripts)
- Location: `/path/to/hiwonder-jetauto-ros1-robot/.env`
- Example file provided: `.env.example`

### ROS Environment (set in shell)
- `ROS_MASTER_URI` - Default: `http://localhost:11311`
- `ROS_HOSTNAME` - Default: `localhost`

## Testing Considerations

- Test with ROS master running
- Verify `/cmd_vel` topic is being subscribed
- Test both English and Spanish commands
- Check OpenAI API responses are valid JSON with metadata field
- Verify robot stops between commands
- Test TTS functionality with both languages
- Verify precise angle/distance execution (e.g., 180° rotation completes fully)

## Known Issues & Solutions

### LiDAR Issues
- Port: Use `/dev/ttyUSB1` (not `/dev/ttyUSB0`)
- Baudrate: Must be 115200
- Locked port: Check with `sudo lsof /dev/ttyUSB1` and kill process

### ROS Master Issues
- Always set `ROS_MASTER_URI` and `ROS_HOSTNAME`
- Kill stuck processes before restarting

### OpenAI API Issues
- Verify `.env` file exists and has correct key
- Check API key is valid and has credits
- Model availability may vary by region

### TTS Issues
- Install espeak: `sudo apt-get install espeak espeak-data libespeak-dev`
- Install pyttsx3: `pip install pyttsx3`
- Test espeak: `espeak "test message"`
- Check for audio output device availability
- TTS will gracefully fail and continue without voice if unavailable

## File-Specific Notes

### `controller_llm.py`
- Main entry point for text control
- Initializes ROS node and TTS engine
- Announces each command via speech before execution
- Extracts metadata (distance, angle, duration) from LLM response
- Publishes velocity commands at 10Hz for smooth control

### `parser_llm.py`
- Splits multi-step commands into individual steps
- Uses numbered list parsing
- Returns list of command strings

### `prompts/system.txt`
- Converts natural language to Twist JSON with metadata
- Enforces strict JSON format with velocities + metadata fields
- Handles both English and Spanish
- Includes velocity scaling guidelines (slow/normal/fast)
- Provides duration calculation formulas
- Contains 30+ examples for various command types
- Supports distance specifications (meters, centimeters)
- Supports angle specifications (degrees, quarter turns, etc.)

### `prompts/multi_step_parser.txt`
- Splits complex commands into atomic steps
- Advanced parsing strategies for temporal connectors and conjunctions
- Handles pattern-based commands (repeat, loops)
- Returns numbered list format
- 15+ example categories
- No explanations, just steps

## Future Enhancements

Potential areas for expansion:
- Autonomous navigation integration
- Object detection with camera
- Web UI using rosbridge_suite
- Multi-robot communication
- Advanced SLAM features
- Voice command integration

---

**Last Updated:** Based on current codebase state (2025)
**Maintainer Context:** This is an open-source project for the Hiwonder JetAuto robot community.

