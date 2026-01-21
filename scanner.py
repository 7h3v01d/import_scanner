import sys
import os
import ast
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
import io # New import for handling encoding

# Ensure compatibility for frozen environments
if getattr(sys, 'frozen', False):
    # This path is where PyInstaller unpacks the binaries
    PYINSTALLER_ROOT = sys._MEIPASS
else:
    PYINSTALLER_ROOT = ''

# Third-party libraries for interactive graph
from pyvis.network import Network
from PyQt6 import QtGui, QtWebEngineWidgets
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QMessageBox, QStatusBar,
    QTabWidget, QWidget, QVBoxLayout, QLabel, QScrollArea
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QUrl


# ---------- Utility Functions ----------

def to_fqn(project_root: Path, file_path: Path) -> str:
    """
    Converts a file path to a fully qualified module name (FQN).
    e.g., /path/to/project/sub/file.py -> sub.file
    """
    rel = file_path.relative_to(project_root).with_suffix("")
    return ".".join(rel.parts)


def resolve_from_import(current_fqn: str, level: int, module: str | None) -> str:
    """
    Resolves a relative import to an FQN.
    e.g., from ..foo import bar -> project.foo.bar
    """
    pkg_parts = current_fqn.split(".")[:-1]
    if level:
        pkg_parts = pkg_parts[: -level + 1] if level > 1 else pkg_parts
    if module:
        return ".".join([*pkg_parts, module])
    return ".".join(pkg_parts)


