from dataclasses import dataclass

from machinelearningcompiler.common import CompileError
from machinelearningcompiler.parser import (
    Atom,
    AtomBool,
    AtomInt,
    AtomRef,
    AtomStack,
    Binding,
    File,
    OpKind,
    OpRhs,
    Rhs,
)


class ConstantInt:
    val: int


class ConstantBool:
    val: bool


type BindingId = int


class BindingDefinition:
    binding: BindingId


type Definition = ConstantInt | ConstantBool | BindingDefinition


type DefinitionId = int

type RhsId = int

# Types


@dataclass
class Mismatch:
    pass


@dataclass
class TypeInt:
    pass


@dataclass
class TypeBool:
    pass


type Type = TypeInt | TypeBool

# Result


@dataclass
class Rejected:
    pass


type Result = Atom | Rejected

type RhsId = int


# Graph
#
from dataclasses import dataclass


@dataclass
class Node:
    title: str


type NodeId = int
type BindingId = str


@dataclass
class Edge:
    start: NodeId
    end: NodeId


class Graph:
    def __init__(self):
        self.node_bindings: dict[BindingId, NodeId] = {}
        self.nodes: dict[NodeId, Node] = {}
        self.edges: list[Edge] = []

    def print(self):
        for node_id, node in self.nodes.items():
            connections = [
                self.nodes[edge.end].title
                for edge in self.edges
                if edge.start == node_id
            ]

            if connections:
                print(f"{node.title} -> {', '.join(connections)}")
            else:
                print(f"{node.title}")


class EvalTest:
    def __init__(self):
        self.bindings: dict[BindingId, Binding] = {}
        self.names: dict[str, BindingId] = {}
        self.graph: Graph = Graph()
        self.current_node_id: NodeId = 0

    def visit_file(self, file: File):
        for stmt in file.statements:
            self.visit_stmt(stmt)

    def visit_stmt(self, binding: Binding):
        assert isinstance(binding, Binding), "only bindings"

        binding_id = len(self.bindings)
        self.bindings[binding_id] = binding
        self.names[binding.lhs] = binding_id

        node_id = len(self.graph.nodes)
        self.graph.node_bindings[binding_id] = node_id
        self.graph.nodes[node_id] = Node(str(binding.rhs))
        self.current_node_id = node_id

        self.visit_rhs(binding.rhs)

    def visit_rhs(self, rhs: Rhs):
        match rhs:
            case OpRhs():
                self.visit_op(rhs)
            # case Ref(name):
            #     ...
            # case Int(val) | Bool(val):
            #     ...
            # case Stack(items):
            #     ...
            case _:
                raise NotImplementedError

    def visit_op(self, op: OpRhs):
        match op:
            case OpRhs(OpKind.ASSERT, [actual, expected]):
                if not self.comparable_to(
                    self.infer_atom_type(actual), self.infer_atom_type(expected)
                ):
                    raise CompileError("rejected")

            case OpRhs(OpKind.ADD, [a1, a2]):
                if not self.can_sum(self.infer_atom_type(a1), self.infer_atom_type(a2)):
                    raise CompileError("Cannot add")
            case _:
                raise NotImplementedError(op.name)

    def lookup_name(self, name: str) -> Binding:
        found = self.names.get(name)
        if found is None:
            print(self.names)
            raise CompileError(f"Undefined name '{name}'")

        self.graph.edges.append(
            Edge(start=self.graph.node_bindings[found], end=self.current_node_id)
        )

        return self.bindings[found]

    def infer_atom_type(self, atom: Atom) -> Type:
        match atom:
            case AtomInt():
                return TypeInt()
            case AtomBool():
                return TypeBool()
            case AtomRef(name):
                binding = self.lookup_name(name)
                return self.infer_binding_type(binding.rhs)
            case _:
                raise NotImplementedError

    def infer_binding_type(self, binding: Rhs) -> Type:
        match binding:
            case OpRhs(OpKind.ASSERT):
                return TypeBool()
            case OpRhs(OpKind.ADD, [arg1, arg2]):
                typ_1 = self.infer_atom_type(arg1)
                typ_2 = self.infer_atom_type(arg2)

                if not self.can_sum(typ_1, typ_2):
                    raise CompileError(f"Cannot add {arg1} & {arg2}")

                return typ_1
            case AtomInt() | AtomBool() | AtomStack() | AtomRef():
                return self.infer_atom_type(binding)
            case _:
                raise NotImplementedError(f"infer_binding_type {binding}")

    def can_sum(self, a: Type, b: Type):
        return self.comparable_to(a, b)

    def comparable_to(self, a: Type, b: Type) -> bool:
        match a:
            case TypeInt():
                match b:
                    case TypeInt():
                        return True
                    case _:
                        return False
            case _:
                raise NotImplementedError(f"a: {a}, b: {b}")
