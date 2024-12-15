from dash import html, dcc, callback, Input, Output, State, register_page
import dash_bootstrap_components as dbc
from components.customToast import CustomToast

register_page(__name__)

def layout(**kwargs):
	return html.Div([
		html.H1("Are you lost?"),
		dcc.Interval(
			id='toast-404',
			n_intervals=0,
			max_intervals=0,
			interval=1
		)
	], style={
		'display': 'flex',
		'alignItems': 'center',
		'justifyContent': 'center',
		'height': '100vh'
	})


@callback(Output('div-toaster', 'children', allow_duplicate=True),
		Input('toast-404', 'n_intervals'),
		State('div-toaster', 'children'),
		prevent_initial_call=True)
def _cb_404toast(_, toasts):
	toasts.append(CustomToast(
		[
			"You tried to access a page that does not exist."
		],
		headerText="404 Not Found",
		level='error'
	))
	return toasts
