__version__ = "1.2.3"

from dash import Dash, html, get_asset_url, page_container, DiskcacheManager, clientside_callback, Input, Output, State
import dash_bootstrap_components as dbc
from scandeavour.utils import initDB, TagRibbons
import diskcache # for background callbacks: https://dash.plotly.com/background-callbacks
from flask import Flask, request
import uuid
import tempfile
from os import path, environ
import dash_cytoscape as cyto
import argparse

cyto.load_extra_layouts()
server = Flask(__name__)

@server.route('/upload-file', methods=['POST'])
def upload_file_api():
	try:
		name = uuid.uuid4().hex
		with open(path.join(tempfile.gettempdir(),name), 'wb') as f:
			f.write(request.data)
		return name, 200
	except Exception as e:
		print(f'Failed to process API request: {e}')
		return '', 500


def DashApp(server):

	cache = diskcache.Cache("./cache")
	background_callback_manager = DiskcacheManager(cache)

	app = Dash(
		__name__,
		server=server,
		serve_locally=True,
		external_stylesheets=[
			# To make this app load offline, we download the desired theme from bootswatch
			# in this case: DARKLY
			# and then inside the bootstrapmin.css file we must remove the google font import at the
			# very beginning because otherwise this app wil not load offline.
			'/assets/bootstrap.min.css', # https://cdn.jsdelivr.net/npm/bootswatch@5.3.3/dist/darkly/bootstrap.min.css
		],
		use_pages=True,
		suppress_callback_exceptions=True, # required for dynamic components
		background_callback_manager = background_callback_manager, # use for background callbacks
	)

	sidebar = html.Div(
		[
			html.Img(src=get_asset_url('icons/hexagon.svg'), className="nav-logo"),
			html.Hr(),
			dbc.Nav(
				[
					dbc.NavLink(
						[
							html.Img(src=get_asset_url('icons/import.svg')),
							html.Span("Import Scan")
						],
						href="/",
						active="exact"
					),
					dbc.NavLink(
						[
							html.Img(src=get_asset_url('icons/graph.svg')),
							html.Span("View Graph")
						],
						href="/graph",
						active="exact"
					),
					dbc.NavLink(
						[
							html.Img(src=get_asset_url('icons/stats.svg')),
							html.Span("View Data")
						],
						href="/data",
						active="exact"
					),
					dbc.NavLink(
						[
							html.Img(src=get_asset_url('icons/pie-chart.svg')),
							html.Span("View Statistics")
						],
						href="/stats",
						active="exact"
					),
				],
				vertical=True,
				pills=True
			),
			html.Span(f'v{__version__}', className='nav-version')

		],
		id='div-sidebar',
		className="sidebar"
	)

	content = html.Div(
		[
			page_container
		],
		id='div-content',
		className='content',
	)

	toasts = dbc.Container(
		[],
		id='div-toaster',
		class_name='toaster'
	)

	app.layout = html.Div([
		sidebar,
		content,
		toasts,
	])

	return app

