"""
ToolRouter – zentrale Steuerung aller Tools
"""

from .browser.browser_tools import BrowserTools
from .file.file_tools import FileTools
from .terminal.terminal_tools import TerminalTools


class ToolRouter:
    """
    Registriert alle verfügbaren Tools und führt sie aus.
    Wird vom MasterAgent genutzt.
    """

    def __init__(self):
        # Direkte Registrierung – kein externes Registry mehr nötig
        self.tools = {
            "browser": BrowserTools(),
            "file": FileTools(),
            "terminal": TerminalTools(),
        }

    def execute(self, tools_list):
        """
        Führt eine Liste von Tool-Aufrufen aus.
        Wird vom MasterAgent übergeben.
        """
        if not tools_list:
            return []

        results = []

        for tool in tools_list:
            name = tool.get("name")
            method_name = tool.get("method", "run")  # Standard-Methode
            args = tool.get("args", {})

            tool_instance = self.tools.get(name)

            if not tool_instance:
                results.append(f"Tool '{name}' nicht gefunden")
                continue

            method = getattr(tool_instance, method_name, None)
            if not method:
                results.append(f"Methode '{method_name}' nicht in {name} gefunden")
                continue

            try:
                result = method(**args)
                results.append(result)
            except Exception as e:
                results.append(f"Fehler bei {name}.{method_name}: {str(e)}")

        return results

    def list_available_tools(self):
        """Gibt Liste aller verfügbaren Tools zurück – für Planner"""
        return list(self.tools.keys())