class BaseIngestor:

	def __init__(self, name, accepted_files):
		self.name = name
		self.accepted_files = accepted_files

	def getName(self):
		return self.name

	def getAcceptedFiles(self):
		return self.accepted_files

	def validate(self, raw_file):
		# Run checks to ensure that this ingestor is the right one
		# for this file
		if len(raw_file) < 1:
			# Return False if it is not
			return False

		# Save the file otherwise
		self.raw_file = raw_file

		# Return True to signal that this ingestor will parse the file
		return True

	def parse(self):
		# Parse file contents and store relevant information
		self.host = self.raw_file.decode('utf8')
		self.port = 0

	def getDatabaseInterface(self):
		# Return this mandatory scan interface
		scan = {
			'tool': '', 				# * [str] tool name
			'args': '', 				#   [str] scan arguments
			'start': 0, 				#   [int] timestamp scan start
			'stop': 0, 				#   [int] timestamp scan stop
			'version': '',				#   [str] tool version
			'hosts_up': 0,				# * [int] hosts identified as up
			'hosts_scanned': 0,			# * [int] hosts scanned
			'hosts': [{				#   <arr>[obj] hosts identified as up
				'ipv4': '',			# X [str] ipv4
				'ipv6': '',			# X [str] ipv6
				'mac': '',			# X [str] mac
				'names': [],			#   <arr>[str] list of hostnames
				'reason': '',			#   [str] reason why this host is marked alive
				'os_name': '',			#   [str] OS name (e.g. Windows Server 2016)
				'os_accuracy': 0, 		#   [int] OS accuracy
				'os_family': '',		#   [str] OS family (e.g. Windows)
				'os_vendor': '',		#   [str] OS vendor (e.g. Microsoft)
				'ports': [{			#   <arr>[obj]
					'port': 0,		# * [int] port number
					'protocol': '',		# * [str] port protocol (e.g. tcp)
					'svc_name': '', 	#   [str] service name
					'svc_info': '', 	#   [str] service details
					'svc_ssl': '',		#   [str] service tunnel
					'scripts': [{		#   <arr>[obj] scripts for port
						'id': '',	# * [str] script name
						'output': '',	# * [str] script output
					}],			#
				}],				# * = must exist (no * = can be set to empty value)
			}]					# X = at least one must exist
		}
		return scan
