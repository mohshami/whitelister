__author__ = 'Mohammad Al-Shami'

import os
import sys
import yaml


# Modularize configuration file loading
class ConfigLoader():
	@classmethod
	def load(self, loader, configFile):
		# Get the path to where this script is installed
		path = os.path.dirname(os.path.abspath(loader))

		# Load our settings
		try:
			with open("%s/%s" % (path, configFile), "r") as f:
				settings = yaml.load(f)
				settings['path'] = path
		except IOError, e:
			print "Error loading %s" % configFile
			sys.exit(0)

		return settings
