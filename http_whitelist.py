#!/usr/bin/env python2.7
__author__ = 'Mohammad Al-Shami'

import multiprocessing
import zmq
import msgpack
import urllib2
import re
from ConfigLoader import ConfigLoader


def getIPs(url):
	# Get the html for the page containing the list of CIDRs
	response = urllib2.urlopen(url)
	html = response.read()

	# Get IPv4 addresses
	pattern = r'[^\d]((?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'\
		+ '(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'\
		+ '(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'\
		+ '(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'\
		+ '(?:/(?:3[0-2]|[1-2]?[0-9]))?)'
	matches = re.findall(pattern, html)

	return matches


def worker(**kwargs):
	settings = kwargs['settings']

	# Prepare pull socket
	context = zmq.Context()
	workerSocket = context.socket(zmq.REQ)
	workerSocket.connect(settings['dispatcher'])

	prevResult = ''

	# Read RBL list from socket
	while True:
		# Inform the dispatcher that we are ready
		workerSocket.send_multipart([b"ready", prevResult])

		# Get the IP and RBL
		url = workerSocket.recv()

		# Check if this was a terminate, if so, exit the loop and terminate
		if url == 'term':
			break

		ips = getIPs(url)
		# At first, the script checked if the returned set of IPs is empty
		# Now we just return empty sets so we can check for any potential issues
		# if len(ips) > 0:
		prevResult = msgpack.packb([url, ips])

def main():
	IPs = dict()

	# Get settings from configuration file
	settings = ConfigLoader.load(__file__, 'whitelist.cf')

	# Prepare the dispatcher socket
	context = zmq.Context()
	dispatcher = context.socket(zmq.ROUTER)
	dispatcher.bind(settings['dispatcher'])

	# Start the worker processes
	processes = []
	for thread in xrange(settings['processes']):
		p = multiprocessing.Process(target=worker, kwargs={'settings': settings})
		processes.append(p)
		p.start()

	# Send jobs to the active threads
	for url in settings['httpLists']:
		# LRU worker is next waiting in the queue
		address, empty, ready, prevResult = dispatcher.recv_multipart()

		# Send the task to the worker
		dispatcher.send_multipart([address, b'', url])

		# The worker might have sent a result with the ready message
		if prevResult == '':
			continue

		# We received a result, add it to the dictionary
		IPs[prevResult] = 1

	# We're done, tell workers to exit
	for i in range(settings['processes']):
		# LRU worker is next waiting in the queue
		address, empty, ready, prevResult = dispatcher.recv_multipart()

		dispatcher.send_multipart([address, b'', b'term'])

		# The worker might have sent a result with the ready message
		if prevResult == '':
			continue

		# We received a result, add it to the dictionary
		IPs[prevResult] = 1

	for ipSet in IPs:
		ips = msgpack.unpackb(ipSet)
		print "#{}".format(ips[0])
		for IP in ips[1]:
			print IP


if __name__ == '__main__':
	main()