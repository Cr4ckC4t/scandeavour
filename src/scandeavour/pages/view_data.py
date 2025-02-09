from dash import html, dcc, callback, Input, Output, State, register_page, get_asset_url, Patch, no_update, ctx, ALL
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from scandeavour.components.customToast import CustomToast
from scandeavour.utils import getDB, NumToIP, IPtoNum, CIDRtoFirstLast, DataFilterMap, TagRibbons
import re

register_page(__name__, path='/data')

def layout(**kwargs):
	return html.Div([
		dcc.Store('datatable-settings', data={
				'filters': [],
			}, storage_type='session'),
		dcc.Store('host-detail-settings', data={
				'show-tags': True
			}, storage_type='session'),
		dcc.Store('tag-click-intent', data={'hid': None}, storage_type='memory'),
		dcc.Store('trigger-tag-update', data={}, storage_type='memory'),
		html.Div([
			html.Div([
				html.Img(src=get_asset_url('icons/headings/filter.svg')),
				html.H3('Filters')
			], className='medium-heading'),
			html.Div([
				dcc.Dropdown(
					options = [
						'AND',
						'OR',
						'AND NEW GROUP',
						'OR NEW GROUP',
					],
					value = 'AND',
					clearable = False,
					className = 'input-filter-basic-dropdown dd-boolean-op',
					id='d-filter-op'
				),
				dcc.Dropdown(
					options = [field for field in DataFilterMap.fields],
					placeholder = 'Select field to filter...',
					className='input-filter-basic-dropdown dd-field-selector',
					id='d-filter-field'
				),
				dcc.Dropdown(
					options = [
						'contains',
						'is',
						'is not',
					],
					placeholder='Select filter type...',
					className='input-filter-basic-dropdown dd-match-op',
					id='d-filter-type'
				),
				dcc.Input(
					placeholder='Select a filter first',
					type='text',
					value='',
					disabled=True,
					debounce=True, # use Enter to submit query
					className='input-filter-basic-input',
					id='d-filter-input'
				),
			], className='input-filter-group'),
			html.Div(
				[],
				id='filter-box-container',
				className='filter-box-container'
			)
		],
		className='data-filters-container'),
	html.Hr(), # reverse indented by intent
		html.Div([
			html.Div([
				html.Div([
					html.Img(src=get_asset_url('icons/headings/grid.svg')),
					html.H3('Hosts'),
					html.H3('', id='result-counter', className='header-result-counter'),
					dbc.Progress(
						value=100,
						color='info',
						id='result-counter-pb',
						className='header-result-counter-progress'
					),
				], className='medium-heading'),
				html.Div(className='data-heading-grower'),
				# Clipboard
				dcc.Clipboard(id='export-clipboard', style={'display': 'none'}, n_clicks=0),
				# Download
				dcc.Download(id='export-download'),
				html.Div(
					[
						html.Img(
							src=get_asset_url('icons/datapage/export/clipboard.svg')
						),
						html.Span('IPv4 target list')
					],
					n_clicks=0,
					className='export-button',
					id='btn-export-target-list'
				),
				dbc.Tooltip(
					'Copy a line separated list of all target IPs matching the current filter to the clipboard (ready for use with Nmap -iL or Nessus)',
					target='btn-export-target-list',
					placement='top',
				),
				html.Div(
					[
						html.Img(
							src=get_asset_url('icons/datapage/export/clipboard.svg')
						),
						html.Span('Port list')
					],
					n_clicks=0,
					className='export-button',
					id='btn-export-port-list'
				),
				dbc.Tooltip(
					'Copy a comma separated list of all unique ports matching the current filter to the clipboard (ready for use with Nmap -p or Nessus)',
					target='btn-export-port-list',
					placement='top',
				),
				html.Div(
					[
						html.Img(
							src=get_asset_url('icons/datapage/export/download.svg')
						),
						html.Span('Hosts table (CSV)'),
					],
					n_clicks=0,
					className='export-button',
					id='btn-export-hosts-table'
				),
				dbc.Tooltip(
					'Export all hosts matching the current filter as CSV (includes all ports and all hostnames for these hosts, regardless of the filter)',
					target='btn-export-hosts-table',
					placement='top',
				),
			],
			className='data-table-heading'),
			dcc.Loading(
				[
					dcc.Input(
						value='',
						placeholder='Search in results 🔎',
						type='text',
						id='data-table-search-input',
						className='data-table-search-input'
					),
					dag.AgGrid(
						id='view-data-table',
						rowData=[{'os':'', 'hostname':'loading'}],
						columnDefs=[
							{'headerName': 'Hostname', 'field': 'hostname', 'width': 200, 'headerTooltip': 'All hostnames matching the current filter'},
							{'headerName': 'IPv4', 'field': 'ipv4', 'width': 160, 'headerTooltip': 'IPv4 address of the host'},
							{'headerName': 'Ports', 'field': 'ports', 'width': 350, 'headerTooltip': 'All ports matching the current filter (view host details for all ports)'},
							{'headerName': 'Scans', 'field': 'scans', 'headerTooltip': 'List of tools matching the current filter'},
							{'headerName': 'OS', 'field': 'os', 'width': 300, 'headerTooltip': 'Operating system information'},
							{'headerName': 'Tag', 'field': 'tag', 'width': 200, 'headerTooltip': 'Tag for the host (set it in the host details pane)'},
							{'headerName': 'Mac', 'field': 'mac', 'minWidth':100, 'flex': 1, 'headerTooltip': 'MAC address of the host'},
							{'headerName': 'IPv6', 'field': 'ipv6', 'minWidth':100, 'flex': 1, 'headerTooltip': 'IPv6 address of the host'},
							{'headerName': 'Hid', 'field': 'hid', 'hide': True},
						],
						defaultColDef={
							'wrapText': True,
							'autoHeight':True,
							'cellStyle': {'wordBreak':'normal'},
						},
						className='ag-theme-alpine-dark',
						style={'height': '30rem'},
						dashGridOptions={ # filter text is updated in callback and not listed here
							'rowSelection': 'multiple'
						},
					)
				],
				overlay_style={'visibility': 'visible', 'filter': 'blur(2px)'},
				type='circle',
				delay_hide=200,
				color='#00ffe0'
			),
		],
		className='data-table-container'),
	html.Hr(), # reverse indented by intent
		html.Div([
			html.Div([
				html.Div([
					html.Img(src=get_asset_url('icons/headings/pocket.svg')),
					html.H3('Details')
				], className='medium-heading'),
				html.Div(className='data-heading-grower'),
				dbc.Switch(
					id='btn-toggle-tags',
					label='Toggle tags',
					class_name='toggle-tags-button',
					persistence=True,
					persistence_type='session',
					value=False
				),
			], className='data-table-heading'),
			html.Div([
				# contains the selected items
			], className='data-detail-rows', id='data-detail-rows')
		],
		className='data-details-container'),

		# Modal for tag management
		dbc.Modal(
			[
				dbc.ModalHeader(dbc.ModalTitle('Update tag')),
				dbc.ModalBody(html.Div([
						html.Div([
							dbc.Label('Choose a tag'),
							dbc.RadioItems(
								options=[
									{'label': TagRibbons.map[opt]['tag-label'], 'value': opt}
									for opt in TagRibbons.map
								],
								value=[t for t in TagRibbons.map][0],
								id='hd-tag-selection',
							),
						]),
						html.Div(style = {
							'display': 'inline-block',
							'flexGrow': '1',
						}),
						html.Div([
							dbc.Label('Apply tag to'),
							dbc.RadioItems(
								options=[
									{'label': 'This host', 'value': 1},
									{'label': 'All selected hosts', 'value': 2},
									{'label': 'All current results', 'value': 3},
								],
								value=1,
								id='hd-tag-targets',
							),
						]),
					],
					style={
						'display': 'flex',
						'flexDirection': 'row',
					})
				),
				dbc.ModalFooter(
					dbc.Button(
						'Confirm',
						id='btn-confirm-modal-update-tag',
						outline=True,
						color='success',
						n_clicks=0
					)
				)
			],
			id='modal-update-tag',
			centered=True,
			is_open=False,
		)
	],
	className='data-view-container')


