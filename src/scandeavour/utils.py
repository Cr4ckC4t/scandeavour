import sqlite3
import re
from os import path,getenv

def getOS(family, name):
	name=name.lower()
	family=family.lower()

	# this logic must compensate for different formats coming from different scans
	# nmap and Nessus for example differ

	os = ''
	# when family is given
	if family in ['windows', 'openbsd', 'freebsd', 'solaris', 'linux']:
		os = family
	# nmap results for apple
	elif 'mac os' in family or 'apple' in name:
		os = 'apple'

	# when family is not given or name is even more specific
	if 'ubuntu' in name:
		os = 'ubuntu'
	elif 'red hat' in name:
		os = 'redhat'
	elif 'windows' in name:
		os = 'windows'
	elif 'linux' in name:
		os = 'linux'

	return os

def getDB(autocommit=False):
	db_con = sqlite3.connect(getenv('SQLITE_PROJECT_FILE'), autocommit=autocommit)
	db = db_con.cursor()
	return (db_con, db)

def initDB():
	print(f'[+] Warming up the database engine')
	db_con, db = getDB(autocommit=True)

	qr = db.execute('SELECT name FROM sqlite_master WHERE name="_setup_"')
	if qr.fetchone() is None:
		# First setup
		setup_script = ''
		with open(path.join(path.dirname(path.abspath(__file__)),'setup_database.sqlite'), 'r') as f:
			setup_script = f.read()
		db.executescript(setup_script)

	db_con.close()
	print(f'[+] Database ready')

class NodeHistory:
	def __init__(self, data):
		self.history = data['history']
		self.index = data['index']
		self.max_history = 5
		self.jumptable = data['jumptable']

	def add_node(self, node):
		self.history.append(node)
		self.history = self.history[-self.max_history:]
		self.index = len(self.history)-1

	# Use this after jumps from origins other than the latest history item
	def re_add_current(self):
		self.add_node(self.history[self.index])

	def nav_previous(self):
		if self.prev_enabled():
			self.index -= 1
			return self.history[self.index]
		return None

	def nav_next(self):
		if self.next_enabled():
			self.index += 1
			return self.history[self.index]
		return None

	def prev_enabled(self):
		return len(self.history) > 1 and self.index > 0

	def next_enabled(self):
		return len(self.history) > 1 and self.index < (len(self.history)-1)

	def get(self):
		return {'history': self.history, 'index': self.index, 'jumptable': self.jumptable}

	# Jumps work like this:
	# You add a jump target to the Node History
	# A target needs a simple id (can be any) and a node object
	# Example:
	#	add_jump('Target-1', {'id': 'node-id', 'label': 'node-label'})
	# After setting up the jump target you can place a jump button
	# with an id like this:
	# id={'id': 'btn-node-jump', 'index': 'Target-1'}
	# We then use callback matching (ALL) to react on th button click
	# On button click, we read the index and use jump_to to retrieve
	# the node data, basically simulating a click on the graph node
	# The history is preserved between callbacks via a state
	def add_jump(self, id, node):
		self.jumptable[id]=node

	def jump_to(self, id):
		return self.jumptable[id]

def validateIP(ip):
	# matches any valid IP with an optional CIDR mask
	# do not allow CIDR range 32, because that would be a single ip
	# do not allow CIDR range 0, because that would be every host (no filter)
	# do allow CIDR range 31
	return re.match(r'^([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])(\.([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])){3}($|\/([1-9]|[1-2][0-9]|3[0-1])$)', ip)

def IPtoNum(ip):
	if ip == '':
		return -1
	return sum([int(v)<<(8*(3-i)) for i,v in enumerate(ip.split('.'))])

def NumToIP(num):
	if num < 0:
		return ''
	return '.'.join([str(num>>(24)&0xFF), str(num>>(16)&0xFF), str(num>>8&0xFF), str(num&0xFF)])

def CIDRtoFirstLast(cidr):
	ip,subnet = cidr.split('/')
	first = IPtoNum(ip) & int('1'*int(subnet)+'0'*(32-int(subnet)),2)
	last = first + int('1'*(32-int(subnet)),2)
	return (first, last)

def getHostLabel(ipv4, ipv6, mac, names):
	# Start by assigning the least important value and add the better ones if they are available
	# ipv6 should be the least desired option simply because it's hard to digest
	label = ipv6
	if len(mac) > 0:
		label = mac
	if len(ipv4) > 0:
		label = ipv4
	if len(names):
		# Just use the first one - there is no easy way to figure out which one is the best
		label = names[0]
	return label

