<p align="center"><img src="https://github.com/user-attachments/assets/40965716-558c-4ab9-b8c6-2cb5dbf3e7c8" width="120px" /></p>
<h1 align="center">Scandeavour</h1>
<p align="center">
<a href="https://pypi.org/project/scandeavour/"><img alt="PyPI - Version" src="https://img.shields.io/pypi/v/scandeavour"></a>
<a href="https://github.com/Cr4ckC4t/scandeavour/blob/main/LICENSE"><img alt="PyPI - License" src="https://img.shields.io/pypi/l/scandeavour"></a>
</p>
<p align="center">
Dashboard for merging, visualising and filtering network scans.
</p>

## 🔨 Installation

![Works on](https://img.shields.io/badge/Works%20on-Windows-green?style=flat)
![Works on](https://img.shields.io/badge/Works%20on-Linux-green?style=flat)
![Requires](https://img.shields.io/badge/Requires-Python%203.12+-green?style=flat)

```
pipx install scandeavour
```


## ✨ Features

- Load Nmap, Nessus and Masscan results (parsers are modular and can be added as plugins)
- View scans, hosts and open ports in an interactive graph with details for every node
- View all merged hosts in a dashboard
- Expand on host details (i.e. related scans, open ports, script outputs)
- Apply tags to hosts for custom prioritisation
- Chain modular drop-down filters to select relevant hosts based on their address, tag, open ports, script outputs, scans, OS, etc.
- Copy identified hosts and open ports to clipboard for a new scan
- Export hosts, ports and services to a CSV (e.g. for import in Word)
- Offline mode - once installed, no internet connection is required (a browser is required to access the dashboard though)

The following scanner outputs are supported. The main focus of this project lies on `nmap` but ingestors for other scanners can be integrated easily. Check out the [existing ingestors here](https://github.com/Cr4ckC4t/scandeavour/tree/main/src/scandeavour/ingestors) if you want to extend one or build your own.

|Tool|Source|Scan information| Open ports | Service detection | Script output |
|---|---|:---:|:---:|:---:|:---:|
|Nmap|`nmap -oX <output>` |✔|✔|✔|✔|
|Nessus|Nessus export|limited|✔|✔|✔|
|Masscan|`masscan -oX <output>` |⛔|✔|⛔|⛔|
|Masscan|`masscan \| tee <output>` |⛔|✔|⛔|⛔|


## 📖 Usage

To visualize your scan results, simply start
```
scandeavour my_project.db
```
This will create a new project database (SQLITE) in the current folder. It will be used to store all your merged scans. You can also checkout the [database schema](https://github.com/Cr4ckC4t/scandeavour/blob/main/src/scandeavour/setup_database.sqlite) if you want to interact with the data manually. The command will also start a Flask webserver running on a local port, exposing the web GUI.

> [!WARNING]  
> Do not run the dashboard with administrative capabilities and do not expose the GUI externally. While special inputs are treated with caution, malicious scan results were not considered during development. The dashboard does also not authenticate users.

1. Open http://127.0.0.1:8050/ and start uploading your scan results
   <img src="https://github.com/user-attachments/assets/d940a2ea-323a-4a13-97d2-e257d1ede519" width="800" />

2. Switch to the graph tab for an overview
   <img src="https://github.com/user-attachments/assets/2b392a38-4a29-4d4e-9354-49a9187bb46c" width="800" />

3. Filter data and view hosts details
   <img src="https://github.com/user-attachments/assets/0011a58c-6c52-43b5-8902-34f7f6f4c633" width="800" />


## 📃 License and attribution

Code released under the [MIT License](LICENSE).

Built using [Dash](https://github.com/plotly/dash/tree/dev) (licensed under MIT), [Dash Bootstrap Components](https://github.com/facultyai/dash-bootstrap-components) (licensed under Apache 2.0), and [Bootswatch](https://github.com/thomaspark/bootswatch) (licensed under MIT).

