#!/usr/bin/env python3

import os
import sys
import yaml
import glob
import rospy
import shutil
import roslaunch
import subprocess as sb

from buffpy_tools import *
from robot_description import Robot_Description

class Robot_Spawner:
	"""
		A tool that works directly with Robot Descriptions
		to start the systems.

		This is where the launching happens, formerly called
		  Odyssey Launch Platform, now just run
	"""

	def __init__(self):
		self.commands = None
		self.respawn = None

		self.pool = None
		self.launch = None
		self.roscore = None

	def launch_ros_core(self):
		# launch core
		self.roscore = sb.Popen('roscore', stdout=sb.PIPE, stderr=sb.PIPE)
		self.launch = roslaunch.scriptapi.ROSLaunch()
		self.launch.start()

	def set_ros_params(self, name, with_xacro):
		"""
			ROS-Param server is a great tool and allows us to use ROS's vizualizer tools

			This function uploads a URDF (xacro) to the server along with a few other
			  variables that programs might want to know
		"""
		namespace = '/buffbot'
		params = {'robot-name': name}
		if (with_xacro):
			command_string = f"rosrun xacro xacro {os.path.join(BuffPy_LOC_LUT['robots'], name, 'buffbot.xacro')}"
			robot_description = sb.check_output(command_string, shell=True, stderr=sb.STDOUT)
			params['description'] = robot_description.decode()

		rospy.set_param(f'{namespace}', params)

	def spawn_nodes(self):
		"""
			Spawn the commands generated by the robot description

			The commands are already created, just pass them to 
			  this launcher
		"""
		print(f"Spawning {len(self.commands)} nodes")
		for (i,cmd) in enumerate(self.commands):
			print(f"Starting {cmd}")
			if self.pool is None:
				self.pool = {}

			process = sb.Popen(cmd)
			self.pool[''.join(cmd)] = process

	def launch_system(self, name, with_xacro):
		"""
			Wraper for functionality

			Launch a ROS core, set the ROS params and spawn the nodes

			@param
				name: name of the robot
				with_xacro: bool weather or not to load the URDF (xacro)
		"""
		project_root = os.getenv('PROJECT_ROOT')

		self.launch_ros_core()
		self.set_ros_params(name, with_xacro)
		self.spawn_nodes()

	def spin(self, robot):
		"""
			Initialize the run and launch nodes
			loop and wait for user kill, an error or core to finish
			PARAMS:
				robot
		"""

		# load the description
		rd = Robot_Description()
		rd.load_description(robot)
		self.respawn, self.commands = rd.get_commands()

		# Try to catch user kill and other errors
		try: 
			self.launch_system(rd.name, rd.with_xacro)
			# core_process is the core process we are trying to spawn (python script or roscore)
			# if it fails there is no point in spinning
			if self.roscore is None: 
				print('Failed to launch core :(')
				exit(0)

			# this hanldes user kill (available after spawn & in the run space below)
			# this will loop until an interrupt or the core dies.
			while self.roscore.poll() is None:
				# restart processes with the respawn flag
				if not self.pool is None:
					for (i, cmd) in enumerate(self.commands):
						proc = self.pool[''.join(cmd)]
						if not proc is None and not proc.poll() is None:
							if proc.returncode != 0 and self.respawn[i]:
								print(f'{self.commands[i]} died: {proc.returncode}')
								spawn_nodes(self.commands[i])

		except KeyboardInterrupt as e:
			print(e)
			print('Terminate Recieved')

		except Exception as e:
			print(e)
			print('Killed due to error')

		if not self.pool is None:
			for (i, cmd) in enumerate(self.commands):
				proc = self.pool[''.join(cmd)]
				if not proc is None:
					proc.terminate()

		if not self.roscore is None:
			self.roscore.terminate()


def main():
	"""
		If someone asks where our run script is... here it is
		  and it's not much of a script anymore
	"""
	if len(sys.argv) < 2:
		with open(os.path.join(BuffPy_LOC_LUT['robots'], 'self.txt'), 'r') as f:
			robot = f.read()
	else:
		robot = sys.argv[1]
		# with open(os.path.join(BuffPy_LOC_LUT['robots'], 'self.txt'), 'w') as f:
		# 	f.write(robot)


	rs = Robot_Spawner()
	rs.spin(robot)

if __name__ == '__main__':
	main()