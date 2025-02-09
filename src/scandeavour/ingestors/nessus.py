#!/usr/bin/env python3

from scandeavour.ingestor_base import BaseIngestor
import sys
import os
import xml.etree.ElementTree as ET
import html
import re

class fc:
	red = '\u001b[31m'
	green = '\u001b[32m'
	orange = '\u001b[33m'
	blue = '\u001b[34m'
	end = '\u001b[0m'

class NessusIngestor(BaseIngestor):
	def __init__(self):
		super().__init__(
			name='Nessus Export',
			accepted_files='export.nessus'
		)

	def validate(self, raw_file):
		if b'</NessusClientData_v2>' in raw_file:
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

		nessusreport = self.root.find('Report')

		report_details = self.root.find('.//ReportItem[@pluginID="19506"]/plugin_output')
		# not every report contains this plugin (depends on the scan configuration)
		if report_details is not None:
			report_details = report_details.text
			self.nessusversion = re.search('Nessus version : (?P<version>.+)\n', report_details).group('version')
			self.args = '(Nessus scan name) ' + re.search('Scan name : (?P<name>.+)\n', report_details).group('name')
		else:
			self.nessusversion = ''
			self.args = ''

		self.scan_start = 0
		self.scan_stop = 0

		self.hosts = []
		for xml_host in nessusreport.findall('ReportHost'):

			# host-ip can be ipv6 or ipv4
			tag_ip = xml_host.find('.//tag[@name="host-ip"]')
			ipv4 = ''
			ipv6 = ''
			if tag_ip is not None:
				if '.' in tag_ip.text:
					ipv4 = tag_ip.text
				elif ':' in tag_ip.text:
					ipv6 = tag_ip.text

			# sanity check
			if ipv4 == '' and ipv6 == '':
				print(f'{fc.red}[!]{fc.end} (Nessus Ingestor) host is missing IPv4 and IPv6 - skipping this host')
				continue

			# store hostname
			# currently this ingestor only parses one host-fqdn
			# Nessus also appears to have "host-fqdns" in some cases, which is an array, but I don't have enough test files to implement that properly
			tag_hostname = xml_host.find('.//tag[@name="host-fqdn"]')
			hostnames = []
			if tag_hostname is not None:
				hostnames = [tag_hostname.text]

			# if it exists, add the netbiosname to the hostname
			tag_netbiosname = xml_host.find('.//tag[@name="netbios-name"]')
			if tag_netbiosname is not None:
				hostnames.append(tag_netbiosname.text)

			# store OS name, when reported
			tag_osname = xml_host.find('.//tag[@name="operating-system"]')
			osname = ''
			osconf = 0
			if tag_osname is not None:
				# before adding it, check if a confidence is available
				tag_osconf = xml_host.find('.//tag[@name="operating-system-conf"]')
				if tag_osconf is not None:
					osname = tag_osname.text
					osconf = int(tag_osconf.text) # we hope that this will roughly compare to Nmap (Nmap uses "accuracy" with values between 0 and 100)

			# use host information to update the scan start and stop time
			tag_start = xml_host.find('.//tag[@name="HOST_START_TIMESTAMP"]')
			if tag_start is not None:
				tag_start = int(tag_start.text)
				self.scan_start = tag_start if tag_start < self.scan_start or self.scan_start == 0 else self.scan_start
			tag_stop = xml_host.find('.//tag[@name="HOST_END_TIMESTAMP"]')
			if tag_stop is not None:
				tag_stop = int(tag_stop.text)
				self.scan_stop = tag_stop if tag_stop < self.scan_stop or self.scan_stop == 0 else self.scan_stop

			# list of port objects
			ports = {}
			for report_item in xml_host.findall('ReportItem'):
				xml_port = report_item.attrib
				port_number = int(xml_port.get('port'))
				if port_number == 0:
					continue

				port_protocol = xml_port.get('protocol')
				# Don't rely on Nessus to provide an accurate service name in the svc_name attribute. Usually its something generic like "netbios-ns?"
				# port['svc_name'] = xml_port.get('svc_name', '')

				# Nessus plugins are more interesting though
				script_id = xml_port.get('pluginName')
				plugin_family = xml_port.get('pluginFamily')

				# Nessus generates a lot of output, we focus on these two
				synopsis = report_item.find('synopsis').text # probably mandatory
				plugin_output = report_item.find('plugin_output') # not mandatory

				if (port_id:=f'{port_number}/{port_protocol}') not in ports.keys():
					# store each port with a unique key for the current host
					ports[port_id] = {
						'number': port_number,
						'protocol': port_protocol,
						'scripts': []
					}

				# Only store plugins as "script results" if it is not the port scan plugin itself
				if plugin_family != 'Port scanners':
					output = html.unescape(plugin_output.text) if plugin_output is not None else synopsis
					output = output[:2000]+'... [Content clipped for brevity. See original Nessus result for full plugin output.]' if len(output) > 2000 else output
					ports[port_id]['scripts'].append({
						'id': script_id,
						'output': output
					})

			self.hosts.append({
				'ipv4': ipv4,
				'ipv6': ipv6,
				'ports': [p for p in ports.values()],
				'hostnames': hostnames,
				'osname': osname,
				'osconf': osconf
			})


	def getDatabaseInterface(self):
		scan = {
			'tool': 'Nessus',
			'args': self.args,
			'start': self.scan_start,
			'stop': self.scan_stop,
			'version': self.nessusversion,
			'hosts_up': len(self.hosts),
			'hosts_scanned': len(self.hosts), # not implemented, since there is no easy way of getting this information
			'hosts': [{
				'ipv4': host['ipv4'],
				'ipv6': host['ipv6'],
				'mac': '', # not implemented
				'names': host['hostnames'],
				'reason': '', # not implemented
				'os_name': host['osname'],
				'os_accuracy': host['osconf'],
				'os_family': '', # not implemented
				'os_vendor': '', # not implemented
				'ports': [{
					'port': port['number'],
					'protocol': port['protocol'],
					'svc_name': '', # not implemented
					'svc_info': '', # not implemented
					'svc_ssl': '', # not implemented
					'scripts': port['scripts']
				} for port in host["ports"]],
			} for host in self.hosts]
		}
		return scan


	def __str__(self):
		str = ''
		str += f'CMD: {self.args}\n'
		str += f'Scan started: {self.scan_start}\n'
		str += f'Scan stopped: {self.scan_stop}\n'
		str += f'Nessus version: {self.nessusversion}\n'
		str += f'Scanned hosts ({len(self.hosts)}):\n'
		for host in self.hosts:
			str += f'====\n'
			str += f'\tIPv4: {host["ipv4"]}\n'
			str += f'\tIPv6: {host["ipv6"]}\n'
