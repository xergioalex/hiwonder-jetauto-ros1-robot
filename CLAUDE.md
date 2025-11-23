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
- **OpenAI API** - For natural language control
- **Jetson Orin Nano** - NVIDIA embedded computing platform
- **Ubuntu 18.04** - Operating system

## Project Structure

```
hiwonder-jetauto-ros1-robot/
├── JETAUTO_GUIDE.md          # Complete technical guide (316 lines)
├── README.md                 # Main project README
├── CLAUDE.md                 # This file
├── .cursorrules              # Cursor IDE rules
└── scripts/
    └── text_control_multistep/
        ├── controller_llm.py  # Main controller using OpenAI
        ├── parser_llm.py      # Multi-step command parser
        ├── requirements.txt   # Python dependencies (openai, python-dotenv)
        ├── README.md          # Module-specific documentation
        ├── .gitignore         # Ignores .env file
        └── prompts/
            ├── system.txt     # System prompt for Twist conversion
            └── multi_step_parser.txt  # Prompt for command splitting
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
- Uses `openai` Python library (v1.0.0+)
- API key stored in `.env` file (not in git)
- Model used: `gpt-4o-mini` (can be changed to `gpt-4o`, `gpt-3.5-turbo`, etc.)
- Environment variables loaded using `python-dotenv`

### File Path Handling
- Always use `os.path.dirname(__file__)` for relative paths
- Prompts stored in `prompts/` subdirectory
- `.env` file in same directory as scripts

### Error Handling
- JSON parsing errors return zero-velocity Twist
- Graceful degradation on API failures

## Language Support

The system supports **both English and Spanish** for:
- Natural language commands
- Multi-step command parsing
- Movement instructions

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
- Commands execute for 2 seconds then stop
- Robot stops between multi-step commands

### Debugging
- Check ROS topics: `rostopic list`, `rostopic echo /cmd_vel`
- Verify LiDAR: `rostopic echo /scan`
- Check battery: `rostopic echo /ros_robot_controller/battery`
- Kill stuck processes: `killall -9 roscore rosmaster roslaunch`

## Environment Variables

### Required
- `OPENAI_API_KEY` - Stored in `scripts/text_control_multistep/.env`

### ROS Environment (set in shell)
- `ROS_MASTER_URI` - Default: `http://localhost:11311`
- `ROS_HOSTNAME` - Default: `localhost`

## Testing Considerations

- Test with ROS master running
- Verify `/cmd_vel` topic is being subscribed
- Test both English and Spanish commands
- Check OpenAI API responses are valid JSON
- Verify robot stops between commands

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

## File-Specific Notes

### `controller_llm.py`
- Main entry point for text control
- Initializes ROS node
- Publishes Twist messages
- Executes commands sequentially with 2-second delays

### `parser_llm.py`
- Splits multi-step commands into individual steps
- Uses numbered list parsing
- Returns list of command strings

### `prompts/system.txt`
- Converts natural language to Twist JSON
- Enforces JSON-only output
- Handles both English and Spanish

### `prompts/multi_step_parser.txt`
- Splits complex commands into steps
- Returns numbered list format
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

