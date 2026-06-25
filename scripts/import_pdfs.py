from pathlib import Path

from parser.extract.batch_extract import BatchExtractor


def main():

    extractor = BatchExtractor()

    extractor.run(

        folder=Path("storage/pdfs"),

        document_type="exam",

    )


if __name__ == "__main__":

    main()