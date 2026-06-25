from __future__ import annotations

import json
import requests

from parser.config import CONFIG


class OllamaClient:

    def __init__(self):

        self.url = CONFIG.ollama_url

        self.model = CONFIG.ollama_model

    def generate(

        self,

        prompt: str,

    ):

        response = requests.post(

            self.url,

            json={

                "model": self.model,

                "prompt": prompt,

                "stream": False,

            },

            timeout=600,

        )

        response.raise_for_status()

        payload = response.json()

        return json.loads(

            payload["response"]

        )