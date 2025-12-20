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

## 2. Initial Setup: SSH Connection and WiFi Configuration

### 2.1. Understanding the Initial Access Challenge

⚠️ **IMPORTANT**: The JetAuto robot's built-in touchscreen displays a **Docker container UI**, not the real host operating system. This means you **cannot** directly access the host OS from the touchscreen interface.

**Why this matters:**
- The touchscreen shows a Docker container environment (`/home/ubuntu`)
- The real host OS is at `/home/jetauto` (not accessible from the UI)
- SSH is the **only** way to access the real host OS for ROS development
- WiFi configuration must be done on the host OS, not in the Docker container

### 2.2. Accessing Host Mode from the Touchscreen (First-Time Setup)

If you don't have SSH access yet, you need to access the host OS through the touchscreen:

**Steps:**

1. **Connect a USB keyboard** to the robot
2. **Open a terminal** on the touchscreen (if available in the Docker UI)
3. **Press the key combination to enter host mode** (typically `Ctrl+Alt+F1` or `Ctrl+Alt+T` depending on the JetAuto firmware)
   - This switches from the Docker container to the real host OS
   - You should see a different terminal prompt (host OS terminal)
4. **Login credentials:**
   - **Username:** `jetauto`
   - **Default password:** `hiwonder`

> **Note:** The exact key combination may vary by firmware version. If `Ctrl+Alt+F1` doesn't work, try `Ctrl+Alt+F2`, `Ctrl+Alt+F3`, or check the JetAuto documentation for your specific firmware version.

### 2.3. WiFi Configuration

Once you have access to the host OS (either via host mode or SSH), configure WiFi:

**Path to WiFi configuration file:**
```bash
/home/jetauto/hiwonder-toolbox/hiwonder_wifi_conf.py
```

**Steps to configure WiFi:**

1. **Edit the WiFi configuration file:**
   ```bash
   sudo nano /home/jetauto/hiwonder-toolbox/hiwonder_wifi_conf.py
   ```

2. **Update the following settings:**
   ```python
   HW_WIFI_MODE = 2                           # Change from 1 to 2
   HW_WIFI_STA_SSID = 'YourActualWiFiName'    # Replace with your network name
   HW_WIFI_STA_PASSWORD = 'YourActualPassword' # Replace with your password
   ```

3. **Restart the WiFi service:**
   ```bash
   sudo systemctl restart hw_wifi.service
   ```

4. **Verify connection:**
   ```bash
   ifconfig
   # or
   ip addr show
   ```

The robot should now connect to your WiFi network.

### 2.4. Connecting via SSH

Once WiFi is configured, connect via SSH from your computer:

**From your local machine:**

```bash
ssh jetauto@jetauto.local
```

**Or if `jetauto.local` doesn't resolve, use the robot's IP address:**

```bash
ssh jetauto@<robot-ip-address>
```

**Login credentials:**
- **Username:** `jetauto`
- **Default password:** `hiwonder`

**First-time SSH connection:**
- You'll be prompted to accept the host key fingerprint (type `yes`)
- Enter the password when prompted

**After successful connection:**
- You're now in the real host OS at `/home/jetauto`
- All ROS development should be done here
- See [Section 3: System Architecture](#3-system-architecture-host-os-vs-docker-ui) for details on the dual-environment setup

**Alternative: If you already have SSH access:**
- You can directly edit the WiFi configuration file without accessing host mode
- Simply SSH into the robot and follow the WiFi configuration steps above

### 2.5. Changing the Default Password (Recommended)

For security, change the default password after first login:

```bash
passwd
```

Enter the current password (`hiwonder`), then set a new secure password.

---

## 3. System Architecture: Host OS vs Docker UI

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

## 4. Environment Fix (Standard ROS Setup)

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

## 5. Launching the Robot

Start the full robot stack (motors, IMU, encoders, TF tree):

```bash
roslaunch jetauto_bringup bringup.launch
```

Check active nodes:

```bash
rosnode list
```

---

## 6. Teleoperation (Keyboard Control)

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

## 7. Motion Scripts

JetAuto includes custom scripts in `~/scripts/`.

Example:

```bash
python3 ~/scripts/move_forward_50cm.py
```

These publish to `/cmd_vel`.

---

## 8. Battery Status

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

## 9. LiDAR (RPLIDAR A1) – Working Configuration

This section documents the actual fix performed to get the RPLIDAR working reliably.

### 9.1. Identify USB Ports

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

### 9.2. Check if LiDAR port is locked

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

### 9.3. Test LiDAR raw data (no ROS)

```bash
sudo cat /dev/ttyUSB1
```

Expected: binary garbage.  
If nothing appears → communication issue.

---

### 9.4. Test LiDAR driver manually

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

## 10. SLAM (Mapping)

### 10.1. Start bringup

Terminal 1:

```bash
roslaunch jetauto_bringup bringup.launch
```

### 10.2. Start SLAM

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

### 10.3. RViz Visualization

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

### 10.4. Save Map

```bash
mkdir -p ~/maps
rosrun map_server map_saver -f ~/maps/jetauto_map
```

Creates:

- `jetauto_map.pgm`
- `jetauto_map.yaml`

---

## 11. Troubleshooting

### Cannot connect via SSH

**Symptoms:**
- `ssh jetauto@jetauto.local` fails
- Connection timeout or "Host unreachable"
- `jetauto.local` doesn't resolve

**Solutions:**

1. **Find the robot's IP address:**
   - Check your router's DHCP client list
   - Or connect via USB keyboard and check in host mode:
     ```bash
     ifconfig
     # or
     hostname -I
     ```

2. **Use IP address instead of hostname:**
   ```bash
   ssh jetauto@<robot-ip-address>
   ```

3. **Verify SSH service is running:**
   - In host mode (via USB keyboard), check:
     ```bash
     sudo systemctl status ssh
     # If not running:
     sudo systemctl start ssh
     sudo systemctl enable ssh
     ```

4. **Check firewall settings:**
   ```bash
   sudo ufw status
   # If needed, allow SSH:
   sudo ufw allow ssh
   ```

5. **Default credentials:**
   - Username: `jetauto`
   - Password: `hiwonder`

### WiFi not connecting

**Symptoms:**
- Robot doesn't connect to WiFi network
- WiFi configuration changes don't take effect

**Solutions:**

1. **Verify configuration file path:**
   ```bash
   sudo nano /home/jetauto/hiwonder-toolbox/hiwonder_wifi_conf.py
   ```

2. **Check settings:**
   - `HW_WIFI_MODE` should be `2` (not `1`)
   - `HW_WIFI_STA_SSID` must match your network name exactly
   - `HW_WIFI_STA_PASSWORD` must be correct

3. **Restart WiFi service:**
   ```bash
   sudo systemctl restart hw_wifi.service
   sudo systemctl status hw_wifi.service
   ```

4. **Check WiFi interface:**
   ```bash
   ifconfig wlan0
   # or
   ip addr show wlan0
   ```

5. **Verify you're editing on the host OS, not Docker:**
   - Configuration must be done via SSH or host mode
   - Docker container changes won't affect WiFi

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

## 12. Next Steps

- Autonomous navigation with `move_base`  
- Using saved maps for localization  
- Astra camera object tracking  
- Web UI using `rosbridge_suite`  
- Multi-robot communication  

---

## 13. License

MIT License or your preferred license.
