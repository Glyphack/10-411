import sys

from machinelearningcompiler.analyzer import EvalTest
from machinelearningcompiler.parser import parse_file


def main() -> None:
    file = sys.argv[1]
    with open(file, "r") as o:
        content = o.read()
    program = parse_file(content)

    e = EvalTest()
    e.visit_file(program)

    print(f"bindings: {e.bindings}")
    print(f"names: {e.names}")

    e.graph.print()


if __name__ == "__main__":
    main()
