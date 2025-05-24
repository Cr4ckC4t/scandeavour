# This is just the base class with pseudo code for demonstration in the validate/parse logic
class BaseIngestor:

	def __init__(self, name, accepted_files):
		self.name = name
		self.accepted_files = accepted_files

	def getName(self):
		return self.name

	def getAcceptedFiles(self):
		return self.accepted_files

	def validate(self, file_path):
		# Run checks to ensure that this ingestor is the right one for this file
		# Do not use .read() as this does not perform well on large files
		# Optimally you read the file line by line for whatever validation you need
		linecount = 0
		with open(file_path, 'rb') as f:
			for line in f:
				linecount += 1
				if b'magic' in line:
					# Save the file path 
					self.file_path = file_path
					# Return True to signal that the ingestor will parse this file
					return True
				if linecount > 20:
					break
		# Return False if this ingestor is not suitable
		return False

	def parse(self):
		# Parse file contents and store relevant information
		with open(self.file_path, 'rb') as f:
			for line in f:
				self.host = line.decode('utf8')
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
