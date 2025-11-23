#!/usr/bin/env python
"""
Emergency Stop Script for JetAuto Robot

This script immediately stops the robot by publishing zero velocities
to the /cmd_vel topic. Use this when the robot is moving unexpectedly
or won't stop.

Usage:
    python stop.py
"""

import rospy
from geometry_msgs.msg import Twist
import sys

def emergency_stop():
    """Publish zero velocities to stop the robot immediately"""
    try:
        # Initialize ROS node
        rospy.init_node('emergency_stop', anonymous=True)

        # Create publisher for velocity commands
        pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        # Wait a bit for publisher to initialize
        rospy.sleep(0.2)

        # Create stop message (all zeros)
        stop_msg = Twist()
        stop_msg.linear.x = 0.0
        stop_msg.linear.y = 0.0
        stop_msg.linear.z = 0.0
        stop_msg.angular.x = 0.0
        stop_msg.angular.y = 0.0
        stop_msg.angular.z = 0.0

        # Publish stop command multiple times to ensure it's received
        print("=" * 50)
        print("EMERGENCY STOP - Stopping robot NOW!")
        print("=" * 50)

        for i in range(10):
            pub.publish(stop_msg)
            print("Published STOP command {}/10".format(i + 1))
            rospy.sleep(0.1)

        print("=" * 50)
        print("Robot should be stopped now.")
        print("=" * 50)

    except rospy.ROSInterruptException:
        print("ROS interrupted, exiting...")
    except Exception as e:
        print("Error: {}".format(e))
        sys.exit(1)

if __name__ == "__main__":
    emergency_stop()
