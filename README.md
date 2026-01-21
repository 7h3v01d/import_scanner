# Python Import Scanner & Dependency Visualizer

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

A powerful desktop utility built with **PyQt6** and **Pyvis** to scan, analyze, and visualize the internal and external dependencies of any Python project. This tool helps developers identify architectural smells, locate circular dependencies, and understand the mapping of large codebases.

## 🚀 Features

- Automated Project Scanning: Recursively walks through project directories, automatically ignoring virtual environments (venv) to focus on your source code.
- Circular Dependency Detection: Implements Tarjan’s Algorithm to find strongly connected components (cycles) and highlights them in red.
- Interactive Dependency Graph: A zoomable, draggable HTML-based graph powered by pyvis.
- Static Graph Export: Generates high-quality PNG or SVG diagrams using Graphviz.
- Internal vs. External Mapping: Distinguishes between your project's modules (internal) and third-party libraries (external).
- Detailed Tree View: A searchable list of all modules, their file paths, and the number of imports they contain.
- Data Export: Export your dependency analysis to JSON for further data processing.

---

## 🛠️ Technology Stack

- GUI Framework: PyQt6 (with QtWebEngine for interactive graphs)
- Graph Engine: pyvis (Interactive) and Graphviz (Static)
- Analysis: ast (Abstract Syntax Trees) for parsing Python files without executing them.
- Algorithm: Tarjan's Strongly Connected Components for cycle detection.

---

## 📋 Prerequisites

Before running the scanner, ensure you have Graphviz installed on your system if you wish to generate static PNG/SVG graphs.

- Windows: choco install graphviz
- macOS: brew install graphviz
- Linux: sudo apt-get install graphviz

**download for windows:**</br> 
32bit - https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/14.1.0/windows_10_cmake_Release_graphviz-install-14.1.0-win32.exe</br> 
64bit - https://gitlab.com/api/v4/projects/4207231/packages/generic/graphviz-releases/14.1.0/windows_10_cmake_Release_graphviz-install-14.1.0-win64.exe

---

## ⚙️ Installation
Clone the repository:

```Bash
git clone https://github.com/yourusername/python-import-scanner.git
cd python-import-scanner
```
Install Python dependencies:
```Bash
pip install PyQt6 PyQt6-WebEngine pyvis
```
---

## 📖 How to Use

1. Run the script:
```Bash
python scanner.py
```
2. Select Project: Upon launch, the app will prompt you to select the root folder of the Python project you want to analyze.
3. Analyze the Tree: Use the "Import Tree" tab to see a breakdown of modules. Modules highlighted in red are part of a circular dependency.
4. Explore the Graph:
    - Switch to the Interactive Graph tab to move nodes around and see how modules link.
    - Use the File menu to toggle "Show External Dependencies" if you want to see your connections to third-party libraries.
5. Export: Go to File > Export to save your graph as an Image, HTML file, or JSON data.

---

## 📂 Project Structure

- ImportScanner: The core logic class that parses files and builds the dependency map.
- ImportTreeViewer: The main GUI window handling user interactions and tab management.
- to_fqn: Utility to convert file paths into Python's dot-notation (e.g., app.models.user).
- strongly_connected_components: The logic used to detect import loops.

---

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
