from __future__ import annotations

from typing import Any


REQUIRED_FIELDS = [

    "question",

    "question_type",

    "correct_answer",

    "rubric",

    "theme",

    "difficulty",

    "bloom",

    "estimated_minutes",

    "skills",

    "knowledge",

    "common_errors",

    "study_tip",

    "keywords",

    "confidence",

]


class ValidationError(Exception):

    pass


class JsonValidator:

    @classmethod

    def validate(

        cls,

        payload: dict[str, Any],

    ):

        for field in REQUIRED_FIELDS:

            if field not in payload:

                raise ValidationError(

                    f"Campo ausente: {field}"

                )

        if not isinstance(

            payload["skills"],

            list,

        ):

            raise ValidationError(

                "skills deve ser lista"

            )

        if not isinstance(

            payload["knowledge"],

            list,

        ):

            raise ValidationError(

                "knowledge deve ser lista"

            )

        if not isinstance(

            payload["keywords"],

            list,

        ):

            raise ValidationError(

                "keywords deve ser lista"

            )

        if not isinstance(

            payload["common_errors"],

            list,

        ):

            raise ValidationError(

                "common_errors deve ser lista"

            )

        if not isinstance(

            payload["confidence"],

            (float, int),

        ):

            raise ValidationError(

                "confidence inválido"

            )

        return True