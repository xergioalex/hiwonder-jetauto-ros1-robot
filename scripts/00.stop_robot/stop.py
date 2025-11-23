#!/usr/bin/env python
"""
Emergency Stop Script for JetAuto Robot

This script immediately stops the robot by publishing zero velocities
to the /cmd_vel topic CONTINUOUSLY until you press Ctrl+C.

This ensures the robot stays stopped even if other scripts try to move it.

Usage:
    python stop.py

    Press Ctrl+C to exit (robot will stay stopped)
"""

import rospy
from geometry_msgs.msg import Twist
import sys
import signal

# Global flag for graceful shutdown
should_stop = False

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global should_stop
    print("\n" + "=" * 60)
    print("Ctrl+C detected - Stopping script...")
    print("Robot will remain stopped (last command was STOP)")
    print("=" * 60)
    should_stop = True

def emergency_stop():
    """Publish zero velocities continuously to keep robot stopped"""
    global should_stop

    try:
        # Initialize ROS node
        rospy.init_node('emergency_stop', anonymous=True)

        # Create publisher for velocity commands
        pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

        # Create rate for 10Hz publishing
        rate = rospy.Rate(10)  # 10 Hz

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

        print("=" * 60)
        print("EMERGENCY STOP - Publishing STOP commands continuously")
        print("=" * 60)
        print("The robot is now stopped and will STAY stopped.")
        print("This script will keep publishing STOP commands at 10Hz.")
        print("")
        print("Press Ctrl+C when you want to exit this script.")
        print("(Robot will remain stopped after you exit)")
        print("=" * 60)
        print("")

        count = 0
        while not rospy.is_shutdown() and not should_stop:
            pub.publish(stop_msg)
            count += 1

            # Print status every second (10 publishes at 10Hz)
            if count % 10 == 0:
                print("Still publishing STOP... ({} commands sent)".format(count))

            rate.sleep()

        # Final message
        print("\n" + "=" * 60)
        print("Emergency stop script finished.")
        print("Total STOP commands sent: {}".format(count))
        print("=" * 60)

    except rospy.ROSInterruptException:
        print("ROS interrupted, exiting...")
    except Exception as e:
        print("Error: {}".format(e))
        sys.exit(1)

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    emergency_stop()
