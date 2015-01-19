#!/usr/bin/env python2.7
__author__ = 'Mohammad Al-Shami'

import multiprocessing
import zmq
import msgpack
from ConfigLoader import ConfigLoader
from SPFFinder import SPFFinder

def RBLworker(**kwargs):
	settings = kwargs['settings']

	# Prepare pull socket
	context = zmq.Context()
	worker = context.socket(zmq.REQ)
	worker.connect(settings['dispatcher'])

	prevResult = ''

	# Read RBL list from socket
	while True:
		# Inform the dispatcher that we are ready
		worker.send_multipart([b"ready", prevResult])

		# Reset the previous result value
		prevResult = ''

		# Get the IP and RBL
		domain = worker.recv()

		# Check if this was a terminate, if so, exit the loop and terminate
		if domain == 'term':
			break

		ips = SPFFinder.getIPs(domain, settings)
		# At first, the script checked if the returned set of IPs is empty
		# Now we just return empty sets so we can check for any potential issues
		# if len(ips) > 0:
		prevResult = msgpack.packb([domain, ips])



def main():
	IPs = dict()
	# Get settings from configuration file
	settings = ConfigLoader.load(__file__, 'spf_whitelist.cf')

	# Prepare the dispatcher socket
	context = zmq.Context()
	dispatcher = context.socket(zmq.ROUTER)
	dispatcher.bind(settings['dispatcher'])

	# Start the worker processes
	processes = []
	for thread in xrange(settings['processes']):
		p = multiprocessing.Process(target=RBLworker, kwargs={'settings': settings})
		processes.append(p)
		p.start()

	# Send jobs to the active threads
	for domain in settings['spfDomains']:
		# LRU worker is next waiting in the queue
		address, empty, ready, prevResult = dispatcher.recv_multipart()

		# Send the task to the worker
		dispatcher.send_multipart([address, b'', domain])

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