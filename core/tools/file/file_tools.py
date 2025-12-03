import os

class FileTools:
    @staticmethod
    def read(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            return "File: Lesen fehlgeschlagen"

    @staticmethod
    def write(path: str, content: str) -> str:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return "File: Geschrieben"
        except:
            return "File: Schreiben fehlgeschlagen"

    @staticmethod
    def list_dir(path: str) -> str:
        try:
            return "\n".join(os.listdir(path))
        except:
            return "File: Verzeichnis nicht lesbar"