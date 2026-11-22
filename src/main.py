import sys
from dataclasses import dataclass
from enum import StrEnum, auto

from lark import Lark, Tree

type Token = Def | Ref | Bool | Int | Op | Attr | Eof

type Atom = Ref | Int | Bool | Stack


type Rhs = Op | Atom

type Stmt = Binding


@dataclass
class Def:
    name: str


@dataclass
class Ref:
    name: str


@dataclass
class Int:
    val: int


@dataclass
class Bool:
    val: bool


@dataclass
class Stack:
    items: list[Atom]


@dataclass
class Attr:
    key: str
    value: str


@dataclass
class Eof:
    pass


@dataclass
class Binding:
    lhs: Def
    rhs: Rhs


@dataclass
class File:
    statements: list[Stmt]


class OpName(StrEnum):
    PARAM = auto()
    CALL = auto()
    STACK = auto()
    INDEX = auto()
    CAST = auto()
    ADD = auto()
    MUL = auto()
    MAX = auto()
    DIV = auto()
    MOD = auto()
    XOR = auto()
    SHL = auto()
    CMPLT = auto()
    WHERE = auto()
    ASSERT = auto()


@dataclass
class Op:
    name: OpName
    srcs: list[Atom]
    attrs: list[Attr]


GRAMMAR = r"""
file: binding+

binding: DEF rhs

rhs: OP atom* ATTR*   -> op_rhs
   | atom             -> alias

?atom: REF | INT | BOOL | stack
stack: "[" atom* "]"


IDENTIFIER: /[A-Za-z0-9_]+/
INT: /0x[0-9a-fA-F]+/ | /-?[0-9]+/
BOOL: "true" | "false"
OP: "param" | "call" | "stack" | "index" | "cast" | "add" | "mul" | "max"
  | "div" | "mod" | "xor" | "shl" | "cmplt" | "where" | "assert"
ATTR: IDENTIFIER "=" IDENTIFIER

DEF: "%" IDENTIFIER WS? "="
REF :"%" IDENTIFIER

COMMENT: /#[^\n]*/

%ignore COMMENT
%import common.WS
%ignore WS
"""

from lark import Transformer, v_args


@v_args(inline=True)
class ToAst(Transformer[Tree, File]):
    def DEF(self, tok: str) -> Def:
        return Def(name=tok.rstrip("= \t\r\n").lstrip("%"))

    def REF(self, tok: str) -> Ref:
        return Ref(name=str(tok))

    def INT(self, tok: str) -> Int:
        value = int(tok, 16) if tok.startswith("0x") else int(tok)
        return Int(value)

    def BOOL(self, tok: str) -> Bool:
        return Bool(tok == "true")

    def OP(self, tok: str) -> OpName:
        return OpName(tok)

    def ATTR(self, tok: str) -> Attr:
        key, value = tok.split("=", 1)
        return Attr(key, value)

    def stack(self, *items: Atom) -> Stack:
        return Stack(list(items))

    def alias(self, atom: Atom) -> Atom:
        return atom

    def op_rhs(self, name: OpName, *rest: Atom | Attr) -> Op:
        srcs = [x for x in rest if not isinstance(x, Attr)]
        attrs = [x for x in rest if isinstance(x, Attr)]
        return Op(name, srcs, attrs)

    def binding(self, lhs: Def, rhs: Rhs) -> Binding:
        return Binding(lhs, rhs)

    def file(self, *bindings: Binding) -> File:
        return File(list(bindings))


@dataclass
class EvalTest:
    defs: list[Def]
    results: dict[Rhs, str]

    def visit_file(self, file: File):
        last = file.statements[-1]
        assert isinstance(last, Binding), "Last statement is not binding"
        assert last.lhs == Def("t"), last
        assert isinstance(last.rhs, Op) and last.rhs.name == OpName.ASSERT, last.rhs

        for stmt in file.statements:
            self.visit_stmt(stmt)

    def visit_stmt(self, stmt: Stmt):
        assert isinstance(stmt, Binding), "only bindings"

        self.visit_def(stmt.lhs)
        self.visit_rhs(stmt.rhs)

    def visit_def(self, _def: Def):
        self.defs.append(_def)

    def visit_rhs(self, rhs: Rhs):
        match rhs:
            case Op():
                self.visit_op(rhs)
            case Ref(name):
                ...
            case Int(val) | Bool(val):
                ...
            case Stack(items):
                ...
            case _:
                assert_never(rhs)

    def visit_op(self, op: Op):
        match op:
            case Op(OpName.ASSERT, [actual, expected]):
                if not comparable_to(actual, expected):
                    print("rejected")
                    return
                if actual != expected:
                    print("mismatch")
                    return
                return
                print("match")
            case _:
                raise NotImplementedError(op.name)

    def visit_atom(self, atom: Atom):
        pass


def main() -> None:
    file = sys.argv[1]
    content = ""

    with open(file, "r") as o:
        content = o.read()

    parser = Lark(GRAMMAR, start="file", parser="lalr")
    tree = parser.parse(content)
    tree = ToAst().transform(tree)
    assert isinstance(tree, File)

    # for stmt in tree.statements:
    #     print(stmt)

    EvalTest([]).visit_file(tree)


def comparable_to(a: Atom, b: Atom):
    match a:
        case Int():
            return isinstance(b, Int)
        case _:
            raise NotImplementedError("")


if __name__ == "__main__":
    main()
