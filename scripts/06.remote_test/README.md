# Remote Movement Test - Script 06

This is a simple test script to verify remote ROS connection between your laptop and the JetAuto robot.

## Purpose

This script performs a simple test:
1. Moves the robot forward for 2 seconds
2. Waits 1 second
3. Moves the robot backward for 2 seconds
4. Stops

It's designed to test that:
- Your laptop can connect to the robot's ROS Master
- Commands can be sent remotely via ROS topics
- The robot receives and executes the commands

## Requirements

### On Robot (JetAuto)
- ROS Master must be running (`roscore` or `roslaunch jetauto_bringup bringup.launch`)
- Robot must be subscribed to `/cmd_vel` topic (usually handled by `jetauto_bringup`)

### On Laptop
- Python 3.6+ (works with any Python version)
- ROS installed and configured
- Network connection to the robot

## Setup

### Step 1: Get Robot IP Address

On the robot (via SSH or local terminal):
```bash
hostname -I
# Example output: 192.168.1.100
```

### Step 2: Get Laptop IP Address

On your laptop:
```bash
# macOS:
ipconfig getifaddr en0
# or
ifconfig | grep "inet " | grep -v 127.0.0.1

# Linux:
hostname -I
```

### Step 3: Configure ROS Environment Variables

On your laptop, set these environment variables:
```bash
export ROS_MASTER_URI=http://ROBOT_IP:11311
export ROS_HOSTNAME=YOUR_LAPTOP_IP

# Example:
export ROS_MASTER_URI=http://192.168.1.100:11311
export ROS_HOSTNAME=192.168.1.50
```

### Step 4: Verify Connection

Test that you can connect to the robot:
```bash
# List topics (should show robot's topics)
rostopic list

# Check if /cmd_vel exists
rostopic list | grep cmd_vel

# Echo /cmd_vel to see if robot is publishing (optional)
rostopic echo /cmd_vel
```

## Usage

### Basic Usage

```bash
# Make sure ROS environment variables are set
export ROS_MASTER_URI=http://robot_ip:11311
export ROS_HOSTNAME=your_laptop_ip

# Run the test script
cd scripts/06.remote_test
python3 remote_move_test.py
```

### Expected Output

```
======================================================================
Remote Movement Test - JetAuto Robot
======================================================================

This script will:
  1. Move the robot forward for 2 seconds
  2. Wait 1 second
  3. Move the robot backward for 2 seconds
  4. Stop

ROS Master URI: http://192.168.1.100:11311

Initializing ROS node...
✓ ROS node initialized
✓ /cmd_vel topic available

Starting movement sequence in 2 seconds...
Press Ctrl+C to stop

Moving forward for 2.0 seconds at 0.3 m/s...
Stopped
Waiting 1 second...
Moving backward for 2.0 seconds at 0.3 m/s...
Stopped

======================================================================
Test completed successfully!
======================================================================
```

## Troubleshooting

### Cannot Connect to ROS Master

**Error**: `Error initializing ROS node: ...`

**Solutions**:
1. Verify robot IP is correct:
   ```bash
   ping ROBOT_IP
   ```

2. Verify ROS Master is running on robot:
   ```bash
   # On robot:
   roscore
   # Or:
   roslaunch jetauto_bringup bringup.launch
   ```

3. Check if port 11311 is accessible:
   ```bash
   # From laptop:
   telnet ROBOT_IP 11311
   # Or:
   nc -zv ROBOT_IP 11311
   ```

4. Verify firewall is not blocking:
   ```bash
   # On robot (if firewall is enabled):
   sudo ufw allow 11311/tcp
   ```

### Robot Doesn't Move

**Possible causes**:
1. Robot is not subscribed to `/cmd_vel`:
   ```bash
   # On robot, check subscribers:
   rostopic info /cmd_vel
   # Should show at least one subscriber
   ```

2. Robot driver is not running:
   ```bash
   # On robot:
   roslaunch jetauto_bringup bringup.launch
   ```

3. Wrong topic name:
   ```bash
   # Check what topics the robot is listening to:
   rostopic list
   ```

### Network Issues

**If robot and laptop are on different networks**:
- Connect both to the same WiFi network
- Or use Ethernet connection
- Or set up a network bridge

**If using WiFi**:
- Make sure both devices are on the same subnet
- Check router settings (some routers isolate devices)

## Next Steps

Once this test works, you can:
- Try Script 05 (Realtime API) for voice control from laptop
- Develop more complex remote control scripts
- Use this as a template for other remote ROS scripts

## File Structure

```
06.remote_test/
├── remote_move_test.py  # Main test script
└── README.md            # This file
```

## Notes

- The script uses a speed of 0.3 m/s (moderate speed)
- Movement duration is 2 seconds each direction
- The script automatically stops the robot if interrupted (Ctrl+C)
- All movement commands are sent at 10Hz for smooth control

