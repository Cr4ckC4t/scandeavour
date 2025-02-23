from dash import html, callback, Output, Input, State, dcc, register_page, get_asset_url, ctx
from dash.exceptions import PreventUpdate
import plotly.graph_objects as go
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from scandeavour.utils import getDB
from scandeavour.components.customToast import CustomToast

register_page(__name__, path='/stats')

def layout(**kwargs):
	db_con, db = getDB()

	default_value = '-/-'

	# Get total ports count
	total_ports = 0
	qr = db.execute('SELECT COUNT(port||protocol) AS cnt FROM ports').fetchone()
	if qr is not None:
		total_ports = qr[0]

	# Get most common ports
	qr = db.execute('SELECT port || "/" || protocol, COUNT(*) AS cnt FROM ports GROUP BY port||protocol ORDER BY cnt DESC LIMIT 4').fetchall()

	most_common_ports = [
		{ 'port': default_value, 'count': 0 },
		{ 'port': default_value, 'count': 0 },
		{ 'port': default_value, 'count': 0 },
		{ 'port': default_value, 'count': 0 },
	]
	i = 0
	for r in qr:
		most_common_ports[i]['port'] = r[0]
		most_common_ports[i]['count'] = r[1]
		i += 1

	# Get least common ports
	qr = db.execute('SELECT port || "/" || protocol, COUNT(*) AS cnt FROM ports GROUP BY port||protocol ORDER BY cnt ASC LIMIT 4').fetchall()

	least_common_ports = [
		{ 'port': default_value, 'count': 0 },
		{ 'port': default_value, 'count': 0 },
		{ 'port': default_value, 'count': 0 },
		{ 'port': default_value, 'count': 0 },
	]
	i = 0
	for r in qr:
		least_common_ports[i]['port'] = r[0]
		least_common_ports[i]['count'] = r[1]
		i += 1

	db_con.close()

	return html.Div([
		dcc.Interval(
			id='interval-once-stats',
			n_intervals=0,
			max_intervals=0,
			interval=1
		),
		dcc.Clipboard(id='stats-clipboard', style={'display': 'none'}, n_clicks=0),
		html.Div([
			html.Div([
				html.Div([
					html.Img(src=get_asset_url('icons/graphpage/box.svg')),
					html.H4('Most common ports')
				],
				className='medium-heading'),
				html.Div(
				[
					html.Div([
						html.Div([
							html.Div([], className='gauge-background'),
							html.Div([], className='gauge-filler', style={'transform': f'rotate({int((int(most_common_ports[0]["count"])*180)/total_ports) if total_ports > 0 else 0}deg)'}),
							html.Div([
								html.H5(most_common_ports[0]['port'])
							], className='gauge-data')
						],
						className='gauge-container'),
						html.Span(f'{most_common_ports[0]["count"]} | {total_ports}', className='gauge-label')
					]),
					dbc.ListGroup(
						[
							dbc.ListGroupItem(html.Div([html.Span(most_common_ports[i]['port']), html.Span(most_common_ports[i]['count'])], className='lg-key-value'))
							for i in range(1,4)
						],
						flush=True,
						className='gauge-data-table'
					),
				],
				className='graph-stats-wrapper')
			],
			className='stats-box'),
			html.Div([
				html.Div([
					html.Img(src=get_asset_url('icons/graphpage/box.svg')),
					html.H4('Least common ports')
				],
				className='medium-heading'),
				html.Div(
				[
					html.Div([
						html.Div([
							html.Div([], className='gauge-background'),
							html.Div([], className='gauge-filler', style={'transform': f'rotate({int((int(least_common_ports[0]["count"])*180)/total_ports) if total_ports > 0 else 0}deg)'}),
							html.Div([
								html.H5(least_common_ports[0]['port'])
							], className='gauge-data')
						],
						className='gauge-container'),
						html.Span(f'{least_common_ports[0]["count"]} | {total_ports}', className='gauge-label')
					]),
					dbc.ListGroup(
						[
							dbc.ListGroupItem(html.Div([html.Span(least_common_ports[i]['port']), html.Span(least_common_ports[i]['count'])], className='lg-key-value'))
							for i in range(1,4)
						],
						flush=True,
						className='gauge-data-table'
					),
				],
				className='graph-stats-wrapper')
			],
			className='stats-box'),
			html.Div([
				html.Div([
					html.Img(src=get_asset_url('icons/headings/tool.svg')),
					html.H4('Identified services'),
				],
				className='medium-heading'),
				dcc.Loading([
						html.Div([
							dcc.Graph(id='stats-service-figure', figure=go.Figure(), className='stats-graph-container'),
							dag.AgGrid(
								id='stats-service-table',
								rowData=[],
								columnDefs=[
									{'headerName': 'Service', 'field': 'svc', 'maxWidth': '100'},
									{'headerName': 'Details', 'field': 'svc_details', 'flex': 1},
									{'headerName': 'Count', 'field': 'count', 'sort': 'desc', 'maxWidth': '100'},
								],
								defaultColDef={
									'wrapText': True,
									'autoHeight':True,
									'cellStyle': {'wordBreak':'normal'},
								},
								className='ag-theme-alpine-dark stats-ag-grid',
								style={'height': '16rem'}
							)
						],
						className='graph-stats-wrapper')
					],
					overlay_style={'visibility': 'visible', 'filter': 'blur(2px)'},
					type='circle',
					delay_hide=200,
					color='#00ffe0'
				)
			],
			className='stats-box grid-span-two'),
			html.Div([
				html.Div([
					html.Img(src=get_asset_url('icons/headings/cpu.svg')),
					html.H4('Operating systems')
				],
				className='medium-heading'),
				dcc.Loading([
						html.Div([
							dcc.Graph(id='stats-os-figure', figure=go.Figure(), className='stats-graph-container'),
							dag.AgGrid(
								id='stats-os-table',
								rowData=[],
								columnDefs=[
									{'headerName': 'Family', 'field': 'os_fam', 'maxWidth': '100'},
									{'headerName': 'Vendor', 'field': 'os_ven', 'flex': 1},
									{'headerName': 'Name', 'field': 'os_nam', 'flex': 1},
									{'headerName': 'Count', 'field': 'count', 'sort': 'desc', 'maxWidth': '100'},
								],
								defaultColDef={
									'wrapText': True,
									'autoHeight':True,
									'cellStyle': {'wordBreak':'normal'},
								},
								className='ag-theme-alpine-dark stats-ag-grid',
								style={'height': '16rem'}
							)
						],
						className='graph-stats-wrapper')
					],
					overlay_style={'visibility': 'visible', 'filter': 'blur(2px)'},
					type='circle',
					delay_hide=200,
					color='#00ffe0'
				)
			],
			className='stats-box grid-span-two'),
		],
		className='stats-grid')
	],
	className='graph-container')


