# Enhanced Python Import Cycle Scanner & Visualizer

⚠️ **LICENSE & USAGE NOTICE — READ FIRST**

This repository is **source-available for private technical evaluation and testing only**.

- ❌ No commercial use  
- ❌ No production use  
- ❌ No academic, institutional, or government research use  
- ❌ No redistribution, sublicensing, or relicensing  
- ❌ No derivative works or independent development based on this code  
- ❌ No benchmarking, publication, or inclusion in reports or papers  

All rights remain exclusively with the author.  
Use of this software constitutes acceptance of the terms defined in **LICENSE.txt**.

---

## Overview

**Enhanced Python Import Cycle Scanner & Visualizer** is a modern desktop and CLI tool designed to analyze Python project structures, detect circular imports, and visualize module dependencies through an interactive graph interface.

This repository is published **solely for evaluation and showcase purposes**, demonstrating implementation quality, architectural decisions, and tooling approach.

---

## Features

- Scans entire Python projects for **module-to-module import relationships**
- Detects **circular dependencies** using graph analysis (strongly connected components)
- Interactive **dependency graph visualization** (pyvis + vis.js)
  - Red nodes indicate modules involved in cycles
  - Zoom, pan, drag, and hover for inspection
- Structured **tree/table view** of modules and imports
- Visual highlighting of cyclic modules
- One-click **rescan** (Ctrl+R)
- **JSON export** of dependency data
- Operates as both:
  - Desktop GUI application
  - Lightweight CLI analysis tool
- Fully local execution (no internet access required)

---

## Screenshots

*(Screenshots intentionally omitted from the public repository.  
You may add local screenshots for private evaluation if desired.)*

---

## Requirements

- Python **3.9+**
- PyQt6  
- pyvis  

Optional:
- PySide6 (alternative Qt backend)

---

## Installation (Evaluation Use Only)

### Minimal dependencies

```bash
pip install PyQt6 pyvis
```
Or with PySide6:
```bash
pip install PySide6 pyvis
```
### Running the Tool
GUI Mode (recommended)

Scan the current directory:
```bash
python scanner_gui_v0.7.py
```
Scan a specific project:
```bash
python scanner_gui_v0.7.py /path/to/your/project
```
### CLI Mode (quick analysis)
```bash
python scanner_gui_v0.7.py /path/to/project
```
Example output:
```text
Scanned 47 modules

Circular Dependencies:
Cycle 1: myapp.core.models → myapp.api.views → myapp.core.models
```

## Keyboard Shortcuts
```text
Copy code
Ctrl+R — Rescan project
Ctrl+E — Export dependency data (JSON)
Ctrl+Q — Quit
```

## How It Works (Technical Summary)

- Recursively walks project .py files
- Parses Python AST to extract:
- import x
- from x import y
- Resolves relative imports
- Builds a directed dependency graph
- Detects cycles via strongly connected components
- Generates an interactive HTML graph
- Displays results via Qt tree view and embedded web view

## Project Structure
```text
.
├── scanner_gui_v0.7.py   # GUI + CLI entry point
├── graph.html            # Generated on execution
├── lib/                  # Local vis.js assets
└── README.md
```

## Known Limitations

- Dynamic imports are not resolved (__import__, importlib)
- External / installed packages are ignored
- Very large projects may produce dense graphs
- Graph is regenerated on each scan

## Contribution Policy

Feedback, issue reports, and suggestions are welcome.

You may submit:

- Bug reports
- Design suggestions
- Pull requests for review

**However:**

- Submitted contributions do not grant any license or ownership rights
- The author retains full discretion over acceptance and future use
- Contributors do not receive redistribution or reuse rights

## License

This project is not open-source.

It is licensed under a private evaluation-only license.</br>
See LICENSE.txt for full terms.
