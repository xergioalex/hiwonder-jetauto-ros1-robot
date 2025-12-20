#!/usr/bin/env python3
"""
Simple Remote Movement Test Script
==================================

This script tests remote ROS connection by moving the robot forward and backward.
It should be run from a laptop/computer connected to the JetAuto robot via ROS.

Usage:
    # Set ROS environment variables first:
    export ROS_MASTER_URI=http://robot_ip:11311
    export ROS_HOSTNAME=your_laptop_ip
    
    # Then run:
    python3 remote_move_test.py
"""

import rospy
from geometry_msgs.msg import Twist
import time
import sys

def move_forward(duration=2.0, speed=0.3):
    """Move robot forward"""
    print("Moving forward for {:.1f} seconds at {:.1f} m/s...".format(duration, speed))
    
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    rate = rospy.Rate(10)  # 10Hz
    
    start_time = time.time()
    while (time.time() - start_time) < duration and not rospy.is_shutdown():
        twist = Twist()
        twist.linear.x = speed
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        
        pub.publish(twist)
        rate.sleep()
    
    # Stop
    stop_twist = Twist()
    pub.publish(stop_twist)
    print("Stopped")

def move_backward(duration=2.0, speed=0.3):
    """Move robot backward"""
    print("Moving backward for {:.1f} seconds at {:.1f} m/s...".format(duration, speed))
    
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    rate = rospy.Rate(10)  # 10Hz
    
    start_time = time.time()
    while (time.time() - start_time) < duration and not rospy.is_shutdown():
        twist = Twist()
        twist.linear.x = -speed
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        
        pub.publish(twist)
        rate.sleep()
    
    # Stop
    stop_twist = Twist()
    pub.publish(stop_twist)
    print("Stopped")

def main():
    """Main function"""
    print("=" * 70)
    print("Remote Movement Test - JetAuto Robot")
    print("=" * 70)
    print("")
    print("This script will:")
    print("  1. Move the robot forward for 2 seconds")
    print("  2. Wait 1 second")
    print("  3. Move the robot backward for 2 seconds")
    print("  4. Stop")
    print("")
    
    # Check ROS environment variables
    ros_master_uri = rospy.get_master_uri()
    print("ROS Master URI: {}".format(ros_master_uri))
    print("")
    
    # Initialize ROS node
    print("Initializing ROS node...")
    try:
        rospy.init_node('remote_move_test', anonymous=True)
        print("✓ ROS node initialized")
    except rospy.ROSException as e:
        print("✗ Error initializing ROS node: {}".format(e))
        print("")
        print("Make sure:")
        print("  1. ROS Master is running on the robot")
        print("  2. ROS_MASTER_URI is set correctly")
        print("  3. ROS_HOSTNAME is set to your laptop IP")
        print("  4. You can reach the robot on the network")
        sys.exit(1)
    
    # Wait a moment for publisher to register
    time.sleep(0.5)
    
    # Check if we can see the /cmd_vel topic
    try:
        topics = rospy.get_published_topics()
        cmd_vel_found = any('/cmd_vel' in topic[0] for topic in topics)
        if not cmd_vel_found:
            print("⚠️  Warning: /cmd_vel topic not found in published topics")
            print("   The robot may not be subscribed to /cmd_vel")
            print("   Continuing anyway...")
        else:
            print("✓ /cmd_vel topic available")
    except Exception as e:
        print("⚠️  Warning: Could not check topics: {}".format(e))
        print("   Continuing anyway...")
    
    print("")
    print("Starting movement sequence in 2 seconds...")
    print("Press Ctrl+C to stop")
    print("")
    time.sleep(2.0)
    
    try:
        # Move forward
        move_forward(duration=2.0, speed=0.3)
        
        # Wait between movements
        print("Waiting 1 second...")
        time.sleep(1.0)
        
        # Move backward
        move_backward(duration=2.0, speed=0.3)
        
        # Final stop
        print("")
        print("=" * 70)
        print("Test completed successfully!")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("")
        print("Interrupted by user")
        # Stop robot
        pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        stop_twist = Twist()
        pub.publish(stop_twist)
        print("Robot stopped")
    except rospy.ROSInterruptException:
        print("ROS interrupt detected")
    except Exception as e:
        print("Error: {}".format(e))
        import traceback
        traceback.print_exc()
        # Stop robot on error
        try:
            pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
            stop_twist = Twist()
            pub.publish(stop_twist)
        except:
            pass

if __name__ == "__main__":
    main()



