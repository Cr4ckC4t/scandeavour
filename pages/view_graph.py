from dash import html, dcc, callback, Input, Output, State, register_page, get_asset_url, ctx, no_update, ALL, Patch
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from components.customToast import CustomToast
from utils import getDB, NodeHistory, NumToIP, IPtoNum, CIDRtoFirstLast, validateIP, getOS, DataFilterMap

register_page(__name__, path='/graph')

def layout(**kwargs):
	graph_stylesheet = [
		# Activity
		{
			'selector': ':selected',
			'style': {
				'border-width': '3px',
				'border-color': '#fff',
			}
		},
		# Groups
		{
			'selector': 'label',
			'style': {
				'content': 'data(label)',
				'color': '#00FFE0'
			}
		},
		{
			'selector': 'node',
			'style': {
				'background-opacity': '0',
			}
		},
		{
			'selector': 'edge',
			'style': {
				'curve-style': 'straight-triangle'
			}
		},
		# Classes
		{
			'selector': '.scan',
			'style': {
				'shape': 'round-rectangle',
				'background-opacity': '0.2',
				'background-color': 'black',
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=command
				'background-image': get_asset_url('icons/graphpage/terminal.svg')
			}
		},
		{
			# Options taken from: https://github.com/nmap/nmap/blob/fef9f592b067e53c58c5c593e8916cd83e4bb873/zenmap/zenmapGUI/Icons.py#L80
			'selector': '.linuxhost',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				# & boxy-svg.com
				'background-image': get_asset_url('icons/hosts/host-linux.svg')
			}
		},
		{
			'selector': '.windowshost',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				# & boxy-svg.com
				'background-image': get_asset_url('icons/hosts/host-windows.svg')
			}
		},
		{
			'selector': '.applehost',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				# & boxy-svg.com
				'background-image': get_asset_url('icons/hosts/host-apple.svg')
			}
		},
		{
			'selector': '.redhathost',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				# & boxy-svg.com
				'background-image': get_asset_url('icons/hosts/host-redhat.svg')
			}
		},
		{
			'selector': '.ubuntuhost',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				# & boxy-svg.com
				'background-image': get_asset_url('icons/hosts/host-ubuntu.svg')
			}
		},
		{
			'selector': '.freebsdhost',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				# & boxy-svg.com
				'background-image': get_asset_url('icons/hosts/host-freebsd.svg')
			}
		},
		{
			'selector': '.openbsdhost',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				# & boxy-svg.com
				'background-image': get_asset_url('icons/hosts/host-openbsd.svg')
			}
		},
		{
			'selector': '.solarishost',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				# & boxy-svg.com
				'background-image': get_asset_url('icons/hosts/host-solaris.svg')
			}
		},
		{
			'selector': '.host',
			'style': {
				'width': 70,
				'height': 70,
				# https://feathericons.com/?query=monitor
				'background-image': get_asset_url('icons/graphpage/host.svg'),
			}
		},
		{
			'selector': '.port',
			'style': {
				# https://feathericons.com/?query=box
				'width': 30,
				'height': 30,
				'background-image': get_asset_url('icons/graphpage/box.svg'),
			}
		}
	]

	return html.Div([
		dcc.Store('graph-settings', data={
	                        'scans-visible': True,
	                        'ports-visible': True,
	                        'hostsnp-visible': True,
	                        'datafilter-linked': True,
	                        'filters': {
	                                'subnets': [],
					'datatable': []
	                        },
	                        'max_elements_render': 512,
			}, storage_type='session'),
		dcc.Store('render-trigger', data={
				'trigger': False
			}, storage_type='memory'),
		dcc.Store('click-intent', data={
				'id': ''
			}, storage_type='memory'),
		dcc.Store('node-nav-state', data={
				'history': [],
				'index': -1,
				'jumptable': {},
			}, storage_type='session'),
		cyto.Cytoscape(
			id='scan-graph',
			# Default to very responsive draggable layout for small datasets
			layout = {
				'name': 'cola',
				'animate': True,
				'refresh': 1,
				'avoidOverlap': True,
				'infinite': True,
				'fit': False,
				'nodeDimensionsIncludeLabels': True
			},
			stylesheet=graph_stylesheet,
			style={
				'width':'100%',
				'height': '100vh',
			},
			elements=[],
			responsive=True,
			zoomingEnabled=True,
			zoom=2,
			wheelSensitivity=0.4,
		),
		html.Div([
			html.Div(
				[
					html.Img(
						src=get_asset_url('icons/graphpage/maximize.svg'),
					),
					# Currently, Popovers generate a React warning in the console when we hover over the target the first time after ctrl+f5
					dbc.Popover(
						'Fit view',
						target='btn-fit-graph-view',
						body=True,
						trigger="hover",
					),
				],
				className='graph-overlay-item',
				id='btn-fit-graph-view',
				n_clicks=0,
			),
			html.Div(
				[
					html.Img(
						src=get_asset_url('icons/graphpage/crosshair.svg'),
					),
					dbc.Popover(
						'Center on node',
						target='btn-center-selected-node',
						body=True,
						trigger="hover",
					),
				],
				className='graph-overlay-item',
				id='btn-center-selected-node',
				n_clicks=0,
			),
			html.Div(
				[
					html.Img(
						src=get_asset_url('icons/graphpage/terminal-on.svg'),
						id='toggle-scans-img'
					),
					dbc.Popover(
						'Hide scans',
						target='btn-toggle-scans',
						body=True,
						trigger="hover",
						id='btn-toggle-scans-label',
					),
				],
				className='graph-overlay-item',
				id="btn-toggle-scans",
				n_clicks=0,
			),
			html.Div(
				[
					html.Img(
						src=get_asset_url('icons/graphpage/box-on.svg'),
						id='toggle-ports-img'
					),
					dbc.Popover(
						'Hide ports',
						target='btn-toggle-ports',
						body=True,
						trigger="hover",
						id='btn-toggle-ports-label',
					),
				],
				className='graph-overlay-item',
				id="btn-toggle-ports",
				n_clicks=0,
			),
			html.Div(
				[
					html.Img(
						src=get_asset_url('icons/graphpage/host-on.svg'),
						id='toggle-hosts-img'
					),
					dbc.Popover(
						'Hide hosts with no ports',
						target='btn-toggle-hosts',
						body=True,
						trigger="hover",
						id='btn-toggle-hosts-label',
					),
				],
				className='graph-overlay-item',
				id="btn-toggle-hosts",
				n_clicks=0,
			),
			html.Div(
				[
					html.Img(
						src=get_asset_url('icons/graphpage/datafilter-on.svg'),
						id='toggle-datafilter-img'
					),
					dbc.Popover(
						'Ignore filters from the data view',
						target='btn-toggle-datafilter',
						body=True,
						trigger="hover",
						id='btn-toggle-datafilter-label',
					),
				],
				className='graph-overlay-item',
				id="btn-toggle-datafilter",
				n_clicks=0,
			),
		],
		className='graph-overlay-bl'
		),
		dbc.Offcanvas(
			[],
			id="node-info-canvas",
			title="",
			placement='end',
			backdrop=False,
			is_open=False,
			class_name='node-info-canvas',
			style={'borderLeft': 'none'}
		),
		# Search form
		html.Div([
			html.Img(src=get_asset_url('icons/graphpage/filter.svg')),
			html.Div(dcc.Input(
				value='',
				placeholder='🔎 IP or CIDR',
				type='text',
				pattern=r'^([1-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])(\.([0-9]|([1-9][0-9])|(1[0-9][0-9])|(2[0-4][0-9])|25[0-5])){3}($|\/([1-9]|[1-2][0-9]|3[0-2])$)',
				id='subnet-filter-input',
				className='subnet-filter-input',
				debounce=True
			), id='filter-input-wrapper'),
			html.Div([], id='subnet-filter-badges', className='subnet-filter-badges'),
		], className='graph-search-menu'),
		html.Div([
			html.Div([
				html.Div([
					html.Span('0', id='ge-counter-edges', className='ge-counter-side'),
					html.Span(' edges', className='ge-counter-label ge-counter-side')
				]),
				html.Div([
					html.Span('{ ', className='ge-counter-label'),
					html.Span('0', id='ge-counter-eles'),
					html.Span(' }', className='ge-counter-label'),
#					html.Span(' elements', className='ge-counter-label')
				]),
				html.Div([
					html.Span('0', id='ge-counter-nodes', className='ge-counter-side'),
					html.Span(' nodes', className='ge-counter-label ge-counter-side')
				]),
			], className='ge-counter-flex')
		], className='graph-element-counter-container')
	],
	className='graph-container')


