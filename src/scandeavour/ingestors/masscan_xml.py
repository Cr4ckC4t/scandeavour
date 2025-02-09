#!/usr/bin/env python3

# Based on the sourcecode from masscan/src/out-xml.c.
# The current masscan XML output is flawed (for example "hosts up" shows the port number not host number) and may change in the future.
# So when things start to break, look at the changes made to out-xml.c in masscan.

from scandeavour.ingestor_base import BaseIngestor
import sys
import os
import xml.etree.ElementTree as ET

class fc:
	red = '\u001b[31m'
	green = '\u001b[32m'
	orange = '\u001b[33m'
	blue = '\u001b[34m'
	end = '\u001b[0m'

class MasscanXMLIngestor(BaseIngestor):
	def __init__(self):
		super().__init__(
			name = 'MasscanXML',
			accepted_files = 'masscan.xml'
		)

	def validate(self, raw_file):
		# masscan XML uses a format similar to Nmap
		if b'</nmaprun>' in raw_file and b'<!-- masscan' in raw_file and b'scanner="masscan"' in raw_file:
			self.raw_file = raw_file
			return True
		return False

	def parse(self):
		self.root = None
		try:
			self.root = ET.fromstring(self.raw_file.decode('utf8'))
		except Exception as e:
			print(f'{fc.red}[!]{fc.end} Parsing failed with: {e}')
			sys.exit(1)

		msrunner = self.root.attrib
		self.scanstart = int(msrunner.get('start',0)) # unix timestamp
		# can't use the version because it is hardcoded in out-xml.c and not updated since the beta release
		#self.msversion = msrunner['version']

		runstats_finished = self.root.find('runstats/finished').attrib # mandatory
		self.scanstop = int(runstats_finished['time']) # unix timestamp - mandatory

		# can't use the runstats as they currently count open ports not the hosts
		#runstats_hosts = self.root.find('runstats/hosts').attrib # mandatory
		#self.hosts_up = int(runstats_hosts['up']) # mandatory
		#self.hosts_total = int(runstats_hosts['total']) # mandatory

		self.hosts = {}
		xml_hosts = self.root.findall('host') # optional
		for xml_host in xml_hosts:

			# can't rely on the addrtype for the current masscan release, see https://github.com/robertdavidgraham/masscan/issues/807
			host_addr = xml_host.find('address').attrib.get('addr') # masscan only shows one addr

			if host_addr not in self.hosts.keys():
				self.hosts[host_addr] = {
					'ipv6': '',
					'ipv4': '',
					'ports': []
				}

			if ':' in host_addr:
				self.hosts[host_addr]['ipv6'] = host_addr
			else:
				self.hosts[host_addr]['ipv4'] = host_addr

			# currently, masscan XML shows one port per host, so a host with multiple ports will actually show up separately for every open port
			xml_port = xml_host.find('ports/port') # mandatory
			port_state = xml_port.find('state').attrib.get('state') # mandatory

			port_protocol = xml_port.attrib['protocol'] # mandatory
			port_number = int(xml_port.attrib['portid']) # mandatory

			if 'open' in port_state:
				# I assume that, like nmap, masscan will show a port only once for every host
				self.hosts[host_addr]['ports'].append({
					'number': port_number,
					'protocol': port_protocol
				})
			else:
				print(f'{fc.red}[!]{fc.end} Masscan identified {host_addr} - {port_number}/{port_protocol}. Host added but port skipped due to state: {port_state}')
				continue

	def getDatabaseInterface(self):
		scan = {
			'tool': 'Masscan',
			'args': '', # not implemented by masscan
			'start': self.scanstart,
			'stop': self.scanstop,
			'version': '', # not implemented by masscan
			'hosts_up': len(self.hosts),
			'hosts_scanned': len(self.hosts), # not implemented by masscan
			'hosts': [{
				'ipv4': host['ipv4'],
				'ipv6': host['ipv6'],
				'mac': '', # not implemented by masscan
				'names': [], # not implemented by masscan
				'reason': '', # not implemented by masscan
				'os_name': '', # not implemented by masscan
				'os_accuracy': 0, # not implemeneted by masscan
				'os_family': '', # not implemented by masscan
				'os_vendor': '', # not implemented by masscan
				'ports': [{
					'port': port['number'],
					'protocol': port['protocol'],
					'svc_name': '', # not implemented
					'svc_info': '', # not implemented
					'svc_ssl': '', # not implemented
					'scripts': [] # not implemented
				} for port in host["ports"]],
			} for host in self.hosts.values()]
		}
		return scan


	def __str__(self):
		str = ''
#		str += f'CMD: {self.cmdline}\n'
		str += f'Scan started: {self.scanstart}\n'
		str += f'Scan stopped: {self.scanstop}\n'
#		str += f'Masscan version: {self.msversion}\n'
		str += f'Scanned hosts: {len(self.hosts)}\n'
		for host in self.hosts:
			str += f'====\n'
			str += f'\tAddr: v4: '+host['ipv4']+', v6: '+host['ipv6']+'\n'
#			str += f'\tNames: '+ ', '.join(host['hostnames']) + '\n'
#			str += f'\tUp-Reason: {host["up_reason"]}\n'
#			str += f'\tOS name: {host["osname"]}\n'
#			str += f'\tOS accuracy: {host["accuracy"]}\n'
#			str += f'\tOS family: {host["osfamily"]}\n'
#			str += f'\tOS vendor: {host["vendor"]}\n'
			str += f'\tPorts:\n'
			for port in host['ports']:
				str += f'\t\t{port["number"]:5}/{port["protocol"]}\n'
#				str += f'{port["svc_name"]} ({port["svc_conf"]}|10) '
#				str += f'{port["svc_product"]} '
#				str += f'{port["svc_version"]} '
#				str += f'{port["svc_extrainfo"]} '
#				str += f'{port["svc_tunnel"]} '
#				str += f'{port["svc_proto"]}\n'
#				for script in port['scripts']:
#					str += f'{script["id"]}: {script["output"]}\n'
		return str

# Standalone version
# Requires a copy of ingestor_base.py in the same directory
if __name__ == '__main__':
	if len(sys.argv) != 2:
		print(f'Usage: {sys.argv[0]} masscan_scan_output.xml')
		sys.exit(1)

	inp = sys.argv[1]
	if not os.path.isfile(inp):
		print(f'{fc.red}[!]{fc.end} {inp} does not exist')
		sys.exit(1)

	with open(inp, 'rb') as f:
		scan = f.read()

	ing = MasscanIngestor()
	if not ing.validate(scan):
		print(f'{fc.red}[!]{fc.end} Not a valid Masscan file')
		sys.exit(1)
	ing.parse()
	print(ing)
