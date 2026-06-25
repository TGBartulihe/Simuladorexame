from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class DocumentMetadata:

    document_type: str

    subject: str | None

    code: str | None

    year: int | None

    phase: str | None


SUBJECT_CODES = {

    "639": "Português",

    "635": "Matemática A",

    "702": "Biologia e Geologia",

    "715": "Física e Química A",

}


PHASE_PATTERN = re.compile(

    r"\b(F1|F2|EE)\b",

    re.IGNORECASE,

)


YEAR_PATTERN = re.compile(

    r"\b(20\d{2})\b"

)


CODE_PATTERN = re.compile(

    r"\b(635|639|702|715)\b"

)


class DocumentClassifier:

    def classify(

        self,

        filename: str,

        text: str,

    ) -> DocumentMetadata:

        upper = text.upper()

        filename_upper = filename.upper()

        year = self._year(

            filename,

            text,

        )

        code = self._code(

            filename,

            text,

        )

        phase = self._phase(

            filename,

            text,

        )

        subject = SUBJECT_CODES.get(code)

        #
        # critérios
        #

        if (

            "CRITÉRIOS DE CLASSIFICAÇÃO" in upper

            or

            "CRITERIOS DE CLASSIFICACAO" in upper

            or

            "-CC" in filename_upper

            or

            "_CC" in filename_upper

        ):

            return DocumentMetadata(

                document_type="criteria",

                subject=subject,

                code=code,

                year=year,

                phase=phase,

            )

        #
        # prova
        #

        if (

            "PROVA" in upper

            or

            "EXAME FINAL NACIONAL" in upper

            or

            filename_upper.startswith("EX-")

        ):

            return DocumentMetadata(

                document_type="exam",

                subject=subject,

                code=code,

                year=year,

                phase=phase,

            )

        #
        # informação
        #

        if (

            "INFORMAÇÃO" in upper

            or

            "INFORMACAO" in upper

        ):

            return DocumentMetadata(

                document_type="information",

                subject=subject,

                code=code,

                year=year,

                phase=phase,

            )

        #
        # guia
        #

        if (

            "GUIA" in upper

            or

            "MANUAL" in upper

        ):

            return DocumentMetadata(

                document_type="guide",

                subject=subject,

                code=code,

                year=year,

                phase=phase,

            )

        return DocumentMetadata(

            document_type="unknown",

            subject=subject,

            code=code,

            year=year,

            phase=phase,

        )

    # ======================================================

    def _year(

        self,

        filename: str,

        text: str,

    ):

        match = YEAR_PATTERN.search(filename)

        if match:

            return int(match.group(1))

        match = YEAR_PATTERN.search(text)

        if match:

            return int(match.group(1))

        return None

    # ======================================================

    def _code(

        self,

        filename: str,

        text: str,

    ):

        match = CODE_PATTERN.search(filename)

        if match:

            return match.group(1)

        match = CODE_PATTERN.search(text)

        if match:

            return match.group(1)

        return None

    # ======================================================

    def _phase(

        self,

        filename: str,

        text: str,

    ):

        match = PHASE_PATTERN.search(filename)

        if match:

            return match.group(1).upper()

        match = PHASE_PATTERN.search(text)

        if match:

            return match.group(1).upper()

        return None