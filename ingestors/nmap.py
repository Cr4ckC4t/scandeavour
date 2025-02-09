#!/usr/bin/env python3

from ingestor_base import BaseIngestor
import sys
import os
import xml.etree.ElementTree as ET

class fc:
	red = '\u001b[31m'
	green = '\u001b[32m'
	orange = '\u001b[33m'
	blue = '\u001b[34m'
	end = '\u001b[0m'

class NmapIngestor(BaseIngestor):
	def __init__(self):
		super().__init__(
			name = 'NmapXML',
			accepted_files = 'nmap.xml'
		)

	def validate(self, raw_file):
		# Other tools (like masscan) use nmap output format as well, so we double check that this XML really is an nmap result
		if b'</nmaprun>' in raw_file and b'<!-- Nmap' in raw_file and b'scanner="nmap"' in raw_file:
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

		nmaprunner = self.root.attrib
		self.cmdline = nmaprunner.get('args','') # optional
		self.scanstart = int(nmaprunner.get('start',0)) # unix timestamp - optional
		self.nmapversion = nmaprunner['version'] # mandatory

		runstats_finished = self.root.find('runstats/finished').attrib # mandatory
		self.scanstop = int(runstats_finished['time']) # unix timestamp - mandatory

		runstats_hosts = self.root.find('runstats/hosts').attrib # mandatory
		self.hosts_up = int(runstats_hosts['up']) # mandatory
		self.hosts_down = int(runstats_hosts['down']) # mandatory
		self.hosts_total = int(runstats_hosts['total']) # mandatory

		self.hosts = []
		xml_hosts = self.root.findall('host') # optional
		for xml_host in xml_hosts:
			host_status = xml_host.find('status').attrib # mandatory
			if host_status['state'] != 'up': # mandatory - up|down|unknown|skipped
				continue
			new_host = {}
			new_host['up_reason'] = host_status['reason'] # mandatory

			host_addrs = xml_host.findall('address') # mandatory - at least one

			addrs = []
			for host_addr in host_addrs:
				attribs = host_addr.attrib
				addrs.append({
					'type': attribs['addrtype'], # ipv4|ipv6|mac - mandatory
					'addr': attribs['addr'] # mandatory
				})
			new_host['addrs'] = addrs

			host_names = xml_host.findall('hostnames/hostname') # optional
			names = []
			for name in host_names:
				names.append(name.attrib.get('name','')) # optional

			new_host['hostnames'] = names

			xml_os = xml_host.find('os/osmatch') # optional
			if xml_os is not None:
				match = xml_os.attrib
				new_host['accuracy'] = int(match['accuracy']) # mandatory
				new_host['osname'] = match['name'] # mandatory
			else:
				new_host['accuracy'] = 0
				new_host['osname'] = ''

			osclass = xml_host.find('os/osmatch/osclass') # optional
			if xml_os is not None and osclass is not None:
				new_host['osfamily'] = osclass.attrib['osfamily'] # mandatory
				new_host['vendor'] = osclass.attrib['vendor'] # mandatory
			else:
				new_host['osfamily'] = ''
				new_host['vendor'] = ''

			# parse ports
			xml_ports = xml_host.findall('ports/port') # optional
			ports = []
			for xml_port in xml_ports:
				port = {}
				port_state = xml_port.find('state').attrib # mandatory
				# State can be one of:
				# open, filtered, unfiltered, closed, open|filtered, closed|filtered, unknown
				port['state'] = port_state['state'] # mandatory
				if port['state'] in ['filtered', 'closed', 'closed|filtered']:
					# ignore closed ports
					continue

				port['protocol'] = xml_port.attrib['protocol'] # mandatory - one of ip, udp, tcp, sctp
				port['number'] = int(xml_port.attrib['portid']) # mandatory

				xml_svc = xml_port.find('service') # optional
				xml_svc = xml_svc.attrib if (xml_svc is not None) else {}
				port['svc_name'] = xml_svc.get('name', '') # name
				port['svc_conf'] = int(xml_svc.get('conf', 0)) # confidence (value between 0 and 10)
				port['svc_product'] = xml_svc.get('product', '') # product
				port['svc_version'] = xml_svc.get('version', '') # version
				port['svc_extrainfo'] = xml_svc.get('extrainfo', '') # additional information
				port['svc_tunnel'] = xml_svc.get('tunnel', '') # optional - if set, then set to "ssl"
				port['svc_proto'] = xml_svc.get('proto', '') # optional - if set, then set to "rpc"

				xml_port_scripts = xml_port.findall('script') # optional
				port_scripts = []
				for xml_port_script in xml_port_scripts:
					port_scripts.append({
						'id': xml_port_script.get('id'), # mandatory
						'output': xml_port_script.get('output').strip('\n'), # mandatory
					})
				port['scripts'] = port_scripts

				ports.append(port)

			new_host['ports'] = ports

			self.hosts.append(new_host)

	# Assume that every host can only have one IPv4, IPv6 and MAC
	def getAddrByType(self, addrs, type):
		for addr in addrs:
			if addr['type'] == type:
				return addr['addr']
		return ''

	def getDatabaseInterface(self):
		scan = {
			'tool': 'Nmap',
			'args': self.cmdline,
			'start': self.scanstart,
			'stop': self.scanstop,
			'version': self.nmapversion,
			'hosts_up': self.hosts_up,
			'hosts_scanned': self.hosts_total,
			'hosts': [{
				'ipv4': self.getAddrByType(host['addrs'], 'ipv4'),
				'ipv6': self.getAddrByType(host['addrs'], 'ipv6'),
				'mac': self.getAddrByType(host['addrs'], 'mac'),
				'names': host['hostnames'], # array of names
				'reason': host['up_reason'],
				'os_name': host['osname'],
				'os_accuracy': host['accuracy'],
				'os_family': host['osfamily'],
				'os_vendor': host['vendor'],
				'ports': [{
					'port': port['number'],
					'protocol': port['protocol'],
					'svc_name': port['svc_name'],
					'svc_info': f'{port["svc_product"]} {port["svc_version"]} {port["svc_extrainfo"]}'.strip(),
					'svc_ssl': port['svc_tunnel'],
					'scripts': port['scripts']
				} for port in host["ports"]],
			} for host in self.hosts]
		}
		return scan


	def __str__(self):
		str = ''
		str += f'CMD: {self.cmdline}\n'
		str += f'Scan started: {self.scanstart}\n'
		str += f'Scan stopped: {self.scanstop}\n'
		str += f'Nmap version: {self.nmapversion}\n'
		str += f'Scanned hosts: {self.hosts_up} up, {self.hosts_down} down, {self.hosts_total} total\n'
		for host in self.hosts:
			str += f'====\n'
			str += f'\tAddrs: '+ ', '.join(((a['addr']+" ("+a['type']+")") for a in host['addrs'])) + '\n'
			str += f'\tNames: '+ ', '.join(host['hostnames']) + '\n'
			str += f'\tUp-Reason: {host["up_reason"]}\n'
			str += f'\tOS name: {host["osname"]}\n'
			str += f'\tOS accuracy: {host["accuracy"]}\n'
			str += f'\tOS family: {host["osfamily"]}\n'
			str += f'\tOS vendor: {host["vendor"]}\n'
			str += f'\tPorts:\n'
			for port in host['ports']:
				str += f'\t\t{port["number"]:5}/{port["protocol"]} '
				str += f'{port["svc_name"]} ({port["svc_conf"]}|10) '
				str += f'{port["svc_product"]} '
				str += f'{port["svc_version"]} '
				str += f'{port["svc_extrainfo"]} '
				str += f'{port["svc_tunnel"]} '
				str += f'{port["svc_proto"]}\n'
				for script in port['scripts']:
					str += f'{script["id"]}: {script["output"]}\n'
		return str

# Standalone version
# Requires a copy of ingestor_base.py in the same directory
if __name__ == '__main__':
	if len(sys.argv) != 2:
		print(f'Usage: {sys.argv[0]} nmap_scan_output.xml')
		sys.exit(1)

	inp = sys.argv[1]
	if not os.path.isfile(inp):
		print(f'{fc.red}[!]{fc.end} {inp} does not exist')
		sys.exit(1)

	with open(inp, 'rb') as f:
		scan = f.read()

	ing = NmapIngestor()
	if not ing.validate(scan):
		print(f'{fc.red}[!]{fc.end} Not a valid Nmap file')
		sys.exit(1)
	ing.parse()
	print(ing)