@callback(	Output('div-toaster', 'children', allow_duplicate=True),
		Output('export-clipboard', 'content'),
		Output('export-clipboard', 'n_clicks'), # Updating the clipboard clicks is required so the copy works!
		Output('export-download', 'data'),
		Input('btn-export-target-list', 'n_clicks'),
		Input('btn-export-port-list', 'n_clicks'),
		Input('btn-export-hosts-table', 'n_clicks'),
		State('view-data-table', 'rowData'),
		State('div-toaster', 'children'),
		State('export-clipboard', 'n_clicks'),
		prevent_initial_call=True
	)
def _cb_exportBtns(tl_clicks, pl_clicks, ht_clicks, rowData, toasts, clipboard_clicks):
	# Initial callback guard (it fires due to the dynamic page load, regardless of prevent_initial_call)
	if ([t for t in ctx.args_grouping if t['id'] == ctx.triggered_id][0]['value'] == 0):
		# We should even be fine without this guard but now I finally got to use Prevent Update and leave it as example
		raise PreventUpdate

	if ctx.triggered_id == 'btn-export-target-list':
		targets = []
		missingCounter = 0
		for row in rowData:
			ipv4 = row['ipv4']

			if ipv4 == '':
				missingCounter += 1
			else:
				targets.append(ipv4)

		if missingCounter > 0:
			toasts.append(CustomToast(
				[
					f'{missingCounter} hosts skipped due to missing IPv4'
				],
				headerText='Some hosts were skipped',
				level='warning',
				duration=8000
			))

		toasts.append(CustomToast(
			[
				f'Copied {len(targets)} target{"s" if len(targets)!=1 else ""} to clipboard'
			],
			headerText='Clipboard',
			level='success',
		))

		# A comma separated list is not a great fit because Nmap does not accept comma separated lists for hosts in a target file
		# Nmap: https://nmap.org/book/host-discovery-specify-targets.html
		# Nessus would accept it: https://docs.tenable.com/nessus/Content/ScanTargets.htm
		# Both support newline separated lists though. For use on the command line, use a simple search and replace.
		return toasts, '\n'.join(targets), clipboard_clicks+1, no_update

	elif ctx.triggered_id == 'btn-export-port-list':
		ports = []
		protoSpecial = False
		for row in rowData:
			ports_string = row['ports']
			if len(ports_string)==0:
				continue
			for port in ports_string.split(', '):
				number,proto=port.split('/')
				new_port=''
				# Both Nmap and Nessus support <protocol-letter>:<port>:
				# https://nmap.org/book/man-port-specification.html
				# https://www.tenable.com/blog/configuring-the-ports-that-nessus-scans
				if proto.lower() == 'tcp':
					new_port+='T:'
				elif proto.lower() == 'udp':
					new_port+='U:'
				elif proto.lower == 'sctp':
					new_port+='S:'
				elif proto.lower == 'ip':
					new_port+='P:'
				else:
					new_port+='' # Nmap would add it to every protocol in this case

				new_port += str(number)

				if new_port not in ports:
					ports.append(new_port)
				else:
					continue

				if new_port[0] not in ['T', 'U']:
					protoSpecial=True

		if protoSpecial is True:
			toasts.append(CustomToast(
				[
					'Some port protocol was neither TCP nor UDP. Nmap will be able to deal with the copied results but other scanners might not be.'
				],
				duration=10000,
				headerText='Custom protocol',
				level='warning'
			))

		toasts.append(CustomToast(
			[
				f'Copied {len(ports)} port{"s" if len(ports)!=1 else ""} to clipboard'
			],
			headerText='Clipboard',
			level='success',
		))

		# At least Nessus and Nmap support comma separated lists for port specification
		return toasts, ','.join(ports), clipboard_clicks+1, no_update

	elif ctx.triggered_id == 'btn-export-hosts-table':
		db_con, db = getDB()

		newFilename='exported-hosts.csv'
		sep = ';' # field separator
		header = sep.join(['Host', 'Name', 'Port', 'Service'])
		lines=[]

		hostCount = 0
		for row in rowData:
			# this should always succeed because the row that was fetched must come from the table
			qr = db.execute('SELECT hid, ipv4, ipv6, mac FROM hosts WHERE hid=?', (row['hid'],)).fetchone()
			hid, ipv4, ipv6, mac = qr
			host = []
			if ipv4 is not None:
				host.append(NumToIP(ipv4))
			if ipv6 is not None:
				host.append(ipv6)
			if mac is not None:
				host.append(mac)

			qr = db.execute('SELECT name FROM hostnames WHERE host=?', (hid,)).fetchall()
			names = [h[0] for h in qr]

			qr = db.execute('SELECT port||"/"||protocol, svc_name, svc_info FROM ports WHERE host=?', (hid,)).fetchall()
			ports = [{
				'port': r[0],
				'service': r[2] if len(r[2])>0 else (r[1] if len(r[1])>1 else '')
			} for r in qr]

			nHostRows = max(len(host),len(ports),len(names))

			for ix in range(nHostRows):
				h = host[ix] if ix<len(host) else ''
				n = names[ix] if ix<len(names) else ''
				p = ports[ix]['port'] if ix<len(ports) else ''
				s = ports[ix]['service'].replace(sep, ' ') if ix<len(ports) else ''

				# Yes, we could just write it to disk directly.
				# This would also prevent issues with very large result sets.
				# However, the Download option offers easier UX and usage.
				# Unless we hit performance issues, this can stay.
				lines.append(sep.join([h,n,p,s]))
			hostCount+=1

		toasts.append(CustomToast(
			[
				f'Exported {hostCount} host{"s" if hostCount!=1 else ""} to {newFilename}'
			],
			headerText='Downloading CSV...',
			level='success' if hostCount>0 else 'warning',
		))

		return toasts, no_update, no_update, {
			'filename': newFilename,
			'content': '\n'.join(lines)
		}
		db_con.close()

	return no_update, no_update, no_update, no_update


