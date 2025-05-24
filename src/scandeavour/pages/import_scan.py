from dash import html, dcc, callback, Input, Output, State, register_page, get_asset_url, set_props
from dash.exceptions import PreventUpdate
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from scandeavour.components.customToast import CustomToast
from scandeavour.ingestors import *
from scandeavour.ingestor_base import BaseIngestor
import sys
import inspect
from scandeavour.utils import getDB, IPtoNum, NumToIP, getHostLabel
from base64 import b64decode
from os import path, remove, stat
import tempfile
import time

register_page(__name__, path='/')

def layout(**kwargs):

	available_ingestors = []
	ingestor_modules = inspect.getmembers(sys.modules['scandeavour.ingestors'], inspect.ismodule)
	for ingestor_module in ingestor_modules:
		mod_name, mod = ingestor_module
		ingestor_classes = inspect.getmembers(mod, inspect.isclass)
		for ingestor in ingestor_classes:
			ingestor_name, ingestor_class = ingestor
			if issubclass(ingestor_class, BaseIngestor) and ingestor_name != 'BaseIngestor':
				available_ingestors.append(ingestor_class())

	accepted_files = ', '.join([ing.getAcceptedFiles() for ing in available_ingestors])

	return 	html.Div([
			# Store value that is cleared when browser tab closes
			dcc.Store(id='upload-data-change', data=False, storage_type='session'),
			dcc.Upload(
				id='upload-scan',
				children=html.Div([
						html.Img(src=get_asset_url('icons/upload-file.svg'), id='import-scan-file-image'), # updated during upload
						html.H4('Import scan', id='import-scan-h4label'), # updated during upload
						html.Span('Select a file or use drag and drop.'),
						html.Span(f'Accepted file types: {accepted_files}'),
					],
					className='upload-content'
				),
				className='upload-scan',
				style={
					'margin': '1rem',
					'borderWidth': '1px',
					'borderStyle': 'dashed',
					'borderRadius': '1rem',
					'textAlign': 'center',
					'padding': '1rem'
			        },
				style_active={
					'backgroundColor': 'var(--bs-secondary)',
				},
				multiple=True,
				disabled=False
			),
			html.Div([
				dbc.Progress(
					id="upload-progress",
					style={'visibility': 'hidden'},
					animated=True,
					striped=True,
					color='success',
					class_name='label-progress-bar',
					label=''
				)
			]),
			html.Div([
				html.Img(src=get_asset_url('icons/headings/list.svg')),
				html.H3('Imported files')
			], className='medium-heading'),
			dcc.Loading([
				dag.AgGrid(
					id='input-files-table',
					rowData=[{'type': 'loading', 'filesize': 0}],
					columnDefs=[
						{'headerName':'Type', 'field':'type', 'maxWidth':150, 'filter': 'agTextColumnFilter'},
						{'headerName':'Filename', 'field':'filename', 'filter': 'agTextColumnFilter'},
						{'headerName':'Hosts scanned', 'field':'targetsScanned', 'maxWidth': 150, 'filter': 'agNumberColumnFilter'},
						{'headerName':'Up', 'field':'targetsUp', 'maxWidth': 100, 'filter': 'agNumberColumnFilter'},
						{'headerName':'Ingest date', 'field':'ingestDate', 'maxWidth': 200},
						{'headerName':'Filesize', 'field':'filesize', 'maxWidth': 150, 'filter': 'agNumberColumnFilter', 'valueFormatter':{'function':'FileSize(params.value)'}}
					],
					defaultColDef={'useValueFormatterForExport': 'False'},
					className='ag-theme-alpine-dark input-file-table-container',
					dashGridOptions={'domLayout': 'autoHeight'},
					columnSize='responsiveSizeToFit',
					style= {
						'height': None,
						'marginBottom': '0.5rem'
					},
				)],
				overlay_style={'visibility': 'visible', 'filter': 'blur(2px)'},
				type='circle',
				delay_hide=200,
				color='#00ffe0'
			),
			dbc.Button('Delete all imported scans', id='btn-delete-scans', disabled=False, outline=True, color='danger', class_name='me-1 scan-del-btn'),
			dbc.Modal(
				[
					dbc.ModalHeader(dbc.ModalTitle('Delete scans')),
					dbc.ModalBody('This will delete all scans stored in the database. Are you sure?'),
					dbc.ModalFooter(
						dbc.Button(
							'Delete',
							id='btn-confirm-delete-scans',
							outline=True,
							color='danger',
							n_clicks=0
						)
					),
				],
				id='modal-confirm-delete-scans',
				centered=True,
				is_open=False
			),
		],
		className='upload-container')


