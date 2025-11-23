#!/bin/bash
# Kill all robot control scripts
# Use this if the robot won't stop and you need to kill all control processes

echo "========================================================"
echo "🛑 KILLING ALL ROBOT CONTROL PROCESSES"
echo "========================================================"
echo ""

# Kill Python scripts that might be controlling the robot
echo "Looking for Python controller scripts..."
pkill -9 -f "controller_llm.py"
pkill -9 -f "parser_llm.py"
pkill -9 -f "teleop_twist_keyboard"

# Kill any process publishing to /cmd_vel
echo "Looking for processes publishing to /cmd_vel..."
for pid in $(rostopic info /cmd_vel 2>/dev/null | grep -A 10 "Publishers:" | grep -oP "http://.*:(\d+)" | cut -d: -f2); do
    echo "  Killing process on port $pid"
    fuser -k $pid/tcp 2>/dev/null
done

# Alternative: kill by process name patterns
echo "Killing any remaining controller processes..."
pkill -9 -f "llm_multi_command_controller"
pkill -9 -f "emergency_stop"

echo ""
echo "========================================================"
echo "✅ Done! All controller processes should be killed."
echo "========================================================"
echo ""
echo "Now run: python stop.py"
echo "to publish STOP commands to the robot."
echo ""