@callback(	Output('d-filter-input', 'placeholder'),
		Output('d-filter-input', 'pattern'),
		Output('d-filter-input', 'disabled'),
		Output('d-filter-input', 'value'),
		Output('d-filter-type', 'value'),
		Output('d-filter-type', 'placeholder'),
		Output('d-filter-type', 'options'),
		Output('d-filter-op', 'options'),
		Output('d-filter-op', 'value'),
		Output('datatable-settings', 'data'),
		Output('div-toaster', 'children', allow_duplicate=True),
		Input('d-filter-op', 'value'),
		Input('d-filter-field', 'value'),
		Input('d-filter-type', 'value'),
		Input('d-filter-input', 'value'),
		State('datatable-settings', 'data'),
		State('div-toaster', 'children'),
		prevent_initial_call = True
	)
def _cb_parseFilterInputs(filter_op, filter_field, filter_type, filter_input, datatable_settings, toasts):
	cur_table_filters = datatable_settings['filters']
	out_filter_input_placeholder='Select a filter first'
	out_filter_input_pattern='.*'
	out_filter_input_disabled=True
	out_filter_input_value=''
	out_filter_type_value=no_update
	out_filter_type_placeholder='Select filter type...'
	out_filter_type_options=[]
	out_filter_op_options=no_update
	out_filter_op_value=no_update
	out_table_filters=None

	filter_map=DataFilterMap.fields

	if filter_field is None:
		out_filter_type_placeholder='Select field first...'
	else:
		# update options
		out_filter_type_options = [ ft for ft in DataFilterMap.fields[filter_field] ]

	# Reset filter type
	if ctx.triggered_id == 'd-filter-field':
		out_filter_type_value = None
		filter_type = None

	# Reset filter input
	if ctx.triggered_id in ['d-filter-field', 'd-filter-op', 'd-filter-type']:
		out_filter_input_value = ''

	if filter_op is not None and filter_field is not None and filter_type is not None:
		out_filter_input_disabled=False
		out_filter_input_placeholder=filter_map[filter_field][filter_type]['placeholder']
		out_filter_input_pattern=filter_map[filter_field][filter_type]['pattern']

		if ctx.triggered_id == 'd-filter-input' and filter_input != '':
			# Reaching this branch, we are adding a new filter:
			# print(f'TRY ADDING FILTER: {filter_op}, {filter_field}, {filter_type}, {filter_input}')

			# Input validator
			pattern = re.compile(filter_map[filter_field][filter_type]['pattern'])
			if not pattern.fullmatch(filter_input):
				out_filter_input_value=''
				toasts.append(CustomToast(
					[
						f'The input does not match the expected type.'
					],
					headerText='Invalid filter',
					level='warning',
					duration=5000
				))
			else:

				ctf = cur_table_filters

				if filter_op.endswith('NEW GROUP'):
					# Add a new group
					ctf.append([{
						'op': filter_op.split(' ')[0], # AND or OR
						'field': filter_field,
						'type': filter_type,
						'input': filter_input
					}])
					# After adding a new group we probably want to keep adding to that group
					# So we reset the value (AND should be more common)
					out_filter_op_value='AND'

				elif filter_op in ['AND', 'OR']:
					# Add any operand
					# Special case: it's the very first filter, so add a group
					if len(ctf) == 0:
						ctf.append([{
							'op': filter_op, # AND or OR
							'field': filter_field,
							'type': filter_type,
							'input': filter_input
						}])
					# Otherwise, add to the last group
					else:
						ctf[-1].append({
							'op': filter_op, # AND or OR
							'field': filter_field,
							'type': filter_type,
							'input': filter_input
						})
				elif ' GROUP ' in filter_op:
					# Add to a specific group
					fop, _, findex = filter_op.split(' ')
					ctf[int(findex)-1].append({
						'op': fop,
						'field': filter_field,
						'type': filter_type,
						'input': filter_input
					})

				out_table_filters = ctf
				# After updating the filter, update the group options
				available_groups = len(ctf)
				out_filter_op_options= ['AND', 'OR', 'AND NEW GROUP', 'OR NEW GROUP'] # This is also set in _cb_renderUpdateFilters
				for index in range(available_groups):
					out_filter_op_options.append(f'AND GROUP {index+1}')
					out_filter_op_options.append(f'OR GROUP {index+1}')

	datatable_settings['filters'] = out_table_filters
	return 	[out_filter_input_placeholder,
		out_filter_input_pattern,
		out_filter_input_disabled,
		out_filter_input_value,
		out_filter_type_value,
		out_filter_type_placeholder,
		out_filter_type_options,
		out_filter_op_options,
		out_filter_op_value,
		datatable_settings if out_table_filters is not None else no_update,
		toasts]


