from parser.ai.exam_analyzer import ExamAnalyzer


def main():

    analyzer = ExamAnalyzer()

    result = analyzer.analyze_all()

    print()

    print("=" * 50)

    print("CACHE IA FINALIZADO")

    print("=" * 50)

    for exam in result:

        print(exam)

    print()


if __name__ == "__main__":

    main()