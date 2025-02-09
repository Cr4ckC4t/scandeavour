# scandeavour

Dashboard for merging, visualising and filtering network scans.

# Features

- Load Nmap, Nessus and Masscan results (parsers are modular and can be added as plugins)
- View scans, hosts and open ports in an interactive graph with details for every node
- View all merged hosts in a dashboard
- Expand on host details (i.e. related scans, open ports, script outputs)
- Apply tags to hosts for custom prioritisation
- Chain modular drop-down filters to select relevant hosts based on their address, tag, open ports, script outputs, scans, OS, etc.
- Copy identified hosts and open ports to clipboard for a new scan
- Export hosts, ports and services to a CSV (e.g. for import in Word)
- Offline mode - once installed, no internet connection is required (a browser is required to access the dashboard though)

# License and attribution

Code released under the [MIT License](LICENSE).

Built using [Dash](https://github.com/plotly/dash/tree/dev) (licensed under MIT), [Dash Bootstrap Components](https://github.com/facultyai/dash-bootstrap-components) (licensed under Apache 2.0), and [Bootswatch](https://github.com/thomaspark/bootswatch) (licensed under MIT).

