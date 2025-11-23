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

## 2. Environment Fix (Standard ROS Setup)

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

## 3. Launching the Robot

Start the full robot stack (motors, IMU, encoders, TF tree):

```bash
roslaunch jetauto_bringup bringup.launch
```

Check active nodes:

```bash
rosnode list
```

---

## 4. Teleoperation (Keyboard Control)

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

## 5. Motion Scripts

JetAuto includes custom scripts in `~/scripts/`.

Example:

```bash
python3 ~/scripts/move_forward_50cm.py
```

These publish to `/cmd_vel`.

---

## 6. Battery Status

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

## 7. LiDAR (RPLIDAR A1) – Working Configuration

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

## 8. SLAM (Mapping)

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

## 9. Troubleshooting

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

---

## 10. Next Steps

- Autonomous navigation with `move_base`  
- Using saved maps for localization  
- Astra camera object tracking  
- Web UI using `rosbridge_suite`  
- Multi-robot communication  

---

## 11. License

MIT License or your preferred license.
