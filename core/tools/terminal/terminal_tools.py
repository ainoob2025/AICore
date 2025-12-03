import subprocess

class TerminalTools:
    @staticmethod
    def run(command: str) -> str:
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
            return result.stdout + result.stderr
        except:
            return "Terminal: Befehl fehlgeschlagen oder Timeout"