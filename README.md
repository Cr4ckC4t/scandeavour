# scandeavour

Dashboard for merging, visualising and filtering network scans.

## Setup

Requires Python 3.12+.

```Bash
git clone https://github.com/Cr4ckC4t/scandeavour.git
cd scandeavour
python3 -m venv ./venv
# On Linux
./venv/bin/pip3 install -r requirements.txt
./venv/bin/python3 app.py my_project.db
# On Windows
.\venv\Scripts\pip3 install -r requirements.txt
.\venv\Scripts\python3 app.py my_project.db
```

## Features

- Load Nmap, Nessus and Masscan results (parsers are modular and can be added as plugins)
- View scans, hosts and open ports in an interactive graph with details for every node
- View all merged hosts in a dashboard
- Expand on host details (i.e. related scans, open ports, script outputs)
- Apply tags to hosts for custom prioritisation
- Chain modular drop-down filters to select relevant hosts based on their address, tag, open ports, script outputs, scans, OS, etc.
- Copy identified hosts and open ports to clipboard for a new scan
- Export hosts, ports and services to a CSV (e.g. for import in Word)
- Offline mode - once installed, no internet connection is required (a browser is required to access the dashboard though)

## Dashboard

Using the Zenmap [`nmap_example.xml`](https://github.com/nmap/nmap/blob/master/zenmap/radialnet/share/sample/nmap_example.xml) for demonstration.

![View a graph with all scans, hosts and open ports.](example_graph.png)

![View all hosts from merged scan results.](example_data.png)

![View scan details for single hosts.](example_details.png)

# License and attribution

Code released under the [MIT License](LICENSE).

Built using [Dash](https://github.com/plotly/dash/tree/dev) (licensed under MIT), [Dash Bootstrap Components](https://github.com/facultyai/dash-bootstrap-components) (licensed under Apache 2.0), and [Bootswatch](https://github.com/thomaspark/bootswatch) (licensed under MIT).