@callback(	Output('graph-settings', 'data', allow_duplicate=True),
		Output('subnet-filter-input', 'value'),
		Output('div-toaster', 'children', allow_duplicate=True),
		Input('subnet-filter-input', 'value'),
		State('graph-settings', 'data'),
		State('div-toaster', 'children'),
		prevent_initial_call=True
	)
def _cb_subnetFilterInput(value, graph_settings, toasts):
	if value is not None and value != '':
		if validateIP(value):
			if value in graph_settings['filters']['subnets']:
				toasts.append(CustomToast(
					[
						'Filter already applied.'
					],
					headerText='Filter invalid',
					level='warning'
				))
				return no_update, '', toasts

			graph_settings['filters']['subnets'].append(value)
			return graph_settings, '', no_update
		else:
			toasts.append(CustomToast(
				[
					'Invalid CIDR notation.'
				],
				headerText='Filter invalid',
				level='warning'
			))
			return no_update, no_update, toasts
	return no_update, no_update, no_update


@callback(	Output('graph-settings', 'data', allow_duplicate=True),
		Output('node-info-canvas', 'is_open', allow_duplicate=True),
		Input({'type': 'btn-del-filter', 'index': ALL}, 'n_clicks'),
		State('graph-settings', 'data'),
		prevent_initial_call=True
	)
