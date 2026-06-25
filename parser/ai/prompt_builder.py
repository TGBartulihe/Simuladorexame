from __future__ import annotations

import json

from parser.config import CONFIG


PROMPT_VERSION = "1.0.0"


class PromptBuilder:

    def __init__(self):

        self.version = PROMPT_VERSION

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def build(

        self,

        question,

    ) -> str:

        statement = question["statement"] or ""

        criteria = question["criteria_text"] or ""

        choices = self._choices(question)

        return f"""
És um professor especialista do IAVE.

Responde APENAS em JSON.

Nunca escrevas markdown.

Nunca expliques fora do JSON.

Nunca inventes informação que não esteja no enunciado ou nos critérios.

Caso uma informação não exista escreve null.

VERSÃO_DO_PROMPT

{self.version}

==========================================================

ENUNCIADO

{statement}

==========================================================

ALTERNATIVAS

{choices}

==========================================================

CRITÉRIOS OFICIAIS

{criteria}

==========================================================

Produz exatamente este JSON.

{self.schema()}

"""
    # ==========================================================

    @staticmethod
    def _choices(question):

        if "choices" not in question.keys():

            return "Sem alternativas."

        if not question["choices"]:

            return "Sem alternativas."

        text = []

        for choice in question["choices"]:

            text.append(

                f'{choice["letter"]}. {choice["text"]}'

            )

        return "\n".join(text)

    # ==========================================================

    @staticmethod
    def schema():

        schema = {

            "question": "",

            "question_type": "",

            "correct_answer": "",

            "rubric": "",

            "theme": "",

            "subtheme": "",

            "difficulty": "",

            "bloom": "",

            "estimated_minutes": 0,

            "skills": [

            ],

            "knowledge": [

            ],

            "common_errors": [

            ],

            "study_tip": "",

            "keywords": [

            ],

            "confidence": 0.0

        }

        return json.dumps(

            schema,

            indent=4,

            ensure_ascii=False,

        )