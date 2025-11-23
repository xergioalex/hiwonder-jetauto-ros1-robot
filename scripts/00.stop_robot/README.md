# Emergency Stop Scripts

🛑 **EMERGENCY STOP** - Use these scripts to immediately stop the robot when it won't stop by other means.

## Description

Two emergency scripts are provided:

1. **stop.py** - Publishes STOP commands continuously (RECOMMENDED)
2. **kill_controllers.sh** - Kills all robot control processes (NUCLEAR OPTION)

## Requirements

- **ROS1** (Melodic or compatible)
- **Python 3.6+**
- **rospy** (comes with ROS)

**NO OpenAI API key needed** - This script has zero dependencies beyond ROS.

## Usage

### Method 1: Continuous Stop (RECOMMENDED)

This keeps the robot stopped by continuously publishing STOP commands:

```bash
cd scripts/00.stop_robot
python stop.py
```

**Output:**
```
============================================================
🛑 EMERGENCY STOP - Publishing STOP commands continuously
============================================================
The robot is now stopped and will STAY stopped.
This script will keep publishing STOP commands at 10Hz.

Press Ctrl+C when you want to exit this script.
(Robot will remain stopped after you exit)
============================================================

Still publishing STOP... (10 commands sent)
Still publishing STOP... (20 commands sent)
...
```

**How it works:**
- Publishes zero velocities at 10Hz continuously
- Overrides any other commands being sent
- Press Ctrl+C to exit (robot stays stopped)
- Shows counter every second

### Method 2: Kill All Controllers (NUCLEAR OPTION)

If stop.py doesn't work, kill all control processes first:

```bash
cd scripts/00.stop_robot
./kill_controllers.sh
python stop.py
```

**What kill_controllers.sh does:**
- Kills all Python controller scripts
- Kills teleop_twist_keyboard processes
- Kills processes publishing to /cmd_vel
- Ensures nothing is sending movement commands

### Alternative: Make it global

Add an alias to your `~/.bashrc` or `~/.zshrc`:

```bash
alias stop-robot="python /path/to/hiwonder-jetauto-ros1-robot/scripts/00.stop_robot/stop.py"
```

Then from anywhere:
```bash
stop-robot
```

## When to use

- Robot is moving unexpectedly
- Robot won't stop with normal commands
- Emergency situation
- After running text control and robot keeps moving
- Battery is low and robot behaving erratically
- Testing/debugging

## Why the robot might not stop

### Common causes:
1. **Multiple publishers competing** - Another script is still sending movement commands
2. **Controller still running** - The LLM controller didn't finish its sequence
3. **Hardware issue** - Low battery can cause erratic behavior
4. **Motor controller stuck** - Need to restart the robot

### Solutions:
1. **First try:** `python stop.py` (continuous stop)
2. **If that fails:** `./kill_controllers.sh` then `python stop.py`
3. **If still moving:** Check battery voltage, might need to power cycle robot
4. **Last resort:** Power off the robot physically

## Troubleshooting

### "ROS Master not found"
Make sure ROS is running:
```bash
roscore
```

Or if using robot launch file:
```bash
roslaunch jetauto_bringup bringup.launch
```

### Script doesn't work
1. Verify ROS environment is sourced:
   ```bash
   source /opt/ros/melodic/setup.bash
   source ~/jetauto_ws/devel/setup.bash
   ```

2. Check if `/cmd_vel` topic exists:
   ```bash
   rostopic list | grep cmd_vel
   ```

3. Manually publish stop command:
   ```bash
   rostopic pub /cmd_vel geometry_msgs/Twist "linear:
     x: 0.0
     y: 0.0
     z: 0.0
   angular:
     x: 0.0
     y: 0.0
     z: 0.0" -r 10
   ```

## Notes

- This script is intentionally simple with minimal dependencies
- It publishes the stop command multiple times to ensure reliability
- No configuration needed - just run it
- Works independently of other control scripts
