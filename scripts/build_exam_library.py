from parser.services.build_exam_library import ExamLibraryBuilder


def main():

    builder = ExamLibraryBuilder()

    result = builder.build()

    builder.close()

    print()

    print("===================================")

    print("Biblioteca criada")

    print("===================================")

    print(f"Total...........: {result['total']}")

    print(f"Criados.........: {result['created']}")

    print(f"Ignorados.......: {result['skipped']}")

    print()


if __name__ == "__main__":

    main()