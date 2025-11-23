# JetAuto ROS1 Robot (Hiwonder) – Quick Start Guide

This repository documents the setup, environment configuration, and basic operation workflow for the **Hiwonder JetAuto** robot running **ROS1 Melodic** on **Jetson Orin/Nano**.

It summarizes the core steps we validated, common fixes, and scripts used to bring the robot to a fully working state.

---

## 1. System Overview

**Robot:** Hiwonder JetAuto 4WD Mobile Robot
**OS:** Ubuntu 18.04.6 LTS (Jetson)
**ROS:** ROS1 Melodic
**Sensors:**

* RPLIDAR A1 (LiDAR)
* Astra Pro Plus (RGB-D camera)
* IMU
* Motor Encoders

**Key ROS Packages:**

* `jetauto_bringup`
* `jetauto_driver`
* `jetauto_slam`
* `jetauto_navigation`
* `rplidar_ros`
* `orbbec_camera`
* `robot_localization`

---

## 2. Fixing the Environment (ROS Setup)

JetAuto images contain several custom startup scripts. To avoid issues, we standardized the ROS environment by using the user shell (`.zshrc` or `.zlogin`).

### Final ROS Environment

```bash
# Load ROS
source /opt/ros/melodic/setup.bash
source $HOME/jetauto_ws/devel/setup.bash

# Always use local master
export ROS_MASTER_URI="http://localhost:11311"
export ROS_HOSTNAME="localhost"
```

This ensures the SSH shell always connects to the running ROS master on the robot.

---

## 3. Running the Robot

### Check active nodes

```bash
rosnode list
```

### Teleoperation (Keyboard Control)

Install once:

```bash
sudo apt install ros-melodic-teleop-twist-keyboard
```

Run teleop:

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

## 4. Basic Python Scripts

JetAuto includes custom motion scripts under `~/scripts/`.

Example:

```bash
python3 ~/scripts/move_forward_50cm.py
```

These scripts publish to `/cmd_vel` after bringup is active.

---

## 5. Battery Status

JetAuto publishes battery voltage on:

```bash
/ros_robot_controller/battery
```

Check real‑time value:

```bash
rostopic echo /ros_robot_controller/battery
```

Values are in **millivolts (mV)**. Example:

```
11310 → ~11.31 V (≈35–40%)
```

Battery reference:

| Voltage  | Meaning                     |
| -------- | --------------------------- |
| 12.6 V   | Full                        |
| 12.0 V   | ~70%                        |
| 11.5 V   | ~50%                        |
| 11.0 V   | Low – recharge soon         |
| < 10.8 V | Critical (LiPo damage risk) |

---

## 6. SLAM (Mapping)

JetAuto provides SLAM launch files under:

```bash
roscd jetauto_slam
ls launch
```

Expected files:

* `slam.launch`
* `rviz_slam.launch`

### Start SLAM

```bash
roslaunch jetauto_slam slam.launch
```

### Start RViz for viewing

```bash
roslaunch jetauto_slam rviz_slam.launch
```

### Save Generated Map

```bash
mkdir -p ~/maps
rosrun map_server map_saver -f ~/maps/jetauto_map
```

This produces:

* `jetauto_map.pgm`
* `jetauto_map.yaml`

---

## 7. Launch Bringup (if not running automatically)

```bash
roslaunch jetauto_bringup bringup.launch
```

This starts:

* Motor controller
* Odometry
* IMU filter
* LiDAR driver
* Camera driver
* Base TF tree

---

## 8. Troubleshooting

### ROS Master not reachable

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
sudo lsof -i:11311
```

---

## 9. Next Steps

* Autonomous navigation using saved map
* Object tracking with Astra camera
* Web control interface via rosbridge
* Multi-robot JetAuto configuration

---

## 10. License

MIT or specify your preferred license.