@callback(	Output('upload-data-change', 'data'),
		Output('div-toaster', 'children', allow_duplicate=True),
		Input('upload-scan', 'contents'),
		State('upload-scan', 'filename'),
		State('div-toaster', 'children'),
		background=True, # Required, so we can use "progress" here, for realtime updates
		running=[
			# view progress bar while uploading
			(
				Output('upload-progress', 'style'),
				{"visibility": "visible"},
				{"visibility": "hidden"}
			),
			# prevent database deletion
			(
				Output('btn-delete-scans', 'disabled'),
				True,
				False
			),
			# prevent new upload
			(
				Output('upload-scan', 'disabled'),
				True,
				False
			),
			# change label
			(
				Output('import-scan-h4label', 'children'),
				'Working on it...',
				'Import scan',
			),
			# change image
			(
				Output('import-scan-file-image','src'),
				get_asset_url('icons/coffee.svg'),
				get_asset_url('icons/upload-file.svg')
			)
		],
		progress=[
			Output('upload-progress', 'value'),
			Output('upload-progress', 'label')
		],
		prevent_initial_call=True,
	) # see https://dash.plotly.com/background-callbacks for explanation of set_progress
def _cb_fileUpload(set_progress, file_contents, file_names, toasts):
	# This gets called on upload but we patched file_contents to be empty, to not crash the browser.
	# By now the file contents are uploaded already.
	# See assets/patchFileReader.js.
	if not file_names:
		raise PreventUpdate

	print(f'[+] Parsing uploaded file(s):')
	for ix in range(len(file_names)):
		print(f'\t- ({ix+1}) {file_names[ix]}')

	# Load ingestors
	available_ingestors = []
	try:
		ingestor_modules = inspect.getmembers(sys.modules['scandeavour.ingestors'], inspect.ismodule)
		for ingestor_module in ingestor_modules:
			mod_name, mod = ingestor_module
			ingestor_classes = inspect.getmembers(mod, inspect.isclass)
			for ingestor in ingestor_classes:
				ingestor_name, ingestor_class = ingestor
				if issubclass(ingestor_class, BaseIngestor) and ingestor_name != 'BaseIngestor':
					available_ingestors.append(ingestor_class)
	except Exception as e:
		toasts.append(CustomToast(
			[ f'Error: {e}' ],
			headerText=f'Failed to load ingestors',
			level='error',
			duration=10000,
		))
		file_contents = None

	if len(available_ingestors) < 1:
		toasts.append(CustomToast(
			[ f'At least one ingestor is required in the "ingestors" folder.' ],
			headerText=f'No ingestors found',
			level='error',
			duration=10000,
		))
		file_contents = None

	# For the progress calculations
	# we start at 40/100 when we are here (40% is set by the assets/patchFileReader.js)
	# so we got 60 left to fill.
	parse_bpct = 40									# start of progress bar (base percentage)
	parse_ftotal = len(file_names)					# files to process
	parse_fcnt = 0									# files processed
	parse_fpct = int((100-parse_bpct)/parse_ftotal)	# percentages available per file (regardless of their size)
	

	# Files have been uploaded to a tmp dir (paths are in file_contents)
	# real file names are in file_names and
	# ingestors have been loaded (at least one)
	if file_contents is not None:
		for tmp_name, name in zip(file_contents, file_names):
			# Increase counter immediately, because it may fail anytime and then we continue with the next one
			parse_fcnt += 1

			# Set progress to base percentage + start of nth file
			set_progress((
				parse_bpct+parse_fpct*(parse_fcnt-1),
				f'📂 {parse_fcnt}|{parse_ftotal} - Loading scan 👷'
			))

			tmp_name = b64decode(tmp_name.split(',')[1]).decode()
			tmp_file = path.join(tempfile.gettempdir(),tmp_name)
			fsize = stat(tmp_file).st_size

			# Let each ingestor validate the file to see if it can parse the scan
			ingestor = None
			for cls in available_ingestors:
				i = cls()
				try:
					if i.validate(tmp_file):
						ingestor = i
						break
				except Exception as e:
					toasts.append(CustomToast(
						[ f'[{i.getName()}] Failed to validate {tmp_file} ({name}): {e}' ],
						headerText=f'Parse error',
						level='error',
						duration=6000,
					))
					# This may have been an error in the parser
					# but another parser could still be valid
					continue

			if ingestor is None:
				toasts.append(CustomToast(
					[ f'Filetype of {name} is not yet supported.' ],
					headerText=f'Missing ingestor',
					level='warning',
					duration=6000,
				))
				continue

			try:
				ingestor.parse()
				# Delete tmp file
				remove(tmp_file)
			except Exception as e:
				toasts.append(CustomToast(
					[ f'Failed to parse {name} ({tmp_file} may still exist): {e}' ],
					headerText=f'Ingestor failed',
					level='warning',
					duration=10000,
				))
				continue

			scan_interface = ingestor.getDatabaseInterface()

			if scan_interface['hosts_scanned'] < 1:
				toasts.append(CustomToast(
					[ f'No hosts were scanned in {name}.' ],
					headerText=f'Scan skipped',
					level='info',
					duration=5000,
				))
				continue

			# Now we parsed the file and can put it into the database

			total_hosts = len(scan_interface['hosts'])

			# Set progress to base percentage + start of nth file + 30% of the assigned percentages per file
			# This represents that the workload per scan is roughly 30% reading, 70% database manipulation
			set_progress((
				parse_bpct+parse_fpct*(parse_fcnt-0.7),
				f'📂 {parse_fcnt}|{parse_ftotal} - Added 0|{total_hosts} 🖥️'
			))

			db_con, db = getDB()

			# Only now we are kind of sure that we want to store the scan, so create a file entry in the db
			db.execute('INSERT INTO input_files(type, filename, ingestDate, filesize) VALUES(?,?,unixepoch(),?)',(
				ingestor.getName(),
				name,
				fsize
			))
			fileID = db.lastrowid

			db.execute('INSERT INTO scans(file, tool, args, version, start, stop, hostsUp, hostsScanned) VALUES (?,?,?,?,?,?,?,?)', (
				fileID,
				scan_interface['tool'],
				scan_interface['args'],
				scan_interface['version'],
				scan_interface['start'],
				scan_interface['stop'],
				scan_interface['hosts_up'],
				scan_interface['hosts_scanned']
			))
			scanID = db.lastrowid

			shosts = scan_interface['hosts']

			added_hosts_cnt = 0
			for shost in shosts:
				added_hosts_cnt += 1 # used for the progress bar at the end

				# All of these addresses are considered unique identifiers for a host:
				# 	IPv4, IPv6, MAC
				# If we detect one of these in the database, we update all new available addresses for the host!
				qr = db.execute('SELECT hid, ipv4, ipv6, mac, reason, os_name, os_accuracy, os_family, os_vendor FROM hosts WHERE (ipv4=?) OR (ipv6=?) OR (mac=?)', (
					IPtoNum(shost['ipv4']),
					shost['ipv6'],
					shost['mac'],
				)).fetchone()
				if qr is not None:
					# Host already exists
					hostID,eipv4,eipv6,emac,ereason,eos_name,eos_accuracy,eos_family,eos_vendor = qr
					# Use the newer IPv4/IPv6/MAC (values may be None if neither the existing nor the new value is set to a value)
					new_ipv4 = (eipv4 if shost['ipv4'] == '' else IPtoNum(shost['ipv4']))
					new_ipv6 = (eipv6 if shost['ipv6'] == '' else shost['ipv6'])
					new_mac = (emac if shost['mac'] == '' else shost['mac'])
					# Generate distinct list of current and new hostnames
					e_hostnames = db.execute('SELECT name FROM hostnames WHERE host=?',(hostID,)).fetchall()
					e_hostnames = [ehn[0] for ehn in e_hostnames]
					new_hostnames = e_hostnames + [nhn for nhn in shost['names'] if nhn not in e_hostnames]
					# Generate the label (replace None with empty strings)
					new_label = getHostLabel(NumToIP(new_ipv4 or -1), new_ipv6 or '', new_mac or '', new_hostnames)

					db.execute('UPDATE hosts SET ipv4=?, ipv6=?, mac=?, reason=?, os_name=?, os_accuracy=?, os_family=?, os_vendor=?, label=? WHERE hid=?', (
						new_ipv4,
						new_ipv6,
						new_mac,
						(ereason if shost['reason'] == '' else shost['reason']),
						# Only update when accuracy is better
						# When the accuracy is better
						(eos_name if int(shost['os_accuracy']) < int(eos_accuracy) or shost['os_name'] == '' else shost['os_name']),
						(eos_accuracy if int(shost['os_accuracy']) < int(eos_accuracy) else shost['os_accuracy']),
						(eos_family if int(shost['os_accuracy']) < int(eos_accuracy) or shost['os_family'] == '' else shost['os_family']),
						(eos_vendor if int(shost['os_accuracy']) < int(eos_accuracy) or shost['os_vendor'] == '' else shost['os_vendor']),
						new_label,
						hostID
					))
				else:
					# Host does not exist yet
					host_label = getHostLabel(shost['ipv4'], shost['ipv6'], shost['mac'], shost['names'])
					db.execute('INSERT INTO hosts(ipv4, ipv6, mac, reason, os_name, os_accuracy, os_family, os_vendor, label) VALUES(?,?,?,?,?,?,?,?,?)', (
						None if ((newIP:=IPtoNum(shost['ipv4'])) < 0) else newIP,
						None if shost['ipv6'] == '' else shost['ipv6'],
						None if shost['mac'] == '' else shost['mac'],
						shost['reason'],
						shost['os_name'],
						shost['os_accuracy'],
						shost['os_family'],
						shost['os_vendor'],
						host_label
					))
					hostID = db.lastrowid

				# Update hostname values
				for new_name in shost['names']:
					# doubles (produced by nmap for user and PTR type for example) will be ignored by the DB constraint UNIQUE
					db.execute('INSERT OR IGNORE INTO hostnames(host, name) VALUES (?, ?)', (
						hostID,
						new_name
					))

				try:
					# If this fails due to a UNIQUE constraint, then
					# the scan contains two results for one host.
					db.execute('INSERT INTO scans_hosts(scan, host) VALUES(?,?)', (
						scanID,
						hostID
					))
				except:
					# This should not happen but we updated the host already and simply
					# skip the ports - let's continue after that.
					toasts.append(CustomToast(
						[ f'Found two results for one host in the same scan: {name}.' ],
						headerText=f'Scan possibly malformed',
						level='warning',
						duration=6000,
					))
					continue

				hports = shost['ports']
				for hport in hports:
					qr = db.execute('SELECT pid, svc_name, svc_info, svc_ssl FROM ports WHERE host=? AND port=? AND protocol=?', (
						hostID,
						hport['port'],
						hport['protocol']
					)).fetchone()
					if qr is not None:
						# Port already exists
						portID,esvc_name,esvc_info,esvc_ssl = qr
						db.execute('UPDATE ports SET svc_name=?, svc_info=?, svc_ssl=? WHERE pid=?',(
							# Use the new value if one exists
							(esvc_name if hport['svc_name'] == '' else hport['svc_name']),
							(esvc_info if hport['svc_info'] == '' else hport['svc_info']),
							(esvc_ssl if hport['svc_ssl'] == '' else hport['svc_ssl']),
							portID
						))
					else:
						# Port does not exist yet
						db.execute('INSERT INTO ports(host, port, protocol, svc_name, svc_info, svc_ssl) VALUES(?,?,?,?,?,?)', (
							hostID,
							hport['port'],
							hport['protocol'],
							hport['svc_name'],
							hport['svc_info'],
							hport['svc_ssl'],
						))
						portID = db.lastrowid

					db.execute('INSERT INTO scans_ports(scan, port) VALUES(?,?)', (
						scanID,
						portID
					))

					pscripts = hport['scripts']
					for pscript in pscripts:
						# If the same script was already run by a previous scan, then overwrite the results
						# Reason: A second scan in the network may reveal new results and we only want the up to date information
						qr = db.execute('SELECT psid FROM pscripts WHERE port=? AND host=? AND name=?', (portID, hostID, pscript['id'])).fetchone()
						if qr is not None:
							pscriptID = qr[0]
							db.execute('UPDATE pscripts SET scan=?, output=? WHERE psid=?', (
								scanID, pscript['output'], pscriptID # Keep in mind that this pscriptID is not pscript['id']! One is the database primary key, the other the script name.
							))
						else:
							db.execute('INSERT INTO pscripts(scan, host, port, name, output) VALUES(?,?,?,?,?)', (
								scanID, hostID, portID, pscript['id'], pscript['output']
							))

				# Fill up the remaining 70% of every scan with the current amount of processed hosts
				# 70%
				set_progress((
					parse_bpct+parse_fpct*(parse_fcnt-0.7 + 0.7*added_hosts_cnt/total_hosts),
					f'📂 {parse_fcnt}|{parse_ftotal} - Added {added_hosts_cnt}|{total_hosts} 🖥️'
				))

			toasts.append(CustomToast(
				[ f'Found {scan_interface["hosts_up"]} hosts in {name}.' ],
				headerText=f'Scan imported',
				level='success',
				duration=3000,
			))

			# Be sparse with transactions as they take longer than statements (because changes are actually written to disk)
			# https://www.sqlite.org/faq.html#q19
			db_con.commit()
			db_con.close()
		
		# All scans processed
		set_progress((100, f'All done 🎉'))
		time.sleep(2) # Keep this for better UX

	return True, toasts