#			str += f'\tMAC: {host["mac"]}'
			str += f'\tNames: '+ ', '.join(host['hostnames']) + '\n'
#			str += f'\tUp-Reason: {host["up_reason"]}\n'
			str += f'\tOS name: {host["osname"]}\n'
			str += f'\tOS accuracy: {host["osconf"]}\n'
#			str += f'\tOS family: {host["osfamily"]}\n'
#			str += f'\tOS vendor: {host["vendor"]}\n'
			str += f'\tPorts:\n'
			for port in host['ports']:
				str += f'\t\t{port["number"]:5}/{port["protocol"]} \n'
#				str += f'{port["svc_name"]}'
#				str += f'{port["svc_product"]} '
#				str += f'{port["svc_version"]} '
#				str += f'{port["svc_extrainfo"]} '
#				str += f'{port["svc_tunnel"]} '
#				str += f'{port["svc_proto"]}\n'
				for script in port['scripts']:
					str += f'{script["id"]}: {script["output"]}\n'
		return str

# Standalone version
# Requires a copy of ingestor_base.py in the same directory
if __name__ == '__main__':
	if len(sys.argv) != 2:
		print(f'Usage: {sys.argv[0]} nessus_export.xml')
		sys.exit(1)

	inp = sys.argv[1]
	if not os.path.isfile(inp):
		print(f'{fc.red}[!]{fc.end} {inp} does not exist')
		sys.exit(1)

	with open(inp, 'rb') as f:
		scan = f.read()

	ing = NessusIngestor()
	if not ing.validate(scan):
		print(f'{fc.red}[!]{fc.end} Not a valid Nessus file')
		sys.exit(1)
	ing.parse()
	print(ing)
