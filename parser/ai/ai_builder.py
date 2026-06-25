from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import requests
from rich.progress import track

from parser.config import CONFIG
from parser.database.repository import Repository


class AIBuilder:

    def __init__(self):

        self.repository = Repository()

        self.url = CONFIG.ollama_url

        self.model = CONFIG.ollama_model

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def process_exam(self, exam_id: int):

        questions = self.repository.list_questions(exam_id)

        for question in track(

            questions,

            description=f"Exam {exam_id}",

        ):

            self.process_question(question)

    # ==========================================================

    def process_question(self, question):

        #
        # cache
        #

        prompt = self.build_prompt(question)

        prompt_hash = hashlib.sha256(

            prompt.encode("utf8")

        ).hexdigest()

        cached = self.repository.get_ai_cache(

            question["id"]

        )

        if cached:

            if cached["prompt_hash"] == prompt_hash:

                return

        #
        # chama IA
        #

        payload = self.ask_ollama(prompt)

        self.repository.save_ai_cache(

            question_id=question["id"],

            model=self.model,

            prompt_hash=prompt_hash,

            json_result=json.dumps(

                payload,

                ensure_ascii=False,

                indent=2,

            ),

        )

    # ==========================================================

    def ask_ollama(

        self,

        prompt: str,

        retries: int = 3,

    ):

        for attempt in range(retries):

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

            raw = response.json()["response"]

            try:

                parsed = json.loads(raw)

                self.validate(parsed)

                return parsed

            except Exception:

                if attempt == retries - 1:

                    raise

                time.sleep(2)

        raise RuntimeError()

    # ==========================================================

    @staticmethod
    def validate(payload: dict[str, Any]):

        required = [

            "question",

            "correct_answer",

            "rubric",

            "theme",

            "difficulty",

            "bloom",

            "skills",

            "common_errors",

            "study_tip",

        ]

        for field in required:

            if field not in payload:

                raise ValueError(

                    f"Campo obrigatório ausente: {field}"

                )

    # ==========================================================

    def build_prompt(self, question):

        criteria = question["criteria_text"]

        if criteria is None:

            criteria = ""

        return f"""
És um professor especialista do IAVE.

Responde exclusivamente em JSON.

Nunca utilizes markdown.

Nunca utilizes texto fora do JSON.

Questão:

{question["statement"]}

Critérios Oficiais:

{criteria}

Estrutura obrigatória:

{{
    "question":"",

    "correct_answer":"",

    "rubric":"",

    "theme":"",

    "difficulty":"Muito Fácil|Fácil|Média|Difícil|Muito Difícil",

    "bloom":"",

    "skills":[

    ],

    "common_errors":[

    ],

    "study_tip":""

}}
"""

    # ==========================================================

    def process_all(self):

        exams = self.repository.list_exams()

        for exam in exams:

            self.process_exam(

                exam["id"]

            )

    # ==========================================================

    def close(self):

        self.repository.close()