def strongly_connected_components(graph: Dict[str, set]) -> List[List[str]]:
    """
    Finds strongly connected components in a directed graph using Tarjan's algorithm.
    Used to detect circular dependencies.
    """
    index = 0
    stack, onstack = [], set()
    indices, lowlink, sccs = {}, {}, []

    def dfs(v):
        nonlocal index
        indices[v] = lowlink[v] = index
        index += 1
        stack.append(v)
        onstack.add(v)
        for w in graph.get(v, ()):
            if w not in indices:
                dfs(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in onstack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            comp = []
            while True:
                w = stack.pop()
                onstack.remove(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                sccs.append(comp)

    for v in graph:
        if v not in indices:
            dfs(v)
    return sccs


# ---------- Scanner ----------

class ImportScanner:
    """
    Scans a Python project for import dependencies.
    """
    def __init__(self, project_root: str = ""):
        self.project_root = Path(project_root).resolve() if project_root else None
        self.module_info: Dict[str, Dict[str, Any]] = {}
        self.local_packages = set()
        self.all_local_modules = set()

    def scan(self):
        """
        Walks the project directory, scanning each Python file.
        Includes logic to skip virtual environments.
        """
        self.module_info.clear()
        if not self.project_root or not self.project_root.is_dir():
            return

        # First pass to find all local packages and modules
        self._find_local_packages_and_modules()

        for root, dirs, files in os.walk(self.project_root):
            # Heuristic to detect and prune venv folders.
            if 'pyvenv.cfg' in files:
                print(f"Ignoring venv folder: {root}")
                dirs[:] = []  # Prunes the directory list to stop os.walk from descending
                continue

            for file in files:
                if file.endswith(".py"):
                    path = Path(root) / file
                    fqn = to_fqn(self.project_root, path)
                    self.module_info[fqn] = {"path": str(path), "imports": []}
                    self._scan_file(path, fqn)
        
        # After scanning, categorize imports as internal or external
        self._categorize_imports()

    def _find_local_packages_and_modules(self):
        """
        Finds all directories that are Python packages and all individual modules.
        """
        self.local_packages.clear()
        self.all_local_modules.clear()
        for root, dirs, files in os.walk(self.project_root):
            rel_path = Path(root).relative_to(self.project_root)
            if '__init__.py' in files:
                package_name = ".".join(rel_path.parts)
                self.local_packages.add(package_name)
            for file in files:
                if file.endswith(".py"):
                    module_name = to_fqn(self.project_root, Path(root) / file)
                    self.all_local_modules.add(module_name)
    
    def _scan_file(self, path: Path, fqn: str):
        """
        Parses a single Python file to find import statements.
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(path))
        except Exception:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.module_info[fqn]["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imported = resolve_from_import(fqn, node.level, node.module)
                self.module_info[fqn]["imports"].append(imported)
    
    def _categorize_imports(self):
        """
        Separates imports into internal and external based on the master list of local modules.
        """
        for fqn, data in self.module_info.items():
            internal_imports = []
            external_imports = []
            for imported_name in data["imports"]:
                if imported_name in self.all_local_modules or imported_name.split('.')[0] in self.local_packages:
                    internal_imports.append(imported_name)
                else:
                    external_imports.append(imported_name)
            data["internal_imports"] = internal_imports
            data["external_imports"] = external_imports

    def build_graph(self) -> Dict[str, set]:
        """
        Builds a graph representation of the dependencies.
        """
        graph = {}
        for mod, data in self.module_info.items():
            graph[mod] = set(data.get("internal_imports", []))
        return graph

    def find_cycles(self) -> List[List[str]]:
        """
        Finds and returns a list of all circular dependencies.
        """
        graph = self.build_graph()
        return strongly_connected_components(graph)


# ---------- Graphviz Export (Static) ----------

def export_dot(scanner: ImportScanner) -> str:
    """
    Generates a DOT language string for Graphviz.
    This version includes all dependencies (internal and external) for a complete view.
    """
    # Create combined graph with internal and external dependencies
    graph = {}
    for mod, data in scanner.module_info.items():
        all_deps = data.get("internal_imports", []) + data.get("external_imports", [])
        graph[mod] = set(all_deps)
    
    cycles = {frozenset(c) for c in scanner.find_cycles()}
    
    # Get all nodes to display, including external ones, and omitting empty __init__.py files
    nodes_to_display = set()
    for mod, data in scanner.module_info.items():
        if not (mod.endswith('.__init__') or mod == '__init__') or data.get("imports"):
            nodes_to_display.add(mod)
    
    # Also add external dependencies to the set of nodes to display
    for deps in graph.values():
        nodes_to_display.update(deps)
    
    lines = ["digraph imports {", "rankdir=LR;"]
    
    # Define node colors based on type and cycles
    for mod in sorted(list(nodes_to_display)):
        color = "gray"
        is_in_cycle = any(mod in cycle for cycle in cycles)
        if is_in_cycle:
            color = "red"
        
        lines.append(f'"{mod}" [shape=box, style=filled, fillcolor="{color}"];')
    
    # Add all edges
    for src, dests in graph.items():
        if src in nodes_to_display:
            for dst in dests:
                if dst in nodes_to_display:
                    lines.append(f'"{src}" -> "{dst}";')
    
    lines.append("}")
    return "\n".join(lines)


def render_graphviz(dot_str: str, out_path: str) -> bool:
    """
    Calls the Graphviz 'dot' command to render the graph.
    """
    try:
        # Check if running as a frozen executable
        if getattr(sys, 'frozen', False):
            # The executable path inside the bundle
            dot_path = os.path.join(PYINSTALLER_ROOT, "dot.exe")
            command = [dot_path, "-Tpng", "-o", out_path]
        else:
            # Running as a regular Python script
            command = ["dot", "-Tpng", "-o", out_path]

        subprocess.run(command, input=dot_str.encode("utf-8"), check=True)
        return True
    except Exception:
        return False


# ---------- Interactive Graph (pyvis) ----------

def build_interactive_graph(scanner: ImportScanner, out_html: str, show_external: bool = True):
    """
    Generates an interactive HTML graph using pyvis, with an option to show/hide external dependencies.
    """
    # Create separate graphs for internal and external dependencies
    internal_graph = {mod: data.get("internal_imports", []) for mod, data in scanner.module_info.items()}
    external_graph = {mod: data.get("external_imports", []) for mod, data in scanner.module_info.items()}
    
    cycles = {frozenset(c) for c in scanner.find_cycles()}

    # Explicit height fixes collapsing issue
    net = Network(height="800px", width="100%", directed=True, bgcolor="#222222", font_color="white", cdn_resources="in_line")
    net.force_atlas_2based(gravity=-50, central_gravity=0.01, spring_length=120, spring_strength=0.05)

    # Add internal nodes and edges, omitting empty __init__.py files
    modules_to_display = [mod for mod, data in scanner.module_info.items() if not ((mod.endswith('.__init__') or mod == '__init__') and not data.get("imports"))]
    
    for mod in modules_to_display:
        data = scanner.module_info[mod]
        color = "gray"
        for cycle in cycles:
            if mod in cycle:
                color = "red"
        net.add_node(mod, label=mod, title=data["path"], color=color)
    
    for src, dests in internal_graph.items():
        if src in modules_to_display:
            for dst in dests:
                if dst in modules_to_display:
                    net.add_edge(src, dst)

    # Add external dependencies if the toggle is on
    if show_external:
        existing_nodes = [node['id'] for node in net.nodes]
        for src, dests in external_graph.items():
            if src in modules_to_display:
                for dst in dests:
                    if dst not in existing_nodes:
                        net.add_node(dst, label=dst, title="External Dependency", color="blue")
                        existing_nodes.append(dst)
                    net.add_edge(src, dst, color="blue")
    
    # Generate HTML content and explicitly write it as binary data with UTF-8 encoding.
    try:
        html_content = net.generate_html()
        with open(out_html, "wb") as f:
            f.write(html_content.encode("utf-8"))
    except Exception as e:
        raise OSError(f"Failed to write HTML to {out_html}: {e}")


# ---------- GUI ----------

class ImportTreeViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scanner = ImportScanner()

        self.setWindowTitle("Enhanced Import Scanner v1.8 by Leon Priest")
        self.resize(1200, 800)

        # Tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tree tab
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Module", "Type", "# Imports", "Imports List"])
        self.tabs.addTab(self.tree, "Import Tree")
        
        # Interactive Graph tab
        self.webview = QtWebEngineWidgets.QWebEngineView()
        self.tabs.addTab(self.webview, "Interactive Graph")
        
        # Static Graph tab
        self.graph_label = QLabel("Static graph not generated yet.")
        self.graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.graph_scroll = QScrollArea()
        self.graph_scroll.setWidgetResizable(True)
        self.graph_scroll.setWidget(self.graph_label)
        self.tabs.addTab(self.graph_scroll, "Static Graph")


        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)

        # Menu/Toolbar
        self._create_actions()
        self._create_menus()
        self._create_toolbar()

        # Initial state: prompt user to open a project
        QMessageBox.information(
            self,
            "Welcome",
            "Please select a project folder to scan for import dependencies."
        )
        self.open_project_folder()

    def _create_actions(self):
        self.open_act = QAction("Open Project", self)
        self.open_act.triggered.connect(self.open_project_folder)

        self.rescan_act = QAction("Rescan", self)
        self.rescan_act.triggered.connect(self.rescan)
        
        self.toggle_deps_act = QAction("Show External Dependencies", self, checkable=True, checked=True)
        self.toggle_deps_act.triggered.connect(self.toggle_dependencies_view)

        self.export_json_act = QAction("Export JSON", self)
        self.export_json_act.triggered.connect(self.export_json)

        self.export_static_graph_act = QAction("Export Static Graph (PNG/SVG)", self)
        self.export_static_graph_act.triggered.connect(self.export_static_graph)

        self.export_interactive_graph_act = QAction("Export Interactive Graph (HTML)", self)
        self.export_interactive_graph_act.triggered.connect(self.export_interactive_graph)

        self.quit_act = QAction("Quit", self)
        self.quit_act.triggered.connect(self.close)

        self.about_act = QAction("About", self)
        self.about_act.triggered.connect(self.show_about)

    def _create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(self.open_act)
        file_menu.addSeparator()
        file_menu.addAction(self.rescan_act)
        file_menu.addAction(self.toggle_deps_act)
        file_menu.addAction(self.export_json_act)
        file_menu.addAction(self.export_static_graph_act)
        file_menu.addAction(self.export_interactive_graph_act)
        file_menu.addSeparator()
        file_menu.addAction(self.quit_act)

        help_menu = menubar.addMenu("&Help")
        help_menu.addAction(self.about_act)

    def _create_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.addAction(self.open_act)
        toolbar.addAction(self.rescan_act)
        toolbar.addAction(self.toggle_deps_act)
        toolbar.addAction(self.export_json_act)
        toolbar.addAction(self.export_static_graph_act)
        toolbar.addAction(self.export_interactive_graph_act)
        toolbar.addAction(self.quit_act)

    def open_project_folder(self):
        """
        Prompts the user to select a project folder and starts a new scan.
        """
        directory = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if directory:
            self.scanner.project_root = Path(directory).resolve()
            self.rescan()

    def populate_tree(self):
        """
        Populates the tree view with module information.
        """
        self.tree.clear()
        cycles = {frozenset(c) for c in self.scanner.find_cycles()}

        # Filter out empty __init__.py files for the tree view
        modules_to_display = {mod for mod, data in self.scanner.module_info.items() if not ((mod.endswith('.__init__') or mod == '__init__') and not data.get("imports"))}

        for module, data in sorted(self.scanner.module_info.items()):
            if module not in modules_to_display:
                continue
            
            # Get internal and external imports separately for display
            internal_imports = data.get("internal_imports", [])
            external_imports = data.get("external_imports", [])
            all_imports = internal_imports + external_imports
            imports_str = ", ".join(all_imports) if all_imports else "-"
            
            # Determine the type of the module (always "Internal" for the main tree view)
            module_type = "Internal"
            
            item = QTreeWidgetItem([module, module_type, str(len(all_imports)), imports_str])

            for cycle in cycles:
                if module in cycle:
                    font = item.font(0)
                    font.setBold(True)
                    item.setFont(0, font)
                    item.setFont(1, font)
                    item.setFont(2, font)
                    item.setFont(3, font)
                    item.setBackground(0, QtGui.QColor("#8b0000"))
                    item.setBackground(1, QtGui.QColor("#8b0000"))
                    item.setBackground(2, QtGui.QColor("#8b0000"))
                    item.setBackground(3, QtGui.QColor("#8b0000"))
        
            self.tree.addTopLevelItem(item)

        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)

        self.status.showMessage(
            f"Scanned {len(self.scanner.module_info)} modules | Cycles: {len(cycles)}"
        )
    
    def refresh_static_graph_view(self):
        out_path = "graph.png"
        if os.path.exists(out_path):
            pixmap = QtGui.QPixmap(out_path)
            self.graph_label.setPixmap(pixmap)
            self.graph_label.adjustSize()
            self.status.showMessage("Refreshed static graph.")
        else:
            QMessageBox.warning(self, "Error", "Static graph file not found. Please run a scan first.")


    def generate_graph(self):
        """
        Generates and displays both static and interactive graphs.
        """
        # Get the state of the toggle button
        show_external = self.toggle_deps_act.isChecked()
        
        # Generate interactive graph (HTML)
        out_html = "graph.html"
        try:
            build_interactive_graph(self.scanner, out_html, show_external)
            self.webview.load(QUrl.fromLocalFile(str(Path(out_html).resolve())))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to generate interactive graph: {e}")
            
        # Generate static graph (PNG)
        out_png = "graph.png"
        dot_str = export_dot(self.scanner)
        if render_graphviz(dot_str, out_png):
            pixmap = QtGui.QPixmap(out_png)
            self.graph_label.setPixmap(pixmap)
            self.graph_label.adjustSize()
        else:
            self.graph_label.setText("Graphviz not available. Install 'graphviz' and ensure 'dot' is on PATH.")
        
    def toggle_dependencies_view(self, checked):
        """
        Regenerates the graph to show or hide external dependencies.
        """
        self.generate_graph()
        self.status.showMessage(
            f"Toggled external dependency view. Currently {'showing' if checked else 'hiding'} external dependencies."
        )


    def rescan(self):
        """
        Rescans the project folder and updates the GUI.
        """
        self.scanner.scan()
        self.populate_tree()
        self.generate_graph()

    def export_json(self):
        """
        Exports the dependency data to a JSON file.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "", "JSON Files (*.json)")
        if not path:
            return
        data = {
            "modules": self.scanner.module_info,
            "cycles": self.scanner.find_cycles()
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.status.showMessage(f"Exported JSON to {path}")

    def export_static_graph(self):
        """
        Exports the dependency graph to an image file (PNG/SVG).
        """
        path, _ = QFileDialog.getSaveFileName(self, "Save Static Graph", "", "PNG Files (*.png);;SVG Files (*.svg)")
        if not path:
            return
        dot_str = export_dot(self.scanner)
        fmt = "png" if path.endswith(".png") else "svg"
        try:
            subprocess.run(["dot", f"-T{fmt}", "-o", path], input=dot_str.encode("utf-8"), check=True)
            self.status.showMessage(f"Exported static graph to {path}")
        except Exception:
            QMessageBox.warning(self, "Error", "Graphviz 'dot' not found. Install graphviz and ensure it is on PATH.")
            
    def export_interactive_graph(self):
        """
        Exports the dependency graph to an HTML file.
        """
        path, _ = QFileDialog.getSaveFileName(self, "Save Interactive Graph", "", "HTML Files (*.html)")
        if not path:
            return
        try:
            show_external = self.toggle_deps_act.isChecked()
            build_interactive_graph(self.scanner, path, show_external)
            self.status.showMessage(f"Exported interactive graph to {path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export interactive graph: {e}")

    def show_about(self):
        """
        Displays an "About" dialog.
        """
        QMessageBox.information(
            self, "About",
            "Enhanced Import Scanner (Interactive Graph)\n\n"
            "• Import Tree + Interactive Dependency Graph\n"
            "• Pan, zoom, and click nodes\n"
            "• Highlights circular dependencies in red\n\n"
            "Clicking a node shows its file path in tooltip."
        )


# ---------- Main ----------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = ImportTreeViewer()
    viewer.show()
    sys.exit(app.exec())
