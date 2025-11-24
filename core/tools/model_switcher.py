import json
import requests
from typing import Optional


class ModelSwitcher:
    """
    ModelSwitcher = kleine Service-Klasse, die sicherstellt,
    dass LM Studio das gewünschte Modell lädt.

    Nutzung:
        switcher.ensure_model(model_id)

    - Macht einen Mini-Chat-Call an LM Studio, NUR um das richtige Modell zu laden.
    - Antwort wird verworfen, nur der erfolgreiche Ladevorgang zählt.
    """

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.current_model: Optional[str] = None

    def ensure_model(self, model_id: str) -> None:
        """
        Stellt sicher, dass LM Studio das gewünschte Modell geladen hat.
        Wenn bereits aktiv: nichts tun.
        Wenn anderes Modell aktiv: POST Call an LM Studio, um das neue Modell zu laden.
        """
        if self.current_model == model_id:
            return  # nichts tun – Modell ist schon aktiv

        # Dummy-Request, aber setzt das Modell in LM Studio
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "load_model"},
                {"role": "user", "content": "initialize"}
            ]
        }

        try:
            requests.post(self.api_url, json=payload)
        except Exception:
            # Fehler nicht hochwerfen – MasterAgent darf niemals crashen
            pass

        self.current_model = model_id
