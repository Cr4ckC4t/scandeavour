from dash import html, get_asset_url
import dash_bootstrap_components as dbc

# There appears to be a glitch that may rerender a previous toast when appending new toasts
# using the previous children of the toast div.
# It's not critical for now, so we leave it as is.
class CustomToast(dbc.Toast):
	def __init__(self,eles, headerText, level='info', duration=4000):

		if level not in ['info', 'warning', 'error', 'success']:
			level = 'info'

		header = [
			html.Img(src=get_asset_url(f'icons/toast/{level}.svg')),
			html.Span(headerText, style={'marginLeft': '0.5rem'})
		]

		super().__init__(
			eles,
			header=header,
			is_open=True,
			dismissable=True,
			duration=duration,
		)
