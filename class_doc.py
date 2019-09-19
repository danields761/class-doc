import ast
import inspect
import itertools
import string
import tokenize
from typing import Dict, List, Optional, Union, Iterator, Any

import more_itertools as mitertools


UniversalAssign = Union[ast.Assign, ast.AnnAssign]


_WHITESPACES = set(string.whitespace)


def _tokens_peekable_iter(lines: List[str]) -> mitertools.peekable:
    lines_iter = iter(lines)
    return mitertools.peekable(tokenize.generate_tokens(lambda: next(lines_iter)))


def _take_until_node(
    tokens: Iterator[tokenize.TokenInfo], node: ast.AST
) -> Iterator[tokenize.TokenInfo]:
    for tok in tokens:
        yield tok
        if tok.start[0] >= node.lineno and tok.start[1] >= node.col_offset:
            break


def _get_assign_targets(node: UniversalAssign) -> Iterator[str]:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Tuple):
                yield from (el.id for el in target.elts)
            else:
                yield target.id
    else:
        yield node.target.id


def _count_neighbor_newlines(lines: List[str], first: ast.AST, second: ast.AST) -> int:
    """
    Count only logical newlines between two nodes, e.g. any node may consist of
    multiple lines, so you can't just take difference of `lineno` attribute, this
    value will be pointless

    :return: number of logical newlines (result will be 0 if second node is placed right
        after first)
    """
    tokens_iter = _tokens_peekable_iter(lines)
    mitertools.consume(_take_until_node(tokens_iter, first))
    return (second.lineno - first.lineno) - sum(
        1
        for tok in _take_until_node(tokens_iter, second)
        if tok.type == tokenize.NEWLINE
    )


def _extract_definition_line_comment(
    lines: List[str], node: UniversalAssign
) -> Optional[str]:
    def valid_comment_or_none(comment):
        if comment.startswith('#:'):
            return comment[2:].strip()
        return None

    # will fetch all tokens until closing bracket of appropriate type occurs
    #  recursively calls himself when new opening bracket detected
    matching_brackets = {'{': '}', '[': ']', '(': ')'}

    def consume_between_bracers(iterable, bracket_type: str):
        closing_bracket = matching_brackets[bracket_type]
        for op in iterable:
            if op.string == closing_bracket:
                return
            if op.string in matching_brackets:
                return consume_between_bracers(iterable, op.string)
        # should never occurs because this lines already parsed and validated
        raise ValueError(f'no closing bracket for bracket of type "{bracket_type}"')

    # find last node
    if node.value is None:
        if not isinstance(node, ast.AnnAssign) or node.annotation is None:
            return None
        last_node = node.annotation
    else:
        if (
            isinstance(node.value, ast.Tuple)
            and lines[node.value.lineno - 1][node.value.col_offset - 1] != '('
        ):
            last_node = node.value.elts[-1]
        else:
            last_node = node.value

    tokens_iter = _tokens_peekable_iter(lines)

    # skip tokens until first token of last node occurred
    tokens_iter.prepend(mitertools.last(_take_until_node(tokens_iter, last_node)))

    # skip all except newline (for \ escaped newlines NEWLINE token isn't emitted) and
    #  comment token itself
    for tok in tokens_iter:
        if tok.type in (tokenize.COMMENT, tokenize.NEWLINE):
            tokens_iter.prepend(tok)
            break
        if tok.type == tokenize.OP and tok.string in matching_brackets:
            consume_between_bracers(tokens_iter, tok.string)

    try:
        maybe_comment = next(tokens_iter)
    except StopIteration:
        return None

    if maybe_comment.type == tokenize.COMMENT:
        return valid_comment_or_none(maybe_comment.string)


def _extract_prev_node_comments(lines: List[str], node: UniversalAssign) -> List[str]:
    leading_whitepsaces = ''.join(
        itertools.takewhile(lambda char: char in _WHITESPACES, lines[node.lineno - 1])
    )
    comment_line_start = leading_whitepsaces + '#:'

    return list(
        line[len(comment_line_start) :].strip()
        for line in itertools.takewhile(
            lambda line: line.startswith(comment_line_start),
            reversed(lines[: node.lineno - 1]),
        )
    )[::-1]


def extract_node_comments(lines: List[str], node: UniversalAssign) -> List[str]:
    # firstly prioritize "after assignment comment"
    res = _extract_definition_line_comment(lines, node)
    if res is not None:
        return [res]

    # then try to extract "right before assignment" comments
    return _extract_prev_node_comments(lines, node)


def extract_all_nodes_comments(
    lines: List[str], cls_def: ast.ClassDef
) -> Dict[str, List[str]]:
    return {
        target: comments
        for node, comments in (
            (node, extract_node_comments(lines, node))
            for node in cls_def.body
            if isinstance(node, (ast.Assign, ast.AnnAssign))
        )
        if len(comments) > 0
        for target in _get_assign_targets(node)
    }


def extract_all_attr_docstrings(
    lines: List[str], cls_def: ast.ClassDef
) -> Dict[str, List[str]]:
    return {
        target: comments
        for node, comments in (
            (node, inspect.cleandoc(next_node.value.s).split('\n'))
            for node, next_node in mitertools.windowed(cls_def.body, 2)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            if isinstance(next_node, ast.Expr) and isinstance(next_node.value, ast.Str)
            if _count_neighbor_newlines(lines, node, next_node) == 0
        )
        for target in _get_assign_targets(node)
    }


def extract_docs(lines: List[str], cls_def: ast.ClassDef) -> Dict[str, List[str]]:
    """
    Extract attrs docstring and '#:' comments from class definition for hist attributes.
    Nodes comments are preferred over attr docstrings.

    TODO: cover all priority nuances

    :param lines: must be those lines from which `cls_def` has been compiled
    :param cls_def: class definition
    :return: per attribute doc lines
    """
    return dict(
        itertools.chain(
            extract_all_attr_docstrings(lines, cls_def).items(),
            extract_all_nodes_comments(lines, cls_def).items(),
        )
    )


def extract_docs_from_cls_obj(cls: Any):
    """
    Extract docs from class object using :py:func:`extract_docs`.

    :param cls: :py:func:`inspect.getsourcelines` must return sources of class
        definition
    :return: same as :py:func:`extract_docs`
    """
    lines = inspect.getsourcelines(cls)[0]
    tree = ast.parse(''.join(lines)).body[0]
    if not isinstance(tree, ast.ClassDef):
        raise TypeError(f'Expecting "{ast.ClassDef.__name__}", but "{cls}" is received')

    return extract_docs(lines, tree)