@callback(	Output('datatable-settings', 'data', allow_duplicate=True),
		Output('d-filter-op', 'options', allow_duplicate=True),
		Output('d-filter-op', 'value', allow_duplicate=True),
		Output('filter-box-container', 'children'),
		Input('datatable-settings', 'data'), # All other inputs are buttons that trigger filter modifications
		Input({'type': 'btn-del-group', 'index': ALL}, 'n_clicks'),
		Input({'type': 'btn-del-single-filter', 'index': ALL}, 'n_clicks'),
		prevent_initial_call=True
	)
def _cb_renderUpdateFilters(datatable_settings, del_group, del_single_filter):
	table_filters = datatable_settings['filters']
	new_filter_boxes = []
	new_filter_op_options = no_update
	new_filter_op_value = no_update
	_update_table_filters = False

	# There are no filters to process
	if len(table_filters) == 0:
		return no_update, no_update, no_update, new_filter_boxes

	# If buttons triggered the update, then we have to update the filter data
	if ctx.triggered_id != 'datatable-settings':
		_update_table_filters = True

		if ctx.triggered_id['type'] == 'btn-del-group':
			# Deleting an entire group
			table_filters.pop(int(ctx.triggered_id['index'])-1)

		elif ctx.triggered_id['type'] == 'btn-del-single-filter':
			# Deleting a single filter
			del_group_index, del_filter_index = ctx.triggered_id['index'].split('-')
			del_group_index = int(del_group_index)-1
			del_filter_index = int(del_filter_index)
			if del_filter_index != 0:
				# Trivial case: delete a random one from the middle or end
				table_filters[del_group_index].pop(del_filter_index)
			else:
				# Delete the first filter from a group
				if len(table_filters[del_group_index]) == 1:
					# It was the last item, delete the group
					table_filters.pop(del_group_index)
				else:
					# It was not the last item, store the group operator in next item
					del_item = table_filters[del_group_index].pop(del_filter_index)
					table_filters[del_group_index][0]['op'] = del_item['op']

		# When filters were updated, we may have to rebuild the available group options for the filter selection
		new_filter_op_options = ['AND', 'OR', 'AND NEW GROUP', 'OR NEW GROUP'] # This is also set in _cb_parseFilterInputs
		for index in range(len(table_filters)):
			new_filter_op_options.append(f'AND GROUP {index+1}')
			new_filter_op_options.append(f'OR GROUP {index+1}')
		new_filter_op_value = 'AND' # We may have destroyed a group that was previously selected, so simply reset to default

	group_index = 0
	# for every filter group
	for filter_group in table_filters:
		group_index += 1

		first_filter_in_group = filter_group[0]
		group_op = first_filter_in_group['op']

		filter_badges = []
		# set first filter (no operator)
		filter_badges.append(dbc.Badge(
			[
				html.Span(first_filter_in_group['field'], className='filter-badge-span-field'),
				html.Span(first_filter_in_group['type'], className='filter-badge-span-type'),
				html.Span(first_filter_in_group['input'], className='filter-badge-span-input'),
				html.Img(
					src=get_asset_url('icons/datapage/filter-close.svg'),
					n_clicks = 0,
					id={'type': 'btn-del-single-filter', 'index': f'{group_index}-0'}
				)
			],
			pill=True,
			color='secondary',
			className='data-filter-badge'
		))

		# set remaining filters (with operator)
		filter_index=0
		for filter in filter_group[1:]:
			filter_index += 1
			filter_badges.append(dbc.Badge(
				[
					html.Span(filter['op'], className='filter-badge-span-op'),
					html.Span(filter['field'], className='filter-badge-span-field'),
					html.Span(filter['type'], className='filter-badge-span-type'),
					html.Span(filter['input'], className='filter-badge-span-input'),
					html.Img(
						src=get_asset_url('icons/datapage/filter-close.svg'),
						n_clicks = 0,
						id={'type': 'btn-del-single-filter', 'index': f'{group_index}-{filter_index}'}
					)
				],
				pill=True,
				color='secondary',
				className='data-filter-badge'
			))

		# create filter box
		new_filter_boxes.append(html.Div([
			# group title
			html.Div([
					html.Div([
						html.Span(
							f'{group_op+" " if group_index!=1 else ""}Group {group_index}',
						),
						html.Img(
							src=get_asset_url('icons/datapage/filter-close.svg'),
							n_clicks = 0,
							id={'type': 'btn-del-group', 'index': f'{group_index}'}
						)
					],className='filter-row-box-header-content')
				], className='filter-row-box-header'
			),
			# all filters
			html.Div(filter_badges, className='filter-group-box')
		],className='filter-row-box'))

	datatable_settings['filters'] = table_filters
	return datatable_settings if _update_table_filters else no_update, new_filter_op_options, new_filter_op_value, new_filter_boxes