def _cb_deleteInputFilter(btn, graph_settings):
	if any(btn):
		id = ctx.triggered_id['index']
		graph_settings['filters']['subnets'].pop(graph_settings['filters']['subnets'].index(id))
		return graph_settings, False
	return no_update, no_update


@callback(	Output('subnet-filter-badges', 'children'),
		Input('graph-settings', 'data')
	)
def _cb_updateSubnetBadges(graph_settings):
	return [
		dbc.Badge([
			html.Span(
				subnet,
				style={'marginRight': '0.5rem'},
				className = 'filter-badge-span'
			),
			html.Img(
				src=get_asset_url('icons/graphpage/trash.svg'),
				width=24,
				height=24,
				id={'type': 'btn-del-filter', 'index': subnet},
				className = 'filter-badge-trash-icon'
			)],
			pill=True,
			color='secondary',
			class_name='filter-badge'
		)
	for subnet in graph_settings['filters']['subnets']]


@callback(	Output('scan-graph', 'elements'),
		Output('div-toaster', 'children', allow_duplicate=True),
		Output('render-trigger', 'data'),
		Output('ge-counter-edges', 'children'),
		Output('ge-counter-eles', 'children'),
		Output('ge-counter-nodes', 'children'),
		Input('graph-settings', 'data'),
		State('div-toaster', 'children'),
		prevent_initial_call=True
	)