class DataFilterMap:
	# Each field can have several match methods
	# Each match method contains the query string which it will generate.
	#
	# query is the actual database query
	# patterns are used for client_side validation of the input (as a hint for the user)
	# placeholder will be displayed in the filter field as an example
	# get_input_value is used to transform the input string to the required type for the query (must return the value(s) as tuple)
	#
	# Avoid aggregations. They can not easily be integrated with this setup.
	# They would require "HAVING"-clauses in different parts of the query.
	# Use the table sort function instead.

	_str_placeholder = '<str>'
	_get_str = lambda i: (i,)

	_str_or_empty_placeholder = '<str>|"empty"'
	_get_str_or_empty = lambda i: (i,) if i!='empty' else ('',)

	_int_placeholder = '<int>'
	_timestamp_placeholder = _int_placeholder + ' [epoch]'
	_bytes_placeholder = _int_placeholder + ' [bytes]'
	_get_int = lambda i: (int(i),)


	fields = {
		# Currenty these handles are available to match values in the query (see further below for the actual query):
		# h	- hosts
		# hn	- hostnames
		# p	- ports
		# p	- pscripts (AS script_name and script_output)
		# s	- scans
		# sf	- input_files
		'scan.tool': {
			'is': { 'query': 's.tool=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'is not': { 'query': 's.tool!=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'contains': { 'query': 's.tool LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 's.tool NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'scan.filename': {
			'is': { 'query': 'sf.filename=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'is not': { 'query': 'sf.filename!=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'contains': { 'query': 'sf.filename LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 'sf.filename NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'scan.ingested': {
			'before': { 'query': 'sf.ingestDate < ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_timestamp_placeholder},
			'after': { 'query': 'sf.ingestDate > ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_timestamp_placeholder},
		},
		'scan.filesize': {
			'greater than': { 'query': 'sf.filesize > ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_bytes_placeholder},
			'smaller than': { 'query': 'sf.filesize < ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_bytes_placeholder},
		},
		'scan.args': {
			'is': { 'query': 's.args=?', 'get_input_value':_get_str_or_empty, 'pattern':'.*', 'placeholder':_str_or_empty_placeholder},
			'is not': { 'query': 's.args!=?', 'get_input_value':_get_str_or_empty, 'pattern':'.*', 'placeholder':_str_or_empty_placeholder},
			'contains': { 'query': 's.args LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 's.args NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'scan.start': {
			'before': { 'query': 's.start < ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_timestamp_placeholder},
			'after': { 'query': 's.start > ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_timestamp_placeholder},
		},
		'scan.stop': {
			'before': { 'query': 's.stop < ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_timestamp_placeholder},
			'after': { 'query': 's.stop > ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_timestamp_placeholder},
		},
		'host.ipv4': {
			'is': { 'query': 'COALESCE(h.ipv4,-1)=?', 'get_input_value':(lambda i:(IPtoNum(i),) if i!='empty' else (-1,)), 'pattern':r'^(empty|([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])(\.([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])){3})$', 'placeholder':'<IPv4>|"empty"'},
			'in subnet': { 'query': 'h.ipv4 BETWEEN ? AND ?', 'get_input_value':(lambda i:CIDRtoFirstLast(i)), 'pattern':r'^([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])(\.([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])){3}\/([1-9]|[1-2][0-9]|3[0-2])$', 'placeholder':'<CIDR>'},
			'is not': { 'query': 'COALESCE(h.ipv4,-1)!=?', 'get_input_value':(lambda i:(IPtoNum(i),) if i!='empty' else (-1,)), 'pattern':r'^(empty|([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])(\.([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])){3})$', 'placeholder':'<IPv4>|"empty"'},
			'not in subnet': { 'query': 'h.ipv4 NOT BETWEEN ? AND ?', 'get_input_value':(lambda i:CIDRtoFirstLast(i)), 'pattern':r'^([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])(\.([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])){3}\/([1-9]|[1-2][0-9]|3[0-2])$', 'placeholder':'<CIDR>'},
		},
		'host.ipv6': {
			'is': { 'query': 'COALESCE(h.ipv6,"")=?', 'get_input_value':_get_str_or_empty, 'pattern':'^(empty|[:0-9a-fA-F]*)$', 'placeholder':_str_or_empty_placeholder},
			'is not': { 'query': 'COALESCE(h.ipv6,"")!=?', 'get_input_value':_get_str_or_empty, 'pattern':'^(empty|[:0-9a-fA-F]*)$', 'placeholder':_str_or_empty_placeholder},
			'contains': { 'query': 'h.ipv6 LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'[:0-9a-fA-F]*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 'h.ipv6 NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'[:0-9a-fA-F]*', 'placeholder':_str_placeholder},
		},
		'host.mac': {
			'is': { 'query': 'COALESCE(h.mac,"")=?', 'get_input_value':_get_str_or_empty, 'pattern':'^(empty|[:0-9a-fA-F]*)$', 'placeholder':_str_or_empty_placeholder},
			'is not': { 'query': 'COALESCE(h.mac,"")!=?', 'get_input_value':_get_str_or_empty, 'pattern':'^(empty|[:0-9a-fA-F]*)$', 'placeholder':_str_or_empty_placeholder},
			'starts with': { 'query': 'h.mac LIKE ? || "%"', 'get_input_value':_get_str, 'pattern':'[:0-9a-fA-F]*', 'placeholder':_str_placeholder},
			'contains': { 'query': 'h.mac LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'[:0-9a-fA-F]*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 'h.mac NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'[:0-9a-fA-F]*', 'placeholder':_str_placeholder},
		},
		'host.os': {
			'contains': { 'query': '(h.os_name ||" "|| h.os_family ||" "|| h.os_vendor) LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': '(h.os_name ||" "|| h.os_family ||" "|| h.os_vendor) NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'host.os_accuracy': {
			'is': { 'query': 'h.os_accuracy=?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'is not': { 'query': 'h.os_accuracy!=?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'greater than': { 'query': 'h.os_accuracy > ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'smaller than': { 'query': 'h.os_accuracy < ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
		},
		'host.name': {
			'is': { 'query': 'hn.name=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'is not': { 'query': 'hn.name!=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'starts with': { 'query': 'hn.name LIKE ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'ends with': { 'query': 'hn.name LIKE "%" || ?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'starts not with': { 'query': 'hn.name NOT LIKE ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'ends not with': { 'query': 'hn.name NOT LIKE "%" || ?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'contains': { 'query': 'hn.name LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 'hn.name NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'host.tag': {
			'is': { 'query': 'h.tag=?', 'get_input_value':_get_str_or_empty, 'pattern':'.*', 'placeholder':_str_or_empty_placeholder},
			'is not': { 'query': 'h.tag!=?', 'get_input_value':_get_str_or_empty, 'pattern':'.*', 'placeholder':_str_or_empty_placeholder},
			'contains': { 'query': 'h.tag LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 'h.tag NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'host.portcount': {
			'is': { 'query': 'h.port_cnt=?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'is not': { 'query': 'h.port_cnt!=?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'greater than': { 'query': 'h.port_cnt > ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'smaller than': { 'query': 'h.port_cnt < ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
		},
		'host.reason': {
			'is': { 'query': 'h.reason=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'is not': { 'query': 'h.reason!=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'contains': { 'query': 'h.reason LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 'h.reason NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'host.scriptcount': {
			'is': { 'query': 'h.script_cnt=?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'is not': { 'query': 'h.script_cnt!=?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'greater than': { 'query': 'h.script_cnt > ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'smaller than': { 'query': 'h.script_cnt < ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
		},
		'port.number': {
			'is': { 'query': 'p.port=?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'is not': { 'query': 'p.port!=?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'greater than': { 'query': 'p.port > ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
			'smaller than': { 'query': 'p.port < ?', 'get_input_value':_get_int, 'pattern':'[0-9]*', 'placeholder':_int_placeholder},
		},
		'port.protocol': {
			'is': { 'query': 'p.protocol=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'is not': { 'query': 'p.protocol!=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'port.string': {
			'is': { 'query': '(p.port||"/"||p.protocol)=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'is not': { 'query': '(p.port||"/"||p.protocol)!=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'port.service': {
			'contains': { 'query': '(p.svc_name||" "||p.svc_info) LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': '(p.svc_name||" "||p.svc_info) NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'script.name': {
			'is': { 'query': 'p.script_name=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'is not': { 'query': 'p.script_name!=?', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'contains': { 'query': 'p.script_name LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 'p.script_name NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
		'script.output': {
			'contains': { 'query': 'p.script_output LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
			'does not contain': { 'query': 'p.script_output NOT LIKE "%" || ? || "%"', 'get_input_value':_get_str, 'pattern':'.*', 'placeholder':_str_placeholder},
		},
	}

	# We use COUNT(t.port) instead of port_cnt because we want to
	# count the resulting ports (matching a query like protocol=tcp).
	# The host detail page will show the full range of open ports.
	data_query_one = '''
SELECT
	y.hid,
	y.os_name,
	y.os_family,
	y.label,
	y.ipv4,
	y.ipv6,
	y.mac,
	y.hns,
	group_concat(y.port||'/'||y.protocol, ", ") AS port,
	group_concat(y.tools) AS tools,
	y.tag,
	group_concat(y.sids) AS sids,
	group_concat(DISTINCT y.pid) AS pids
FROM (
	SELECT
		x.hid,
		x.os_name,
		x.os_family,
		x.label,
		x.ipv4,
		x.ipv6,
		x.mac,
		x.tag,
		x.hns,
		x.port,
		x.protocol,
		group_concat(x.tool) AS tools,
		group_concat(x.sid) AS sids,
		x.pid
	FROM ( SELECT
			h.hid,
			h.os_name,
			h.os_family,
			h.label,
			h.ipv4,
			h.ipv6,
			h.mac,
			h.tag,
			group_concat(DISTINCT hn.name) as hns,
			p.port,
			p.protocol,
			s.tool,
			s.sid,
			p.pid
		FROM hosts h
		LEFT JOIN hostnames hn ON (hn.host = h.hid)
		INNER JOIN scans_hosts sh ON (sh.host = h.hid)
		INNER JOIN scans s ON (s.sid = sh.scan)
		INNER JOIN input_files sf ON (sf.fid = s.file)
		LEFT JOIN (
			SELECT
				sp.port AS pid,
				sp.scan AS sid,
				p.host AS hid,
				p.port,
				p.protocol,
				p.svc_name,
				p.svc_info,
				p.svc_ssl,
				ps.name AS script_name,
				ps.output AS script_output
			FROM scans_ports sp INNER JOIN ports p ON (sp.port = p.pid) LEFT JOIN pscripts ps ON (ps.scan = sp.scan AND ps.port=p.pid)
		) AS p ON p.sid = s.sid AND p.hid = h.hid
'''
	# Filters will end up between part one and two
	data_query_two = '''
		GROUP BY h.hid, p.pid, s.sid
	) x GROUP BY x.hid, x.pid
) y GROUP BY y.hid
'''

	def buildSQLQuery(self, inp_filters):

		filter_added=False

		query_filter = 'WHERE'

		query_params = tuple()
		try:
			last_group_index=len(inp_filters)-1
			for group_index in range(len(inp_filters)):
				group = inp_filters[group_index]
				last_filter_index = len(group)-1

				if group_index == 0:
					# surrounding everything
					query_filter += ' ( '

				# For every but the first group, add group operator
				if group_index != 0:
					query_filter += group[0]['op']

				# Open Group
				query_filter += ' ( '

				for filter_index in range(len(group)):
					filter_item = group[filter_index]

					# For every but the first filter per group, add its operator
					if filter_index != 0:
						query_filter += filter_item['op']

					# Open Filter
					query_filter += ' ( '

					query_filter += self.fields[filter_item['field']][filter_item['type']]['query']
					query_params += self.fields[filter_item['field']][filter_item['type']]['get_input_value'](filter_item['input'])
					filter_added=True

					# Close Filter
					query_filter += ' ) '

				# Close Group
				query_filter += ' ) '

				if group_index == last_group_index:
					# surrounding everything
					query_filter += ' ) '
		except Exception as e:
			print(f'[!] Building the SQL query with filters failed: {e}')
			print(f'\tThe following filters were tried: {inp_filters}')

		query  = self.data_query_one
		query += query_filter if filter_added else ''
		query += self.data_query_two

		return query, query_params

class TagRibbons:
	# maps the actual tag values to their label for selection and color
	map = { # The first option must be the default option (no tag)
		'Choose tag': {
			'tag-label': '(Remove tag)',
			'css-color': 'linear-gradient(to right, #2C5364, #0F2027)'
		},
		'Todo': {
			'tag-label': 'Todo',
			'css-color': 'linear-gradient(to right, #A5CC82, #00467F)'
		},
		'Interesting': {
			'tag-label': 'Interesting',
			'css-color': 'linear-gradient(to right, #c94b4b, #4b134f)'
		},
		'Starred': {
			'tag-label': 'Starred',
			'css-color': 'linear-gradient(to right, #F09819, #FF512F)'
		},
		'High value': {
			'tag-label': 'High value',
			'css-color': 'linear-gradient(to right, #FFC837, #FF8008)'
		},
		'Vulnerable': {
			'tag-label': 'Vulnerable',
			'css-color': 'linear-gradient(to right, #ff0084, #33001b)'
		},
		'Pwned!': {
			'tag-label': 'Pwned!',
			'css-color': 'linear-gradient(to right, #8E0E00, #1F1C18)'
		},
		'Checked': {
			'tag-label': 'Checked',
			'css-color': 'linear-gradient(to right, #0f9b0f, #000000)'
		},
		'Ignore': {
			'tag-label': 'Ignore',
			'css-color': 'linear-gradient(to right, #b29f94, #603813)'
		},
	}

	customLabelRegex = '[A-Za-z][A-Za-z0-9 ]+'