@callback(	Output('view-data-table', 'dashGridOptions'),
		Input('data-table-search-input', 'value')
	)
def _cb_searchDataTable(filter_value):
	newFilter = Patch()
	newFilter['quickFilterText'] = filter_value
	return newFilter


def genScanList(scans):
	return html.Div(
		[
			html.Div(
				[
					html.H4(f'{scan["tool"]} {scan["version"]}'),
					html.Div([
						html.Img(src=get_asset_url('icons/host-details/tag.svg'), className='detail-icon', id=f'sd-filename-icon-{scan["sid"]}'),
						html.Span(scan['filename'], className='code-text'),
						dbc.Popover('Filename', target=f'sd-filename-icon-{scan["sid"]}', body=True, trigger='hover', placement='left'),
					]),
					html.Div([
						html.Img(src=get_asset_url('icons/host-details/play-circle.svg'), className='detail-icon', id=f'sd-scanstart-icon-{scan["sid"]}'),
						html.Span(scan['start'], className='code-text'),
						dbc.Popover('Scan started', target=f'sd-scanstart-icon-{scan["sid"]}', body=True, trigger='hover', placement='left'),
					]),
					html.Div([
						html.Img(src=get_asset_url('icons/host-details/stop-circle.svg'), className='detail-icon', id=f'sd-scanstopped-icon-{scan["sid"]}'),
						html.Span(scan['stop'], className='code-text'),
						dbc.Popover('Scan stopped', target=f'sd-scanstopped-icon-{scan["sid"]}', body=True, trigger='hover', placement='left'),
					]),
					html.Div([
						html.Img(src=get_asset_url('icons/host-details/eye.svg'), className='detail-icon', id=f'sd-ports-icon-{scan["sid"]}'),
						dbc.Popover('Ports discovered for this host by this scan', target=f'sd-ports-icon-{scan["sid"]}', body=True, trigger='hover', placement='right'),
						html.Div([dbc.Badge(
                                                                port,
                                                                pill=True,
                                                                color='secondary',
                                                                class_name=f'me-1 port-pill-{"tcp" if "tcp" in port else ("udp" if "udp" in port else "other")}',
                                                        ) for port in (scan['ports'] if len(scan['ports'])>0 else ['-/-'])],
                                                )
					]),
					html.Div([
						html.Img(src=get_asset_url('icons/host-details/trello.svg'), className='detail-icon', id=f'sd-scripts-icon-{scan["sid"]}'),
						dbc.Popover(
							'Scripts executed for this host. If the same script was run again in a more recent scan, it will not be displayed here.',
							target=f'sd-scripts-icon-{scan["sid"]}',
							body=True,
							trigger='hover',
							placement='right'),
						html.Div([dbc.Badge(
                                                                script,
                                                                pill=True,
                                                                color='secondary',
                                                                class_name=f'me-1 sd-script-pill',
                                                        ) for script in (scan['scripts'] if len(scan['scripts'])>0 else ['-/-'])],
                                                )
					]),
					html.Div(
						html.Code(scan['args'] if len(scan['args']) > 0 else '-/-'),
						className='code-box'
					),
				],
				className='hd-sl-row'
			)
			for scan in scans
		],
		className='hd-sl-container'
	)


