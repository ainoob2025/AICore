class BrowserTools:
    @staticmethod
    def safe_get(url: str) -> str:
        import requests
        try:
            r = requests.get(url, timeout=10)
            return r.text[:2000]
        except:
            return "Browser: Seite nicht erreichbar"