def main():
	parser = argparse.ArgumentParser(
		description='Version: ' + __version__,
	)
	parser.add_argument('projectfile', action='store', help='SQLite database project file (will be created if it doesn\'t exist yet)')
	parser.add_argument('-p', '--port', required=False, default=8050, action='store', help='port to host the dashboard on')
	parser.add_argument('-d', '--debug', required=False, action='store_true', help='enable debugging')
	parser.add_argument('-v', '--version', required=False, action='store_true', help='print version')

	args = parser.parse_args()

	if args.version == True:
		print(f'v{__version__}')
		exit(0)

	environ['SQLITE_PROJECT_FILE'] = args.projectfile

	print(f'[+] Version: {__version__}')
	initDB()
	app = DashApp(server)

	# Client side callbacks
	# Placing the clientside_callbacks apparently has to happen before the run_server is executed
	# It wouldn't work in the pages.

        # Delete the graph node history when deleting scan results
	clientside_callback(
		"""
		function(n_clicks){
			if (n_clicks){
				sessionStorage.removeItem('node-nav-state');
				sessionStorage.removeItem('node-nav-state-timestamp');
			}
			return dash_clientside.no_update
		}
		""",
		Output('btn-confirm-delete-scans', 'n_clicks'), # dummy output
		Input('btn-confirm-delete-scans', 'n_clicks'),
	)
	# Recenter the view of the graph without redrawing the layout
	clientside_callback(
		"""
		function(n_clicks){
			cy.fit(padding=20);
			return dash_clientside.no_update;
		}
		""",
		Output('btn-fit-graph-view', 'n_clicks'), # dummy output
		Input('btn-fit-graph-view', 'n_clicks'), # center when clicked
	)
	# Center the graph around a selected node
	clientside_callback(
		"""
		function(n_clicks, unused){
			cy.centre(cy.elements(':selected'));
			return dash_clientside.no_update;
		}
		""",
		Output('btn-fit-graph-view', 'n_clicks', allow_duplicate=True), # dummy output
		Input('btn-center-selected-node', 'n_clicks'), # This input centers a node on button click
		prevent_initial_call=True
	)
	# Regain focus of subnet filter after clicking on it while node info is open
	# First, we need to close the node info (and set the click-intent), then we update the focus
	clientside_callback(
		"""
		function(n_clicks) {
			if (n_clicks>0) {
				return [false, {'id': 'subnet-filter-input'}];
			}
			return [dash_clientside.no_update, {'id': ''}];
		}
		""",
		Output('node-info-canvas', 'is_open', allow_duplicate=True),
		Output('click-intent', 'data', allow_duplicate=True),
		Input('filter-input-wrapper', 'n_clicks'),
		prevent_initial_call=True,
	)
	clientside_callback(
		"""
		function(canvasOpen, clickIntent) {
			if (canvasOpen===false && clickIntent.id.length > 0) {
				setTimeout(function(){
					document.getElementById('subnet-filter-input').focus();
				}, 400); /* This delay ensures, that the offcanvas had time to close */
			}
			return {'id':''};
		}
		""",
		Output('click-intent', 'data', allow_duplicate=True),
		Input('node-info-canvas', 'is_open'),
		State('click-intent', 'data'),
		prevent_initial_call=True
	)
	# Recenter the view of the graph after loading cola layout
	clientside_callback(
		"""
		function(trigger){
			setTimeout(function(){
				cy.fit(padding=20);
			},500); /* Set a timeout to let the layout run a bit*/
			return dash_clientside.no_update;
		}
		""",
		Output('render-trigger', 'data', allow_duplicate=True), # dummy output
		Input('render-trigger', 'data'), # center when graph was redrawn
		prevent_initial_call=True,
	)
	# Overlay button callbacks to update the settings
	# We do this on the clientside because we need access to the datastore of another page (which may not exist yet)
	# Splitting this up into client and server side callbacks is not a good idea
	# because we would update the graph settings from multiple locations and we don't want that. We want to update
	# the graph settings only in one place so the settings are up to date on page rendering and the graph stays synced with
	# the settings.
	clientside_callback(
		"""
		function(n_scans, n_ports, n_hosts, n_datafilter, graph_settings) {
			const triggered_id = dash_clientside.callback_context.triggered_id;

			/* Toggle scan view */
			if (triggered_id === 'btn-toggle-scans' && n_scans > 0) {
				graph_settings['scans-visible'] = !graph_settings['scans-visible'];
			}
			let scans_btn_img_src = '/assets/icons/graphpage/terminal-off.svg';
			let toggle_scans_label = 'Show scans';
			if (graph_settings['scans-visible']) {
				scans_btn_img_src = '/assets/icons/graphpage/terminal-on.svg';
				toggle_scans_label = 'Hide scans';
			}

			/* Toggle port view */
			if (triggered_id === 'btn-toggle-ports' && n_ports > 0) {
				graph_settings['ports-visible'] = !graph_settings['ports-visible'];
			}
			let ports_btn_img_src = '/assets/icons/graphpage/box-off.svg';
			let toggle_ports_label = 'Show ports';
			if (graph_settings['ports-visible']) {
				ports_btn_img_src = '/assets/icons/graphpage/box-on.svg';
				toggle_ports_label = 'Hide ports';
			}

			/* Toggle hosts with no ports */
			if (triggered_id === 'btn-toggle-hosts' && n_hosts > 0) {
				graph_settings['hostsnp-visible'] = !graph_settings['hostsnp-visible'];
			}
			let hosts_btn_img_src = '/assets/icons/graphpage/host-off.svg';
			let toggle_hosts_label = 'Show hosts with no open ports';
			if (graph_settings['hostsnp-visible']) {
				hosts_btn_img_src = '/assets/icons/graphpage/host-on.svg';
				toggle_hosts_label = 'Hide hosts with no open ports';
			}

			/* Toggle datafilter linking */
			if (triggered_id === 'btn-toggle-datafilter' && n_datafilter > 0) {
				graph_settings['datafilter-linked'] = !graph_settings['datafilter-linked'];
			}
			let datafilter_btn_img_src = '/assets/icons/graphpage/datafilter-off.svg';
			let toggle_datafilter_label = 'Apply filters from the data view';
			graph_settings['filters']['datatable'] = [];
			if (graph_settings['datafilter-linked']) {

				datafilter_btn_img_src = '/assets/icons/graphpage/datafilter-on.svg';
				toggle_datafilter_label = 'Ignore filters from the data view';

				/* Get the datatable settings (they may not exist yet) */
				const datatable_settings = sessionStorage.getItem('datatable-settings');

				graph_settings['filters']['datatable'] = datatable_settings ? (JSON.parse(datatable_settings))['filters'] : [];
			}

			return [
				graph_settings,
				scans_btn_img_src,
				ports_btn_img_src,
				hosts_btn_img_src,
				datafilter_btn_img_src,
				toggle_scans_label,
				toggle_ports_label,
				toggle_hosts_label,
				toggle_datafilter_label,
			];
		}
		""",
		Output('graph-settings', 'data'),
		Output('toggle-scans-img', 'src'),
		Output('toggle-ports-img', 'src'),
		Output('toggle-hosts-img', 'src'),
		Output('toggle-datafilter-img', 'src'),
		Output('btn-toggle-scans-label', 'children'),
		Output('btn-toggle-ports-label', 'children'),
		Output('btn-toggle-hosts-label', 'children'),
		Output('btn-toggle-datafilter-label', 'children'),
		Input('btn-toggle-scans', 'n_clicks'),
		Input('btn-toggle-ports', 'n_clicks'),
		Input('btn-toggle-hosts', 'n_clicks'),
		Input('btn-toggle-datafilter', 'n_clicks'),
		State('graph-settings', 'data'),
	)

	# Toggle the tags of the host-detail card in the datapage
	# We don't need to sync toggle switches on page load, as they persist their property via dbc persistence (session)
	# We just need to update the styles of the current host-detail cards and store the change (so the host details can use the setting when rendering)
	clientside_callback(
		"""
		function(toggle_tags, host_detail_settings) {
			host_detail_settings['show-tags'] = toggle_tags;

			const ribbons = document.getElementsByClassName('hd-ribbon');
			let ix=0;
			while (ix < ribbons.length) {
				ribbons[ix].style.display = toggle_tags ? 'block' : 'none';
				ix++;
			}

			return host_detail_settings;
		}
		""",
		Output('host-detail-settings', 'data'),
		Input('btn-toggle-tags', 'value'),
		State('host-detail-settings', 'data'),
	)

	# Update tags on the clientside so that a refresh is not needed when updating tags
	clientside_callback(
		"""
		function(update) {
			const tag_ribbons_map="""+str(TagRibbons.map)+""";
			const targets = new Set(update['targets']);
			const tag = update['tag'];

			/* Update details */
			const ribbons = document.getElementsByClassName('hd-ribbon');
			let ix=0;
			while (ix < ribbons.length) {
				/* the id of a ribbon is an object like {"index": "btn..", "type": "<hid>"} */
				if (targets.has(JSON.parse(ribbons[ix].id)['type'])) {
					ribbons[ix].style.background = tag_ribbons_map[tag]['css-color'];
					ribbons[ix].innerText = tag;
				}
				ix++;
			}

			/* Update AG grid */
			const vdtApi = dash_ag_grid.getApi('view-data-table')
			const table_rows = vdtApi.rowModel.rowsToDisplay;
			ix = 0;
			while (ix < table_rows.length) {
				if (targets.has(table_rows[ix].data.hid.toString())) {
					vdtApi.rowModel.rowsToDisplay[ix].data.tag = tag === 'Choose tag' ? '' : tag;
				}
				ix++;
			}
			/* activate changes */
			vdtApi.refreshCells();

			return {};
		}
		""",
		Output('trigger-tag-update', 'data', allow_duplicate=True),
		Input('trigger-tag-update', 'data'),
		prevent_initial_call=True
	)

	# DO NOT EXPOSE THIS APPLICATION TO ANYTHING OTHER THAN LOCALHOST
	app.run(
		host='127.0.0.1',
		port=args.port,
		debug=args.debug,
		use_reloader=False, # using this option can lead to unexpected behaviour (calls being executed twice etc.)
		dev_tools_silence_routes_logging=(not args.debug)
	)

if __name__ == "__main__":
	main()