def _cb_redrawGraph(graph_settings, toasts):
	subnet_filter = graph_settings['filters']['subnets']

	# populate the input filters with the datable filters
	# this will be empty, unless the user wants to enable the datapage filters in the graph
	inp_filters = graph_settings['filters']['datatable']

	viewScans = graph_settings['scans-visible']
	viewPorts = graph_settings['ports-visible']
	viewHostsNP = graph_settings['hostsnp-visible'] # hosts with no ports

	# Retrieve hosts

	# if the user added subnet filters, these must be added as filters as well
	if len(subnet_filter) > 0:
		# we add an AND NEW GROUP filter (so a list) to make sure this condition is met for all results
		new_filter_group = []
		for ix in range(len(subnet_filter)):
			if not validateIP(subnet_filter[ix]):
				# This can never happen via GUI but just in case..
				continue
			new_filter_group.append({
				'op': 'AND' if ix==0 else 'OR', # only the group gets an "AND" the unique filters get an OR
				'field': 'host.ipv4',
				'type': 'in subnet' if '/' in subnet_filter [ix] else 'is', # either for subnet or single IP
				'input': subnet_filter[ix] # the query parser will do the processing for us
			})
		inp_filters.append(new_filter_group)

	if not viewHostsNP:
		# we add an AND NEW GROUP filter (same reason as for the subnet filter)
		inp_filters.append([{
			'op': 'AND',
			'field': 'host.portcount',
			'type': 'greater than',
			'input': '0'
		}])

	dfm = DataFilterMap()
	query, query_params = dfm.buildSQLQuery(inp_filters)

	filter_active = len(query_params) > 0

	eles = []
	edge_counter = 0
	node_counter = 0

	db_con, db = getDB()

	# Not using fetchall here should improve performance
	# otherwise all hosts would be copied into a list in memory before being processed
	qr = db.execute(query, query_params)
	relevant_hosts = []

	relevant_sids = []
	relevant_pids = []

	for host in qr:
		# since we use the big query, we don't need every column, only enough to create the node
		hid, os_name, os_family, hostLabel, _, _, _, _, _, _, _, _, h_sids, h_pids  = host

		relevant_hosts.append(hid)

		# add scans that weren't stored already to the relevant sids
		for h_sid in h_sids.split(','):
			if h_sid not in relevant_sids:
				relevant_sids.append(int(h_sid))

		# a host may not have any open ports so h_pids may be None
		# add all ports relevant to this host to the relevant ports
		# ports are always unique to a host so we don't need to check if they were added already
		if h_pids:
			for h_pid in h_pids.split(','):
				relevant_pids.append(int(h_pid))

		os = getOS(os_family, os_name)

		eles.append({
			'data': {'id': f'host-{hid}', 'label': hostLabel},
			'classes': f'{os}host',
		})
		node_counter += 1

	if len(relevant_hosts) == 0:
		toasts.append(CustomToast(
			[
				'Try removing a filter.' if filter_active else 'Import a scan first.'
			],
			headerText='No hosts available',
			level='warning'
	        ))
		db_con.close()
		return eles, toasts, no_update, 0, 0, 0

	# Retrieve relevant scans (and edges)
	if viewScans:
		sid_list=[]
		qr = db.execute('SELECT s.sid, s.tool, sh.host FROM scans s INNER JOIN scans_hosts sh ON s.sid == sh.scan')
		for scan in qr:
			sid, tool, hid = scan

			if sid not in relevant_sids:
				continue

			# add scan node if it doesn't exist yet
			if sid not in sid_list:
				sid_list.append(sid)
				eles.append({
					'data': {'id': f'scan-{sid}', 'label': tool},
					'classes': 'scan'
				})
				node_counter += 1

			# add an edge for every host id
			# I believe filtering items in memory should be more efficient than a SQL query for every host
			if hid in relevant_hosts:
				eles.append({
					'data': {'source': f'scan-{sid}', 'target': f'host-{hid}', 'id': f'scan-edge-{sid}-{hid}', 'label': ''}
				})
				edge_counter += 1

	# Retrieve relevant ports
	if viewPorts:
		qr = db.execute('SELECT pid, port, protocol, host FROM ports')
		for port in qr:
			pid, portnumber, protocol, hid = port

			if pid not in relevant_pids:
				continue

			# Filter out irrelevant hosts
			if hid in relevant_hosts:
				eles.append({
					'data': {'id': f'port-{pid}', 'label': f'{portnumber}/{protocol}'},
					'classes': 'port'
				})
				node_counter += 1
				# Retrieve the relevant edges
				eles.append({
					'data': {'source': f'host-{hid}', 'target': f'port-{pid}', 'id': f'host-edge-{hid}-{pid}', 'label': ''}
				})
				edge_counter += 1

	db_con.close()

	ele_counter = node_counter + edge_counter

	if ele_counter > graph_settings['max_elements_render']:
		eles = []
		toasts.append(CustomToast(
			[
				f'You want to render too much data at once. The current limit is {graph_settings["max_elements_render"]} nodes & edges. Try a node filter (top left) or display filter (bottom left) to decrease the amount of nodes and edges.'
			],
			headerText=f'Layout warning ({ele_counter} elements)',
			level='warning',
			duration=15000
		))

	# return the counters regardless of whether we set the eles to []
	# this is because the user should know how many edges/nodes the query returned
	return eles, toasts, {'trigger': True}, edge_counter, ele_counter, node_counter


