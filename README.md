# Hiwonder JetAuto ROS1 Robot

Open-source repository for controlling and operating the **Hiwonder JetAuto 4WD robot** using **ROS1 Melodic** on **Jetson Orin Nano**.

This project includes complete system configuration, control scripts, SLAM, mapping, and natural language control using OpenAI.

## 🤖 Robot Overview

**Hardware:**
- **Robot:** Hiwonder JetAuto 4WD
- **SBC:** Jetson Orin Nano
- **OS:** Ubuntu 18.04 (JetPack)
- **ROS:** ROS1 Melodic

**Sensors:**
- RPLIDAR A1 (LiDAR)
- Astra Pro Plus RGB-D camera
- IMU
- Motor encoders

## 📁 Project Structure

```
hiwonder-jetauto-ros1-robot/
├── JETAUTO_GUIDE.md          # Complete technical guide
├── README.md                 # This file
├── CLAUDE.md                 # Documentation for AI assistants
├── .cursorrules              # Development rules for Cursor
└── scripts/
    └── text_control_multistep/
        ├── controller_llm.py  # Controller with OpenAI
        ├── parser_llm.py      # Multi-step command parser
        ├── requirements.txt   # Python dependencies
        ├── README.md          # Module documentation
        └── prompts/          # OpenAI prompts
```

## 🚀 Quick Start

### 1. ROS Environment Setup

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Load ROS
source /opt/ros/melodic/setup.bash
source $HOME/jetauto_ws/devel/setup.bash

# ROS Master configuration
export ROS_MASTER_URI="http://localhost:11311"
export ROS_HOSTNAME="localhost"
```

### 2. Start the Robot

```bash
roslaunch jetauto_bringup bringup.launch
```

### 3. Keyboard Control

```bash
rosrun teleop_twist_keyboard teleop_twist_keyboard.py
```

### 4. Text Control with Voice (OpenAI + TTS)

The robot can understand natural language commands in English and Spanish, and announces each action before executing it!

See complete documentation in [`scripts/text_control_multistep/README.md`](scripts/text_control_multistep/README.md)

```bash
# Install system dependencies for voice
sudo apt-get install espeak espeak-data libespeak-dev

# Install Python dependencies
cd scripts/text_control_multistep
pip install -r requirements.txt

# Create .env with OPENAI_API_KEY
echo "OPENAI_API_KEY=your_key_here" > .env

# Run controller
python controller_llm.py
```

**Example:**
```
Enter command: Avanza 2 metros, gira 180 grados, retrocede
```

The robot will:
1. 🔊 Say "Avanza 2 metros" → Move forward 2 meters
2. 🔊 Say "Gira 180 grados" → Rotate 180 degrees
3. 🔊 Say "Retrocede" → Move backward

## 📚 Documentation

- **[JETAUTO_GUIDE.md](JETAUTO_GUIDE.md)** - Complete technical guide:
  - System configuration
  - LiDAR configuration
  - SLAM and mapping
  - Troubleshooting
  - Battery status
  - Teleoperation

- **[scripts/text_control_multistep/README.md](scripts/text_control_multistep/README.md)** - Natural language control with voice:
  - Installation and configuration
  - Text-to-Speech (TTS) setup
  - Using OpenAI for intelligent command parsing
  - Precise distance and angle control
  - Examples in English and Spanish

## 🔧 Main Features

### Robust Control
- ⌨️ Keyboard teleoperation
- 📝 Predefined movement scripts
- 🗣️ Natural language control (English/Spanish)
- 🔊 Voice announcements (Text-to-Speech)

### SLAM and Navigation
- 🗺️ Mapping with gmapping
- 📍 Localization with AMCL
- 🎯 Autonomous navigation

### AI Integration
- 🤖 Intelligent command parsing using OpenAI GPT-4o-mini
- 📋 Multi-step command decomposition
- ⚡ Automatic conversion to ROS velocity commands
- 📏 Precise distance and angle control with metadata
- 🎤 Voice feedback for each action
- 🌐 Bilingual support (English/Spanish)

## 🛠️ Main ROS Packages

- `jetauto_bringup` - System initialization
- `jetauto_driver` - Hardware drivers
- `jetauto_slam` - SLAM and mapping
- `jetauto_navigation` - Autonomous navigation
- `rplidar_ros` - LiDAR driver
- `orbbec_camera` - Astra camera driver
- `robot_localization` - Sensor fusion

## 📋 Requirements

### System Requirements
- **ROS1 Melodic** installed and configured
- **Python 3.6+**
- **Jetson Orin Nano** with Ubuntu 18.04
- **ROS Workspace:** `~/jetauto_ws`

### For Natural Language Control (Optional)
- **OpenAI API Key** - Get at [platform.openai.com](https://platform.openai.com)
- **espeak** - Text-to-Speech engine (`sudo apt-get install espeak espeak-data libespeak-dev`)
- **pyttsx3** - Python TTS library (`pip install pyttsx3`)

## 🔍 Troubleshooting

### ROS Master not accessible
```bash
export ROS_MASTER_URI=http://localhost:11311
export ROS_HOSTNAME=localhost
```

### Blocked ROS processes
```bash
killall -9 roscore rosmaster roslaunch
```

### LiDAR with no data
- Check USB port (`/dev/ttyUSB1`)
- Check baudrate (115200)
- Check that no other process is using the port

For more details, see [JETAUTO_GUIDE.md](JETAUTO_GUIDE.md).

## 📝 Battery Status

Monitor battery:
```bash
rostopic echo /ros_robot_controller/battery
```

Voltage reference:
- **12.6 V** - Full
- **12.0 V** - ~70%
- **11.5 V** - ~50%
- **11.0 V** - Low (recharge soon)
- **<10.8 V** - Critical

## 🤝 Contributing

This is an open-source project. Contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

MIT License - see LICENSE file for details.

## 🔗 References

- [Hiwonder JetAuto Documentation](https://www.hiwonder.com/)
- [ROS Melodic Documentation](http://wiki.ros.org/melodic)
- [OpenAI API Documentation](https://platform.openai.com/docs)

## 📧 Contact

For questions or support, open an issue in the repository.

---

**Note:** This project is under active development. Documentation is updated regularly.