@callback(	Output('modal-update-tag', 'is_open'),
		Output('tag-click-intent', 'data'),
		Input({'index': 'btn-choose-tag', 'type': ALL}, 'n_clicks'),
		prevent_initial_call=True
	)
def _cb_openUpdateTagModal(n_clicks):
	# Guard to prevent opening on detail rendering
	if not any(n_clicks):
		raise PreventUpdate
	return True, {'hid': int(ctx.triggered_id['type'])}


# Update the serverside (database) with the tag changes
@callback(	Output('trigger-tag-update', 'data'),
		Output('modal-update-tag', 'is_open', allow_duplicate=True),
		Input('btn-confirm-modal-update-tag', 'n_clicks'),
		State('hd-tag-selection', 'value'),
		State('hd-tag-targets', 'value'),
		State('tag-click-intent', 'data'),
		State('view-data-table', 'selectedRows'),
		State('view-data-table', 'rowData'),
		prevent_initial_call=True
	)
def _cb_btnConfirmTagUpdate(confirm_click, tag, target, tag_intent, cur_selected_rows, cur_rows):
	if confirm_click == 0:
		raise PreventUpdate

	hid = tag_intent['hid']

	db_con, db = getDB()

	updated_hids = []
	# This host
	if target == 1:
		db.execute('UPDATE hosts SET tag=? WHERE hid=?', (tag if tag != 'Choose tag' else '', hid))
		updated_hids = [str(hid)]
	# All selected hosts or  All current results
	elif target == 2 or target == 3:
		for row in (cur_selected_rows if target == 2 else cur_rows):
			db.execute('UPDATE hosts SET tag=? WHERE hid=?', (tag if tag != 'Choose tag' else '', row['hid']))
			updated_hids.append(str(row['hid']))

	trigger_tag_update = {
		'targets': updated_hids,
		'tag': tag
	}

	db_con.commit()
	db_con.close()

	return trigger_tag_update, False


@callback(	Output('data-detail-rows', 'children'),
		Input('view-data-table', 'selectedRows'),
		State('host-detail-settings', 'data'),
		#prevent_initial_call=True # An update will be triggered everytime the table is initialized
	)
