import rospy
from geometry_msgs.msg import Twist
import openai
import json
import time
import os
from dotenv import load_dotenv
from parser_llm import split_into_steps

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

def load_system_prompt():
    with open(os.path.join(os.path.dirname(__file__), "prompts", "system.txt"), "r") as f:
        return f.read()

def ask_llm_for_twist(command, system_prompt):
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command},
        ]
    )
    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {"linear": {"x": 0, "y": 0, "z": 0}, "angular": {"x": 0, "y": 0, "z": 0}}

def execute_sequence(commands):
    rospy.init_node('llm_multi_command_controller')
    pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
    rate = rospy.Rate(1)
    system_prompt = load_system_prompt()

    for cmd in commands:
        print(f"Executing: {cmd}")
        twist_data = ask_llm_for_twist(cmd, system_prompt)
        twist = Twist()
        twist.linear.x = twist_data['linear']['x']
        twist.linear.y = twist_data['linear']['y']
        twist.linear.z = twist_data['linear']['z']
        twist.angular.x = twist_data['angular']['x']
        twist.angular.y = twist_data['angular']['y']
        twist.angular.z = twist_data['angular']['z']
        pub.publish(twist)
        time.sleep(2)
        pub.publish(Twist())  # Stop after each step
        rate.sleep()

if __name__ == "__main__":
    user_input = input("Enter a multi-step command (English or Spanish): ")
    steps = split_into_steps(user_input)
    print(f"Steps: {steps}")
    execute_sequence(steps)