@callback(	Output('input-files-table', 'rowData'),
		Input('upload-data-change', 'data'),
	)
def _cb_updateFileUploadTable(_):
	db_con, db = getDB()
	# Nested SQL queries won't work with the same connection when iterating over a cursor
	# Alternatively we'd have to use fetchall()
	db_con_secondary, db_secondary = getDB()

	if_table_rows = []
	qr = db.execute('SELECT fid, type, filename, datetime(ingestDate,"unixepoch","localtime"), filesize FROM input_files')
	for file in qr:
		fid = file[0]
		hosts_scanned, hosts_up = db_secondary.execute('SELECT hostsScanned, hostsUp FROM scans WHERE file=?', (fid,)).fetchone()
		if_table_rows.append(dict(
			type=file[1],
			filename=file[2],
			targetsScanned=hosts_scanned,
			targetsUp=hosts_up,
			ingestDate=file[3],
			filesize=file[4]
		))
	db_con.close()
	db_con_secondary.close()
	return if_table_rows


@callback(	Output('modal-confirm-delete-scans', 'is_open'),
		Input('btn-delete-scans', 'n_clicks'),
		State('input-files-table', 'rowData'),
		prevent_initial_call = True
	)
def _cb_deleteAllScans(n, eles):
	return (len(eles)>0)

@callback( 	Output('upload-data-change', 'data', allow_duplicate=True),
		Output('modal-confirm-delete-scans', 'is_open', allow_duplicate=True),
		Input('btn-confirm-delete-scans', 'n_clicks'),
		prevent_initial_call = True
)
def _cb_confirmDeleteAllScans(n_clicks):
	if n_clicks:
		con, cur = getDB()
		cur.execute('DELETE FROM scans_ports')
		cur.execute('DELETE FROM scans_hosts')
		cur.execute('DELETE FROM ports')
		cur.execute('DELETE FROM pscripts')
		cur.execute('DELETE FROM hosts')
		cur.execute('DELETE FROM hostnames')
		cur.execute('DELETE FROM scans')
		cur.execute('DELETE FROM input_files')
		con.commit()
		con.close()
	return True, False
