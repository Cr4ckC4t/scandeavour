#!/usr/bin/env python3

# Import the plaintext results of masscan in the format of:
#
# Discovered open port 22/tcp on 127.0.0.1
# Discovered open port 80/tcp on 127.0.0.1

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

class MasscanPlainIngestor(BaseIngestor):
	def __init__(self):
		super().__init__(
			name = 'MasscanPlain',
			accepted_files = 'masscan.log'
		)

	def validate(self, file_path):
		# masscan plain output contains always the same line
		with open(file_path, 'rb') as f:
			line = f.readline()
			if line.startswith(b'Discovered open port '):
				self.file_path = file_path
				return True
		return False

	def parse(self):

		self.hosts = {}
		with open(self.file_path, 'rb') as f:
			for line in f:
				# parse output from
				# https://github.com/robertdavidgraham/masscan/blob/a31feaf5c943fc517752e23423ea130a92f0d473/src/output.c#L757

				result_line = line.decode()
				if not result_line.startswith('Discovered open port '):
					# ignore closed ports
					continue

				port = result_line.split('open port ')[1].split(' on ')[0]
				port_num = int(port.split('/')[0])
				port_prot = port.split('/')[1]

				if port_prot not in ['tcp', 'udp']:
					# let's ignore arp and icmp results for now
					# it could be added on request though
					continue

				host = result_line.split(' on ')[1]

				if host not in self.hosts.keys():
					self.hosts[host] = []

				self.hosts[host].append({
					'num': port_num,
					'prot': port_prot
				})

	def getDatabaseInterface(self):
		scan = {
			'tool': 'Masscan',
			'args': '', # not implemented by masscan
			'start': 0, # not included in default stdout
			'stop': 0, # not included in default stdout
			'version': '', # not implemented by masscan
			'hosts_up': len(self.hosts),
			'hosts_scanned': len(self.hosts), # not implemented by masscan
			'hosts': [{
				'ipv4': host if '.' in host else '',
				'ipv6': host if ':' in host else '',
				'mac': '', # not yet implemented here
				'names': [], # not implemented by masscan
				'reason': '', # not implemented by masscan
				'os_name': '', # not implemented by masscan
				'os_accuracy': 0, # not implemeneted by masscan
				'os_family': '', # not implemented by masscan
				'os_vendor': '', # not implemented by masscan
				'ports': [{
					'port': port['num'],
					'protocol': port['prot'],
					'svc_name': '', # not implemented
					'svc_info': '', # not implemented
					'svc_ssl': '', # not implemented
					'scripts': [] # not implemented
				} for port in self.hosts[host]],
			} for host in self.hosts]
		}
		return scan


	def __str__(self):
		str = ''
#		str += f'CMD: {self.cmdline}\n'
#		str += f'Scan started: {self.scanstart}\n'
#		str += f'Scan stopped: {self.scanstop}\n'
#		str += f'Masscan version: {self.msversion}\n'
		str += f'Identified hosts: {len(self.hosts)}\n'
		for host in self.hosts:
			str += f'====\n'
			str += f'\tAddr: {host}\n'
#			str += f'\tNames: '+ ', '.join(host['hostnames']) + '\n'
#			str += f'\tUp-Reason: {host["up_reason"]}\n'
#			str += f'\tOS name: {host["osname"]}\n'
#			str += f'\tOS accuracy: {host["accuracy"]}\n'
#			str += f'\tOS family: {host["osfamily"]}\n'
#			str += f'\tOS vendor: {host["vendor"]}\n'
			str += f'\tPorts:\n'
			for port in host[host]:
				str += f'\t\t{port["num"]:5}/{port["prot"]}\n'
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
		print(f'Usage: {sys.argv[0]} masscan_scan_output.log')
		sys.exit(1)

	inp = sys.argv[1]
	if not os.path.isfile(inp):
		print(f'{fc.red}[!]{fc.end} {inp} does not exist')
		sys.exit(1)

	ing = MasscanIngestor()
	if not ing.validate(inp):
		print(f'{fc.red}[!]{fc.end} Not a valid Masscan file')
		sys.exit(1)
	ing.parse()
	print(ing)