@callback(	Output('node-info-canvas', 'is_open'),
		Output('node-info-canvas', 'title'),
		Output('node-info-canvas', 'children'),
		Output('node-nav-state', 'data'),
		Output('scan-graph', 'elements', allow_duplicate=True),
		Input('scan-graph', 'tapNodeData'),
		Input({'type': 'btn-node-nav', 'index': ALL }, 'n_clicks'), # Input for dynamic nav (< & >) button that does not exist the first time
		Input({'type': 'btn-node-jump', 'index': ALL }, 'n_clicks'), # Input for dynamic jump buttons that does not exist the first time
		State('node-nav-state', 'data'),
		State('scan-graph', 'elements'),
		prevent_initial_call=True
	)
def _cb_selectNode(data, nav_clicks, jump_clicks, node_nav_state, node_elements):

	node_history = NodeHistory(node_nav_state)

	# When the nav menu was used instead of a click on a node
	_nav_prev = ctx.triggered_id=={'type': 'btn-node-nav', 'index': 'prev'} and nav_clicks[0]
	_nav_next = ctx.triggered_id=={'type': 'btn-node-nav', 'index': 'next'} and nav_clicks[1]
	_nav = _nav_prev or _nav_next

	_jumped = False
	if 'type' in ctx.triggered_id and 'index' in ctx.triggered_id and ctx.triggered_id['type'] == 'btn-node-jump':
		_jumped = True
		# If we did a jump from a position that was not the latest, add that position to latest again
		# so on moving back, we get to that node again - and not the current latest.
		if node_history.next_enabled():
			node_history.re_add_current()

	if _nav_prev:
		data = node_history.nav_previous()
	elif _nav_next:
		data = node_history.nav_next()
	elif _jumped:
		data = node_history.jump_to(ctx.triggered_id['index'])

	if data:
		db_con, db = getDB()

		patched_nodes = Patch()
		# Make sure only the active node is selected
		for index,element in enumerate(node_elements):
			patched_nodes[index]['selected'] = element['data']['id']==data['id']

		# If the node was clicked on in the graph or jumped to, then add it to the history
		if not _nav:
			node_history.add_node(data)

		node_type, node_id = data['id'].split('-') # the unused value is the unique identifier of each node
		node_label = data['label']

		# The label may update for hosts over time, so a history state may contain an outdated label value
		# That's why we need to update it when we display it coming from a nav
		# On clicks and jumps we can be sure that the label comes fresh from the database
		if node_type == 'host' and _nav:
			node_label = db.execute('SELECT label FROM hosts WHERE hid=?', (node_id,)).fetchone()[0]

		title_text = ''
		title_icon = ''
		match node_type:
			case 'host':
				title_text = f'{node_label}'
				title_icon = 'icons/graphpage/host.svg'
			case 'scan':
				title_text = f'{node_label} Scan'
				title_icon = 'icons/graphpage/terminal.svg'
			case 'port':
				title_text = f'Port {node_label}'
				title_icon = 'icons/graphpage/box.svg'
			case _:
				print(f'An unknown node type was selected: {data}')
				return False, no_update, no_update, no_update, no_update

		title = html.Div([
			html.Img(
				src=get_asset_url(title_icon),
				width=32,
				height=32,
				id='node-info-title-icon'
			),
			html.Span(
				title_text,
				style={'marginLeft': '0.5rem'}
			),
		])

		eles = []

		# Get node details from the database and build the node info panel

		if node_type == 'scan':
			sid = node_id
			sfid, stool, sargs, sversion, sstart, sstop, shosts, sup = db.execute('SELECT file, tool, args, version, datetime(start,"unixepoch"), datetime(stop,"unixepoch"), hostsScanned, hostsUp FROM scans WHERE sid=?', (sid,)).fetchone()

			sfilename = db.execute('SELECT filename FROM input_files WHERE fid=?', (sfid,)).fetchone()

			eles.append(dbc.ListGroup([
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/git-branch.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Tool version:',
							className='node-li-key'
						),
						html.Div(html.Span(
							f'{stool} {sversion}',
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/list.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Scan details:',
							className='node-li-key'
						),html.Div(html.Span(
							sargs,
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/file-text.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Filename:',
							className='node-li-key'
						),
						html.Div(html.Span(
							sfilename,
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/play-circle.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Scan started:',
							className='node-li-key'
						),
						html.Div(html.Span(
							f'{sstart}',
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/stop-circle.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Scan stopped:',
							className='node-li-key'
						),
						html.Div(html.Span(
							f'{sstop}',
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/pie-chart.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Hosts:',
							className='node-li-key'
						),
						html.Div(html.Span(
							f'{shosts} scanned, {sup} up',
							className='node-li-value',
						))
					]),
				],
				flush=True
			))
		if node_type == 'host':
			hid = node_id
			hipv4, hipv6, hmac, hreason, hos_name, hos_acc, hos_fam, hos_vendor, htag = db.execute('SELECT ipv4, ipv6, mac, reason, os_name, os_accuracy, os_family, os_vendor, tag FROM hosts WHERE hid=?', (hid,)).fetchone()
			hipv4 = hipv4 or -1
			hipv6 = hipv6 or ''
			hmac = hmac or ''
			hipv4 		= NumToIP(hipv4)
			hnames 		= [hn[0] for hn in db.execute('SELECT name FROM hostnames WHERE host=?', (hid,))]
			hos_acc 	= f' ({hos_acc:02}%)' if hos_acc>0 else ''
			hos_fam 	= f' {hos_fam}' if len(hos_fam) else ''
			hos_vendor 	= f' {hos_vendor}' if len(hos_vendor) else ''
			hos_name 	= hos_name+hos_fam+hos_vendor+hos_acc

			tools = db.execute('SELECT s.sid, tool FROM scans_hosts sh INNER JOIN scans s ON (sh.scan == s.sid) WHERE sh.host=?', (hid,)).fetchall()
			for tool in tools:
				sid, toolname = tool
				# generate a jump id like "Nmap-<sid>"
				node_history.add_jump(f'{toolname}-{sid}', {'id': f'scan-{sid}', 'label': f'{toolname}'})


			hports = db.execute('SELECT pid, port, protocol FROM ports WHERE host=?', (hid,)).fetchall()
			for hport in hports:
				# generate a jump id like "Port-<pid>"
				pid, port, protocol = hport
				node_history.add_jump(f'Port-{pid}', {'id': f'port-{pid}', 'label': f'{port}/{protocol}'})


			eles.append(dbc.ListGroup([
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/link.svg'),
							className='node-li-icon'
						),
						html.Span(
							'IPv4 address:',
							className='node-li-key'
						),
						html.Div(html.Span(
							hipv4,
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/link.svg'),
							className='node-li-icon'
						),
						html.Span(
							'IPv6 address:',
							className='node-li-key'
						),
						html.Div(html.Span(
							hipv6,
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/link.svg'),
							className='node-li-icon'
						),
						html.Span(
							'MAC address:',
							className='node-li-key'
						),
						html.Div(html.Span(
							hmac,
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/home.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Hostname:',
							className='node-li-key'
						),
						html.Div(html.Span(
							', '.join(hnames),
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/bookmark.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Tag:',
							className='node-li-key'
						),
						html.Div(html.Span(
							htag,
							className='node-li-value',
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/compass.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Up reason:',
							className='node-li-key'
						),
						html.Div(html.Span(
							hreason,
							className='node-li-value'
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/cpu.svg'),
							className='node-li-icon'
						),
						html.Span(
							'OS:',
							className='node-li-key'
						),
						html.Div(html.Span(
							hos_name,
							className='node-li-value'
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/graphpage/terminal.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Found by:',
							className='node-li-key'
						),
						html.Div([ dbc.Badge(
								f'{tool[1]} ({tool[0]})',
								pill=True,
								color='secondary',
								class_name='me-1 selectable-node-badge',
								id={'type': 'btn-node-jump', 'index': f'{tool[1]}-{tool[0]}'},
							) for tool in tools],
							className='node-li-value'
						)
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/graphpage/box.svg'),
							className='node-li-icon'
						),
						html.Span(
							f'Open ports ({len(hports)}):',
							className='node-li-key'
						),
						html.Div([ dbc.Badge(
								f'{hport[1]}/{hport[2]}',
								pill=True,
								color='secondary',
								class_name='me-1 selectable-node-badge',
								id={'type': 'btn-node-jump', 'index': f'Port-{hport[0]}'},
							) for hport in hports],
							className='node-li-value'
						)
					]),
				],
				flush=True
			))
		if node_type == 'port':
			pid = node_id
			hid, svc_name, svc_info, port, protocol = db.execute('SELECT host, svc_name, svc_info, port, protocol FROM ports WHERE pid=?', (pid,)).fetchone()
			hostlabel = db.execute('SELECT label FROM hosts WHERE hid=?', (hid,)).fetchone()[0]

			node_history.add_jump(f'Host-{hid}', {'id': f'host-{hid}', 'label': hostlabel}) # Jump ID for the host
			tools = db.execute('SELECT sid, tool FROM ports p LEFT JOIN scans_ports sp ON (p.pid=sp.port) LEFT JOIN scans s ON (sp.scan=s.sid) WHERE pid=?', (pid,)).fetchall()
			for tool in tools:
				sid, toolname = tool
				# generate a jump id like "Nmap-<sid>"
				node_history.add_jump(f'{toolname}-{sid}', {'id': f'scan-{sid}', 'label': f'{toolname}'})

			n_hosts = db.execute('SELECT COUNT(host) FROM ports WHERE port=? AND protocol=? AND host!=?', (port, protocol,hid)).fetchone()[0]

			qr = db.execute('SELECT name FROM pscripts WHERE host=? AND port=?', (hid,pid)).fetchall()
			script_names = ', '.join([name[0] for name in qr])

			eles.append(dbc.ListGroup([
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/graphpage/host.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Host:',
							className='node-li-key'
						),
						html.Div(html.Span(
							hostlabel,
							className='node-li-value span-link',
							id={'type': 'btn-node-jump', 'index': f'Host-{hid}'},
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/tool.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Service:',
							className='node-li-key'
						),
						html.Div(html.Span(
							svc_name,
							className='node-li-value'
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/activity.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Service info:',
							className='node-li-key'
						),
						html.Div(html.Span(
							svc_info,
							className='node-li-value'
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/trello.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Available script results:',
							className='node-li-key'
						),
						html.Div(html.Span(
							script_names,
							className='node-li-value'
						))
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/graphpage/terminal.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Found by:',
							className='node-li-key'
						),
						html.Div([ dbc.Badge(
								f'{tool[1]} ({tool[0]})',
								pill=True,
								color='secondary',
								class_name='me-1 selectable-node-badge',
								id={'type': 'btn-node-jump', 'index': f'{tool[1]}-{tool[0]}'},
							) for tool in tools],
							className='node-li-value'
						)
					]),
					dbc.ListGroupItem([
						html.Img(
							src=get_asset_url('icons/node-info/repeat.svg'),
							className='node-li-icon'
						),
						html.Span(
							'Also found on:',
							className='node-li-key'
						),
						html.Div(html.Span(
							f'{n_hosts} other host{"s" if n_hosts!=1 else ""}',
							className='node-li-value'
						))
					]),
				],
				flush=True
			))

		eles.append(html.Hr())
		eles.append(html.Div([
			dbc.Button([
					html.Img(
						src=get_asset_url('icons/node-info/chevron-left.svg'),
					),
				],
				disabled=not node_history.prev_enabled(),
				color='dark',
				class_name='node-info-nav-btn',
				id={'type': 'btn-node-nav', 'index': 'prev'},
				n_clicks=0,
			),
			dbc.Button([
					html.Img(
						src=get_asset_url('icons/node-info/chevron-right.svg'),
					),
				],
				disabled=not node_history.next_enabled(),
				color='dark',
				class_name='node-info-nav-btn',
				id={'type': 'btn-node-nav', 'index': 'next'},
				n_clicks=0,
			)
		], className='node-info-nav-container'))

		db_con.close()

		return True, title, eles, node_history.get(), patched_nodes
	return False, no_update, no_update, no_update, no_update
