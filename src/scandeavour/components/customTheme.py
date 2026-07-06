class CustomTheme():
	def __init__(self):
		self.darkAgGridTheme = {
			"function": """
				themeQuartz.withParams({
					backgroundColor: "#2f323a",
					browserColorScheme: "dark",
					chromeBackgroundColor: {
					        ref: "foregroundColor",
					        mix: 0.07,
					        onto: "backgroundColor"
					},
					fontFamily: "Inter, system-ui, sans-serif",
					headerFontFamily: "Inter, system-ui, sans-serif",
					cellFontFamily: "Inter, system-ui, sans-serif",
					foregroundColor: "#FFF"
				})
			"""
		}

	def getDarkAgGrid(self):
		return self.darkAgGridTheme
