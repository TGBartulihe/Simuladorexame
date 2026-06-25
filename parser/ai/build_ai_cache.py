from parser.ai.ai_builder import AIBuilder


def main():

    builder = AIBuilder()

    builder.process_all()

    builder.close()

    print()

    print("=================================")

    print("AI CACHE FINALIZADO")

    print("=================================")


if __name__ == "__main__":

    main()