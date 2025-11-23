# Emergency Stop Script

🛑 **EMERGENCY STOP** - Use this script to immediately stop the robot when it won't stop by other means.

## Description

This is a simple, no-dependencies emergency stop script that publishes zero velocities to `/cmd_vel` to stop the robot immediately.

## Requirements

- **ROS1** (Melodic or compatible)
- **Python 3.6+**
- **rospy** (comes with ROS)

**NO OpenAI API key needed** - This script has zero dependencies beyond ROS.

## Usage

### Quick Stop (From anywhere in the repository)

```bash
cd scripts/00.stop_robot
python stop.py
```

### Alternative: Make it global

Add an alias to your `~/.bashrc` or `~/.zshrc`:

```bash
alias stop-robot="python /path/to/hiwonder-jetauto-ros1-robot/scripts/00.stop_robot/stop.py"
```

Then from anywhere:
```bash
stop-robot
```

## What it does

1. Initializes a ROS node
2. Creates a publisher to `/cmd_vel`
3. Publishes zero velocities 10 times (1 second total)
4. Ensures the robot receives the stop command

## When to use

- Robot is moving unexpectedly
- Robot won't stop with normal commands
- Emergency situation
- Testing/debugging

## Output Example

```
==================================================
EMERGENCY STOP - Stopping robot NOW!
==================================================
Published STOP command 1/10
Published STOP command 2/10
Published STOP command 3/10
...
Published STOP command 10/10
==================================================
Robot should be stopped now.
==================================================
```

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
