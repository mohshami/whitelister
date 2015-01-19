__author__ = 'Mohammad Al-Shami'

import dns.resolver

class SPFFinder:
	@classmethod
	def getIPs(self, domain, settings):
		retVal = []

		# Go through all SPF records of this domain
		for record in self.getSPFRecord(domain, settings):
			# Split each record into parts
			segments = record.split(' ')

			for segment in segments:
				# Some domains have multiple spaces between their segments, this results in empty segments
				# Just skip them
				if segment == '':
					continue

				# Get each part of the segment 'ip4' and ip
				parts = segment.split(':', 1)

				# Ignore records starting with these
				if parts[0][0] in ['-', '?', '~']:
					continue

				# If we have a + at the beginning, just remove it
				if parts[0][0] == '+':
					parts[0] = parts[0][1:]

				# Some segments can be directly processed
				# Accept invalid values like ipv4 and ipv6
				if len(parts) == 2 and parts[0] in ['ip4', 'ip6', 'ipv4', 'ipv6']:
					retVal.append(parts[1])
				# Get the IPs for mx and a segments
				elif parts[0] in ['a', 'mx']:
					host = domain
					if len(parts) == 2:
						host = parts[1]
					retVal.extend(self.getRecord(host, parts[0], settings))
				# If this was a redirect or an include,
				# just get the IPs for that SPF record and add them to the current ones
				elif parts[0] in ['include', 'redirect']:
					IPs = self.getIPs(parts[1], settings)
					retVal.extend(IPs)

		# Only return unique values
		return sorted(set(retVal))


	@classmethod
	def getSPFRecord(self, domain, settings):
		retVal = []

		# Prepare DNS resolver
		resolver = dns.resolver.Resolver()
		resolver.nameservers = settings['nameServers']

		# Find any SPF records
		try:
			# Get all TXT records for the domain
			answers = resolver.query(domain, 'TXT')

			# Go through all records
			for answer in answers:
				# DNS queries are returned as objects, the the string equivalent
				# and remove any quotation marks
				# Also replace = with : to make parsing easier
				answer = str(answer).replace('"', '').replace('=', ':')

				# The returned record is not SPF, it's something else
				if not "spf2.0" in answer and not "v:spf1" in answer and not answer is None:
					continue

				retVal.append(answer)
		except:
			return ""

		return retVal


	@classmethod
	def getRecord(self, record, type, settings):
		retVal = []
		type = type.lower()

		# Prepare DNS resolver
		resolver = dns.resolver.Resolver()
		resolver.nameservers = settings['nameServers']

		# Find any records
		try:
			answers = resolver.query(record, type)

			# Go through all records
			for answer in answers:
				# If the request record was of type a, just return it,
				if type == 'a':
					answer = str(answer)

					retVal.append(answer)
				# If the request record was of type mx, resolve it
				else:
					answer = self.getRecord(str(answer.exchange), 'a', settings)

					retVal.extend(answer)
		except:
			return ""

		return retVal