@callback(	Output('stats-clipboard', 'content'),
		Output('div-toaster', 'children', allow_duplicate=True),
		Output('stats-clipboard', 'n_clicks'),
		Input('stats-service-table', 'cellDoubleClicked'),
		Input('stats-os-table', 'cellDoubleClicked'),
		State('div-toaster', 'children'),
		State('stats-clipboard', 'n_clicks'),
		prevent_initial_call=True
)
def _cb_copy_table_cell_to_clipboard(svc_cell, os_cell, toasts, n_clipboard):
	cell = None
	if ctx.triggered_id == 'stats-service-table':
		cell = svc_cell
	elif ctx.triggered_id == 'stats-os-table':
		cell = os_cell

	if cell is None or 'value' not in cell:
		raise PreventUpdate

	clipboard_value = cell['value']

	toasts.append(CustomToast(
		[
			'Copied cell content to clipboard.'
		],
		duration = 1000,
		headerText = 'Value copied',
		level = 'success'
	))

	n_clipboard += 1
	return clipboard_value, toasts, n_clipboard


@callback(	Output('stats-service-table', 'rowData'),
		Output('stats-service-figure', 'figure'),
		Output('stats-os-table', 'rowData'),
		Output('stats-os-figure', 'figure'),
		Input('stats-service-table', 'rowData'), # dummy Input to trigger callback
	)
def _cb_init_stats_page(_):
	db_con, db = getDB()

	# Get all services
	qr = db.execute('SELECT svc_name, svc_info, COUNT(*) AS cnt FROM ports GROUP BY svc_name||svc_info ORDER BY cnt DESC').fetchall()

	svc_labels = []
	svc_details = []
	svc_values = []
	svc_combo = []

	for r in qr:
		svc_labels.append(r[0])
		svc_details.append(r[1])
		svc_values.append(int(r[2]))
		svc_combo.append(f'{r[0] if r[0]!="" else "-/-"}{" - " if r[1]!="" else ""}{r[1]}')

	svc_table_data = [{'svc': svc_labels[i], 'svc_details': svc_details[i], 'count': svc_values[i]} for i in range(len(svc_labels))]

	defaultLayout = go.Layout(
		paper_bgcolor='rgba(0,0,0,0)',
		plot_bgcolor='rgba(0,0,0,0)',
		margin = go.layout.Margin(
			l = 0,
			r = 0,
			b = 0,
			t = 0
		),
		showlegend = False,
		uniformtext_minsize=12,
		uniformtext_mode='hide',
		colorway = [
			'#4E878C',
			'#508B8D',
			'#518E8D',
			'#53918E',
			'#54948E',
			'#56978F',
			'#579A8F',
			'#599D8F',
			'#599D8F',
			'#5AA08F',
			'#60AC90',
			'#63B291',
			'#65B891',
			'#6BBE95',
			'#71C498',
			'#77CA9B',
			'#7CCF9E',
			'#82D5A2',
			'#88DAA5',
		]
	)

	# Pie chart for services
	svc_donut = go.Figure(
		data = [go.Pie(
			labels=svc_combo,
			values=svc_values,
			hole=.5,
			textposition='inside',
			direction='clockwise',
			sort=True,
		)],
		layout = defaultLayout
	)


	# Get all Operating systems
	qr = db.execute('SELECT os_family, os_vendor, os_name, COUNT(*) AS cnt FROM hosts GROUP BY os_family||os_vendor||os_name ORDER BY cnt DESC').fetchall()

	os_family = []
	os_vendor = []
	os_name = []
	os_combo = []
	os_values = []

	for r in qr:
		os_family.append(r[0])
		os_vendor.append(r[1])
		os_name.append(r[2])
		os_combo.append(f'{r[0] if r[0]!="" else "-"} / {r[1] if r[1]!="" else "-"} / {r[2] if r[2]!="" else "-"}')
		os_values.append(int(r[3]))

	os_table_data = [{'os_fam': os_family[i], 'os_ven': os_vendor[i], 'os_nam': os_name[i], 'count': os_values[i]} for i in range(len(os_name))]
	# Pie chart for OS
	os_donut = go.Figure(
		data = [go.Pie(
			labels=os_combo,
			values=os_values,
			hole=.5,
			textposition='inside',
			direction='clockwise',
			sort=True,
		)],
		layout = defaultLayout
	)

	db_con.close()

	return svc_table_data, (svc_donut), os_table_data, (os_donut)
