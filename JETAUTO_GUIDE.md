# JetAuto ROS1 Robot (Hiwonder) – Full Technical Guide (2025)

This repository documents the full setup, environment configuration, and validated workflow to operate the **Hiwonder JetAuto** robot running **ROS1 Melodic** on **Jetson Orin Nano**.

It includes all fixes required for stable robot control, LiDAR configuration, SLAM, mapping, and debugging.

---

## 1. System Overview

**Robot:** Hiwonder JetAuto 4WD  
**OS:** Ubuntu 18.04 (JetPack)  
**ROS:** ROS1 Melodic  
**Workspace:** `~/jetauto_ws`

**Sensors:**
- RPLIDAR A1 (LiDAR)
- Astra Pro Plus RGB-D camera
- IMU
- Motor encoders

**Key ROS Packages:**
- `jetauto_bringup`
- `jetauto_driver`
- `jetauto_slam`
- `jetauto_navigation`
- `rplidar_ros`
- `orbbec_camera`
- `robot_localization`

---

## 2. System Architecture: Host OS vs Docker UI

⚠️ **CRITICAL**: The JetAuto robot runs **two different Linux environments**. Understanding this distinction is essential to avoid confusion.

### 2.1. SSH Terminal → Real Host OS

When you connect via SSH:

```bash
ssh jetauto@jetauto.local
```

You enter the **real Jetson host operating system** at `/home/jetauto`.

**Characteristics of the Host OS:**
- **User**: `jetauto`
- **Full hardware access**: `/dev/*` devices (LiDAR, ttyUSB1, camera, motors)
- **Real ROS workspace**: `~/jetauto_ws` (actual filesystem)
- **Docker engine**: Available here (`docker` command works)
- **ROS runs here**: All ROS nodes execute on the host, not in containers
- **System services**: `systemctl` commands work here
- **Network configuration**: WiFi, network settings live here
- **Hardware drivers**: LiDAR, camera, IMU, motor controllers accessible

**✅ This is the environment where all ROS development must happen.**

### 2.2. Graphical UI Terminal → Docker Container

When you open the JetAuto UI on the built-in screen and start a terminal, you are **NOT** in the host OS.

You are inside a **Docker container**:

- **User**: `ubuntu`
- **Isolated filesystem**: Only `/home/ubuntu` (separate from host)
- **Not the real workspace**: The JetAuto workspace you see here is **not** the host workspace
- **No Docker**: Docker is not available inside the container
- **No hardware access**: Devices (ttyUSB, LiDAR, camera) are **not** accessible
- **Network isolation**: NetworkManager configuration not shared with host
- **Missing tools**: Some commands/tools may appear missing

**❌ This container is meant only for the JetAuto UI apps — NOT for ROS development.**

### 2.3. Why This Matters

Because of the dual-environment setup:

| Issue | Host OS (SSH) | Docker UI |
|-------|----------------|-----------|
| **Files created** | Visible in `/home/jetauto` | Only in `/home/ubuntu` (isolated) |
| **Docker commands** | ✅ Available | ❌ Not available |
| **Hardware access** | ✅ Full access | ❌ No access |
| **ROS launch files** | ✅ Must run here | ❌ Will not work |
| **LiDAR/Camera** | ✅ Accessible | ❌ Not accessible |
| **System config** | ✅ Real configuration | ❌ Isolated environment |

**Key Rules:**
- ❌ Files created in UI terminal do **not** appear in SSH
- ❌ Docker cannot be used inside the UI terminal
- ❌ LiDAR, camera, and servo drivers do **not** work inside Docker
- ✅ ROS launch files must **always** be run from SSH
- ✅ Real system configuration is only visible via SSH

### 2.4. Best Practices

**Always use SSH for:**
- ROS development and debugging
- Running `roslaunch` commands
- Accessing hardware (LiDAR, camera, motors)
- Building ROS packages
- System configuration
- SLAM and navigation

**UI Terminal is only for:**
- Touchscreen interface apps
- Visual feedback (if needed)
- **NOT for ROS development**

> **⚠️ IMPORTANT**: Always use SSH when building, running, or debugging ROS on JetAuto. The UI terminal is only for the touchscreen interface.

---

## 3. Environment Fix (Standard ROS Setup)

JetAuto images include mixed login shells. To avoid inconsistent ROS behavior, the environment was standardized.

Add to `~/.zshrc`:

```bash
# Load ROS
source /opt/ros/melodic/setup.bash
source $HOME/jetauto_ws/devel/setup.bash

# Always use the local ROS master on the Jetson
export ROS_MASTER_URI="http://localhost:11311"
export ROS_HOSTNAME="localhost"
```

Validate:

```bash
rosversion -d
# melodic
```

---

## 4. Launching the Robot

