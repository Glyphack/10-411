from dataclasses import dataclass
from enum import StrEnum, auto

from lark import Lark, Tree


@dataclass
class File:
    statements: list[Binding]


@dataclass
class Binding:
    lhs: str
    rhs: Rhs


# Right-hand side

type Rhs = OpRhs | Atom


@dataclass(unsafe_hash=True)
class OpRhs:
    name: OpKind
    srcs: list[Atom]
    attrs: list[Attr]


@dataclass
class Attr:
    key: str
    value: str


class OpKind(StrEnum):
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


# Atoms

type Atom = AtomRef | AtomInt | AtomBool | AtomStack


@dataclass
class AtomRef:
    name: str


@dataclass
class AtomInt:
    val: int


@dataclass
class AtomBool:
    val: bool


@dataclass
class AtomStack:
    items: list[Atom]


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
    def DEF(self, tok: str) -> str:
        return tok.rstrip("= \t\r\n").lstrip("%")

    def REF(self, tok: str) -> AtomRef:
        return AtomRef(name=str(tok).lstrip("%"))

    def INT(self, tok: str) -> AtomInt:
        value = int(tok, 16) if tok.startswith("0x") else int(tok)
        return AtomInt(value)

    def BOOL(self, tok: str) -> AtomBool:
        return AtomBool(tok == "true")

    def OP(self, tok: str) -> OpKind:
        return OpKind(tok)

    def ATTR(self, tok: str) -> Attr:
        key, value = tok.split("=", 1)
        return Attr(key, value)

    def stack(self, *items: Atom) -> AtomStack:
        return AtomStack(list(items))

    def alias(self, atom: Atom) -> Atom:
        return atom

    def op_rhs(self, name: OpKind, *rest: Atom | Attr) -> OpRhs:
        srcs = [x for x in rest if not isinstance(x, Attr)]
        attrs = [x for x in rest if isinstance(x, Attr)]
        return OpRhs(name, srcs, attrs)

    def binding(self, name: str, rhs: Rhs) -> Binding:
        return Binding(name, rhs)

    def file(self, *bindings: Binding) -> File:
        return File(list(bindings))


def parse_file(program: str) -> File:
    parser = Lark(GRAMMAR, start="file", parser="lalr")
    tree = parser.parse(program)
    tree = ToAst().transform(tree)
    assert isinstance(tree, File), "Program should be a file"
    return tree