def _cb_outputSelectedRows(selected_rows, host_detail_settings):

	detail_rows = []

	show_tag = host_detail_settings['show-tags']

	if selected_rows is not None:

		db_con, db = getDB()
		for selected_row in selected_rows:
			# this should always succeed because the row that was fetched must come from the table
			qr = db.execute('SELECT hid, ipv4, ipv6, mac, reason, os_name, os_accuracy, os_family, os_vendor, label, tag FROM hosts WHERE hid=?', (int(selected_row['hid']),)).fetchone()
			hid, ipv4, ipv6, mac, reason, os_name, os_accuracy, os_family, os_vendor, host_label, tag = qr

			ipv4 = NumToIP(ipv4) if ipv4 else '-/-'
			ipv6 = ipv6 or '-/-'
			mac = mac or '-/-'
			reason = reason if len(reason) else '-/-'

			tag = tag if len(tag) > 0 else 'Choose tag'

			os_vendor = f'{os_vendor} - ' if len(os_vendor) else ''
			os_family = f'{os_family} - ' if len(os_family) else ''
			os_name   = f'{os_name} - ' if len(os_name) else ''
			os_string = f'OS: {os_vendor}{os_family}{os_name}'
			if len(os_vendor+os_family+os_name):
				os_string += str(os_accuracy) + '%'
			else:
				os_string += '-/-'

			hostnames = db.execute('SELECT name FROM hostnames WHERE host=?', (hid,)).fetchall()
			hostnames = [hn[0] for hn in hostnames]
			if not len(hostnames):
				hostnames = ['-/-']

			qr = db.execute('SELECT pid, port, protocol, svc_name, svc_info, svc_ssl FROM ports where host=?', (hid,)).fetchall()
			ports = []
			for r in qr:
				qrp = db.execute('SELECT psid, name, output FROM pscripts WHERE port=?', (r[0],)).fetchall()
				ports.append({
					'pid': r[0],
					'port': f'{r[1]}/{r[2]}',
					'svc_name': r[3],
					'svc_info': r[4],
					'svc_ssl': r[5],
					'scripts': [{
						'psid': rp[0],
						'name': rp[1],
						'output': rp[2],
					} for rp in qrp]
				})

			qr = db.execute('SELECT sid, filename, tool, args, version, datetime(start,"unixepoch","localtime"), datetime(stop,"unixepoch","localtime") FROM scans_hosts INNER JOIN scans ON scans_hosts.scan=scans.sid INNER JOIN input_files ON scans.file=input_files.fid WHERE scans_hosts.host=?', (hid,)).fetchall()
			scans = []
			for r in qr:
				# get ports for this host found by this scan
				qrp = db.execute('SELECT p.port, p.protocol FROM ports p INNER JOIN scans_ports sp ON sp.port=p.pid WHERE sp.scan=? AND p.host=?',(r[0],hid)).fetchall()
				# get scripts for this host run by this scan
				qrps = db.execute('SELECT ps.name, p.port, p.protocol FROM pscripts ps INNER JOIN ports p ON ps.port=p.pid WHERE ps.scan=? AND ps.host=?',(r[0],hid)).fetchall()
				scans.append({
					'sid': f'{r[0]}-{hid}', # to make the sid unique to each host we append th hid
					'filename': r[1],
					'tool': r[2],
					'args': r[3],
					'version': r[4],
					'start': r[5],
					'stop': r[6],
					'ports': [str(p[0])+'/'+p[1] for p in qrp],
					'scripts': [f'{ps[0]} for {ps[1]}/{ps[2]}' for ps in qrps],
				})

			detail_rows.append(html.Div([
				html.Div(
					tag,
					className='hd-ribbon hd-ribbon-color',
					n_clicks=0,
					id={'index': 'btn-choose-tag', 'type': f'{hid}'},
					style={
						'display': 'block' if show_tag else 'none',
						'background': TagRibbons.map[tag]['css-color']
					}
				),
				html.Div([
					html.Div([
						html.Span([
							html.H3(host_label),
							html.Span(os_string, className='hd-os-label'),
						], className='hd-label-header'),
						html.Div([
							html.Div([
								html.Div([
									html.Span('IPv4: ', className='hd-id-label'),
									html.Span(ipv4),
								]),
								html.Div([
									html.Span('Mac: ', className='hd-id-label'),
									html.Span(mac),
								]),
								html.Div([
									html.Span('Up reason: ', className='hd-id-label'),
									html.Span(reason),
								]),
							], className='hd-label-card-col'),
							html.Div([
								html.Div([
									html.Span('IPv6: ', className='hd-id-label'),
									html.Span(ipv6),
								]),
								html.Div([
									html.Span('Hostname: ', className='hd-id-label'),
									html.Span(", ".join(name for name in hostnames)),
								]),
							], className='hd-label-card-col'),
						], className='hd-label-card-identifiers'),
					], className='hd-card hd-label-card'),
					html.Div([
						html.H1(str(len(ports))),
						html.Span('open ports', className='hd-id-label')
					], className='hd-card hd-port-stat-card'),
				], className='hd-grid-row'),
				dbc.Accordion([
						dbc.AccordionItem(
							genScanList(scans),
							title=[html.Span(f'Scans related to {host_label}', className='hd-port-scans-label')]
						)
					]+[
					dbc.AccordionItem(
						[
							html.Div([
								html.Div([
									html.Img(src=get_asset_url('icons/host-details/box.svg'), className='detail-icon', id=f'pd-port-icon-{port["pid"]}'),
									html.Span(port['port']),
									dbc.Popover('Port & protocol', target=f'pd-port-icon-{port["pid"]}', body=True, trigger='hover', placement='top'),

								], className='hd-p-detail-card'),
								html.Div([
									html.Img(src=get_asset_url('icons/host-details/tool.svg'), className='detail-icon', id=f'pd-svc-icon-{port["pid"]}'),
									html.Span(port['svc_name'] if len(port['svc_name']) else '-/-'),
									dbc.Popover('Service', target=f'pd-svc-icon-{port["pid"]}', body=True, trigger='hover', placement='top'),
								], className='hd-p-detail-card'),
								html.Div([
									html.Img(src=get_asset_url('icons/host-details/shield.svg'), className='detail-icon', id=f'pd-ssl-icon-{port["pid"]}'),
									html.Span(port['svc_ssl'] if len(port['svc_ssl']) else '-/-'),
									dbc.Popover('SSL', target=f'pd-ssl-icon-{port["pid"]}', body=True, trigger='hover', placement='top'),
								], className='hd-p-detail-card'),
								html.Div([
									html.Img(src=get_asset_url('icons/host-details/activity.svg'), className='detail-icon', id=f'pd-svcinfo-icon-{port["pid"]}'),
									html.Span(port['svc_info'] if len(port['svc_info']) else '-/-'),
									dbc.Popover('Service info', target=f'pd-svcinfo-icon-{port["pid"]}', body=True, trigger='hover', placement='top'),
								], className='hd-p-detail-card-last'),
							], className='hd-p-detail-container'),

							html.Div(
								[
									html.Div([
										html.Div([
											html.Img(src=get_asset_url('icons/host-details/tag.svg'), className='detail-icon', id=f'pd-scriptname-icon-{script["psid"]}'),
											html.Span(script['name'], className='code-text'),
											dbc.Popover('Script name', target=f'pd-scriptname-icon-{script["psid"]}', body=True, trigger='hover', placement='left'),
										]),
										html.Div(
											html.Code(script['output']),
											className='code-box'
										),
									], className='hd-script-row')
									for script in port['scripts']
								],
								className='hd-sl-container'
							),
						],
						title=[
							html.Span(port['port'],	className='hd-port-row-id'),
							html.Span(
								[
									port['svc_name'] if len(port['svc_name']) else '',
									dbc.Badge(
										str(len(port['scripts'])),
										color='transparent',
										pill=True,
										text_color='white',
										className='hd-port-scriptcount-badge',
									) if len(port['scripts']) > 0 else None,

								],
								className='hd-port-svc-label'
							)
						],
					) for port in ports
				],
				flush=True,
				always_open=True,
				active_item=[]),
			], className='hd-container'))

		db_con.close()


	if not len(detail_rows):
		detail_rows.append(html.Div([
			html.Div([
				html.Div([
					html.Span([
						html.H3('-/-'),
						html.Span('Select a host in the table to view details.', className='hd-os-label'),
					], className='hd-label-header'),
					html.Div([
						html.Div([
							html.Div([
								html.Span('IPv4: ', className='hd-id-label'),
								html.Span('-/-'),
							]),
							html.Div([
								html.Span('Mac: ', className='hd-id-label'),
								html.Span('-/-'),
							]),
							html.Div([
								html.Span('Up reason: ', className='hd-id-label'),
								html.Span('-/-'),
							]),
						], className='hd-label-card-col'),
						html.Div([
							html.Div([
								html.Span('IPv6: ', className='hd-id-label'),
								html.Span('-/-'),
							]),
							html.Div([
								html.Span('Hostname: ', className='hd-id-label'),
								html.Span('-/-'),
							]),
						], className='hd-label-card-col'),
					], className='hd-label-card-identifiers'),
				], className='hd-card hd-label-card'),
				html.Div([
					html.H1('-'),
					html.Span('open ports', className='hd-id-label')
				], className='hd-card hd-port-stat-card'),
			], className='hd-grid-row'),
		], className='hd-container'))

	return detail_rows