Start the full robot stack (motors, IMU, encoders, TF tree):

```bash
roslaunch jetauto_bringup bringup.launch
```

Check active nodes:

```bash
rosnode list
```

---

## 5. Teleoperation (Keyboard Control)

Install (once):

```bash
sudo apt install ros-melodic-teleop-twist-keyboard
```

Run:

```bash
rosrun teleop_twist_keyboard teleop_twist_keyboard.py
```

Controls:

```
i = forward
, = backward
j = turn left
l = turn right
k = stop
```

---

## 6. Motion Scripts

JetAuto includes custom scripts in `~/scripts/`.

Example:

```bash
python3 ~/scripts/move_forward_50cm.py
```

These publish to `/cmd_vel`.

---

## 7. Battery Status

Battery topic:

```bash
/ros_robot_controller/battery
```

View:

```bash
rostopic echo /ros_robot_controller/battery
```

Voltage reference:

| Voltage | Meaning              |
| ------- | -------------------- |
| 12.6 V  | Full                 |
| 12.0 V  | ~70%                 |
| 11.5 V  | ~50%                 |
| 11.0 V  | Low – recharge soon  |
| <10.8 V | Critical             |

---

## 8. LiDAR (RPLIDAR A1) – Working Configuration

This section documents the actual fix performed to get the RPLIDAR working reliably.

### 7.1. Identify USB Ports

```bash
dmesg | grep ttyUSB
```

Typical JetAuto output:

```
usb ... ch341-uart converter now attached to ttyUSB0
usb ... ch341-uart converter now attached to ttyUSB1
```

Final port for LiDAR: **`/dev/ttyUSB1`**

---

### 7.2. Check if LiDAR port is locked

```bash
sudo lsof /dev/ttyUSB0
sudo lsof /dev/ttyUSB1
```

If you see:

```
rplidarNode 7037 jetauto  9u  CHR 188,1 /dev/ttyUSB1
```

Kill it:

```bash
sudo kill <PID>
```

---

### 7.3. Test LiDAR raw data (no ROS)

```bash
sudo cat /dev/ttyUSB1
```

Expected: binary garbage.  
If nothing appears → communication issue.

---

### 7.4. Test LiDAR driver manually

**Terminal 1:**

```bash
rosrun rplidar_ros rplidarNode _serial_port:=/dev/ttyUSB1 _serial_baudrate:=115200
```

**Terminal 2:**

```bash
rostopic echo /scan
```

If `/scan` outputs ranges → LiDAR is fully working.

---

## 9. SLAM (Mapping)

### 8.1. Start bringup

Terminal 1:

```bash
roslaunch jetauto_bringup bringup.launch
```

### 8.2. Start SLAM

Terminal 2:

```bash
roslaunch jetauto_slam slam.launch
```

Check:

```bash
rostopic list | grep scan
rostopic list | grep map
```

---

### 8.3. RViz Visualization

Terminal 3:

```bash
rviz
```

Set:

- **Fixed Frame:** `map` or `odom`
- Add displays:
  - LaserScan (`/scan`)
  - Map (`/map`)
  - TF
  - RobotModel

Move the robot slowly to build the map.

---

### 8.4. Save Map

```bash
mkdir -p ~/maps
rosrun map_server map_saver -f ~/maps/jetauto_map
```

Creates:

- `jetauto_map.pgm`
- `jetauto_map.yaml`

---

## 10. Troubleshooting

### ROS master not reachable

```bash
export ROS_MASTER_URI=http://localhost:11311
export ROS_HOSTNAME=localhost
```

### Kill broken ROS processes

```bash
killall -9 roscore rosmaster roslaunch
```

### Check port usage

```bash
sudo lsof /dev/ttyUSB1
```

### LiDAR spins but no data

- Wrong port (should be `/dev/ttyUSB1`)
- Wrong baudrate (use `115200`)
- Another process locking the port
- CH341 USB instability (unplug & replug)

### Confusion between Host OS and Docker UI

**Symptoms:**
- Files created in UI terminal don't appear in SSH
- ROS commands fail in UI terminal
- Hardware devices not accessible in UI terminal
- Docker commands not found in UI terminal

**Solution:**
- Always use SSH (`ssh jetauto@jetauto.local`) for ROS development
- UI terminal is only for touchscreen interface, not for development
- All ROS work must be done in the host OS at `/home/jetauto`
- If you created files in UI terminal, they are in `/home/ubuntu` (Docker), not `/home/jetauto` (host)

---

## 11. Next Steps

- Autonomous navigation with `move_base`  
- Using saved maps for localization  
- Astra camera object tracking  
- Web UI using `rosbridge_suite`  
- Multi-robot communication  

---

## 12. License

MIT License or your preferred license.
