from __future__ import annotations

import hashlib
import json
import time

from parser.ai.prompt_builder import PromptBuilder
from parser.ai.ollama_client import OllamaClient
from parser.ai.json_validator import JsonValidator
from parser.database.repository import Repository
from parser.logger import get_logger


log = get_logger(__name__)


class QuestionAnalyzer:

    MAX_RETRIES = 3

    def __init__(self):

        self.repository = Repository()

        self.prompt_builder = PromptBuilder()

        self.client = OllamaClient()

    # =======================================================
    # PUBLIC
    # =======================================================

    def analyze(self, question):

        prompt = self.prompt_builder.build(question)

        prompt_hash = self._hash(prompt)

        cache = self.repository.get_ai_cache(
            question["id"]
        )

        if cache:

            if cache["prompt_hash"] == prompt_hash:

                log.info(
                    "CACHE %s",
                    question["question_number"],
                )

                return json.loads(
                    cache["response_json"]
                )

        start = time.perf_counter()

        payload = self._generate(prompt)

        elapsed = time.perf_counter() - start

        payload["processing_seconds"] = round(
            elapsed,
            2,
        )

        self.repository.save_ai_cache(

            question_id=question["id"],

            model=self.client.model,

            prompt_hash=prompt_hash,

            json_result=json.dumps(

                payload,

                ensure_ascii=False,

                indent=2,

            ),

        )

        return payload

    # =======================================================

    def _generate(self, prompt):

        last_exception = None

        for attempt in range(

            self.MAX_RETRIES

        ):

            try:

                payload = self.client.generate(
                    prompt
                )

                JsonValidator.validate(
                    payload
                )

                return payload

            except Exception as ex:

                last_exception = ex

                log.warning(

                    "Tentativa %d falhou.",

                    attempt + 1,

                )

                time.sleep(2)

        raise last_exception

    # =======================================================

    @staticmethod
    def _hash(prompt):

        return hashlib.sha256(

            prompt.encode("utf8")

        ).hexdigest()