@callback(	Output('view-data-table', 'rowData'),
		Output('div-toaster', 'children', allow_duplicate=True),
		Output('result-counter', 'children'),
		Output('result-counter-pb', 'value'),
		Input('datatable-settings', 'data'),
		Input('view-data-table', 'dashGridOptions'), # pseudo input to guarantee initial call because table_filters may not update initially
		State('div-toaster', 'children'),
		prevent_initial_call=True
	)
def _cb_updateResultsTable(datatable_settings, _, toasts):

	inp_filters = datatable_settings['filters']

	result_rows=[]
	db_con, db = getDB()

	# Sanity check:
	for g in inp_filters:
		for f in g:
			if f['field'] not in DataFilterMap.fields:
				toasts.append(CustomToast(
					[
						f'The field value is invalid.'
					],
					headerText='Invalid filter',
					level='error',
					duration=8000
				))
				return [], toasts, '', 0

	dfm = DataFilterMap()
	query, query_params = dfm.buildSQLQuery(inp_filters)

	# The default limit should be 32766 but...
	# https://www.sqlite.org/limits.html#max_variable_number
	if (lqp:=len(query_params)) > 50:
		toasts.append(CustomToast(
			[
				f'What on earth are you trying to do? Sorry, {lqp} parameters is too much. Reduce your query.'
			],
			headerText='Max amount of filters exceeded',
			level='error',
			duration=8000
		))
		return [], toasts, '', 0

	# The final query will join all information on the hosts, so we got every host with every detail as a single row
	qr = db.execute(query, query_params).fetchall()

	for host_result in qr:
		# in the datatable we don't use the os_family or the label
		# but the graph uses the same query and needs the family (this is more readable than managing two giant queries)
		hid, os_name, _, _, ipv4, ipv6, mac, names, ports, tools, tag, _, _ = host_result
		# tools can be listed redundantly, so use a set to get unique values (DISTINCT would fail on edge cases due to multiple GROUP BY)
		tools = ', '.join(set(tools.split(',')))
		names = names.replace(',', ', ') if names else ''
		result_rows.append(dict(
			os=os_name,
                        ipv4=NumToIP(ipv4 or -1),
                        ipv6=ipv6 or '',
                        mac=mac or '',
                        hostname=names or '',
                        ports=ports or '',
                        scans=tools,
                        tag=tag,
                        hid=hid
		))

	max_hosts = db.execute('SELECT COUNT() FROM hosts').fetchone()[0]
	host_count = len(result_rows)

	db_con.close()
	return result_rows, toasts, str(host_count), int(host_count*100/max_hosts) if max_hosts > 0 else 0


