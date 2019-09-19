import ast
import inspect

from pytest import mark

from class_doc import extract_node_comments, extract_docs, extract_all_nodes_comments, \
    _count_neighbor_newlines, extract_docs_from_cls_obj


def cls_func(kwarg=None):
    return int


class Foo:
    #:1
    #: 2
    #: 3
    bar: int
    #: neither part of bar nor baz descr

    #: baz descr
    baz: str = 'val'
    #: should be ignored

    baf: 'List[int]' = []  #: baf descr

    bam: cls_func(
        kwarg='some val'
    )  #: bam descr

    bam2: cls_func(
        kwarg='some val'
    )
    #: not a bam2 descr

    bak: cls_func(kwarg=None) = cls_func(
        [{1}]
    )  #: bak descr

    bak2: cls_func(kwarg=None) = cls_func([{1}])
    #: not a bak2 descr

    bah = 1, 2, 3  #: bah descr
    bat = (1, 2, 3)  #: bat descr

    bah2 = 1, 2, 3
    #: not a bah2 descr

    bai = 1, \
          2, \
          3  #: bai descr

    attr_docstring = 1
    """attr_docstring descr"""

    attr_docstring_after_line = 2

    """not a attr_docstring_after_line descr"""

    ad_multi, ad_target = (1, 2)
    """both targets docstring (ad_multi, ad_target)"""

    #: both targets comment (c_multi, c_target)
    c_multi, c_target = (1, 2)

    c_same_line_multi, c_same_line_target = (1, 2)  #: both targets comment (c_same_line_multi, c_same_line_target)


FOO_LINES = inspect.getsourcelines(Foo)[0]
FOO_CLASSDEF = ast.parse(''.join(FOO_LINES)).body[0]


def get_foo_attr(name):
    for node in FOO_CLASSDEF.body:
        if isinstance(node, ast.Assign):
            if any(True for t in node.targets if t.id == name):
                return node
        else:
            if node.target.id == name:
                return node

    raise ValueError(f'Foo doesnt defines such name: {name}')


@mark.parametrize(
    'node, result',
    [
        (get_foo_attr('bar'), ['1', '2', '3']),
        (get_foo_attr('baz'), ['baz descr']),
        (get_foo_attr('baf'), ['baf descr']),
        (get_foo_attr('bam'), ['bam descr']),
        (get_foo_attr('bam2'), []),
        (get_foo_attr('bak'), ['bak descr']),
        (get_foo_attr('bak2'), []),
        (get_foo_attr('bah'), ['bah descr']),
        (get_foo_attr('bat'), ['bat descr']),
        (get_foo_attr('bah2'), []),
        (get_foo_attr('bai'), ['bai descr']),
    ],
)
def test_comment_extraction(node, result):
    assert extract_node_comments(FOO_LINES, node) == result


def test_all_comments_extraction():
    assert extract_all_nodes_comments(FOO_LINES, FOO_CLASSDEF) == {
        'bar': ['1', '2', '3'],
        'baz': ['baz descr'],
        'baf': ['baf descr'],
        'bam': ['bam descr'],
        'bak': ['bak descr'],
        'bah': ['bah descr'],
        'bat': ['bat descr'],
        'bai': ['bai descr'],
        'c_same_line_multi': ['both targets comment (c_same_line_multi, c_same_line_target)'],
        'c_same_line_target': ['both targets comment (c_same_line_multi, c_same_line_target)'],
        'c_multi': ['both targets comment (c_multi, c_target)'],
        'c_target': ['both targets comment (c_multi, c_target)']
    }


def test_attr_docstring_extraction():
    assert extract_docs_from_cls_obj(Foo) == extract_docs(FOO_LINES, FOO_CLASSDEF) == {
        'bar': ['1', '2', '3'],
        'baz': ['baz descr'],
        'baf': ['baf descr'],
        'bam': ['bam descr'],
        'bak': ['bak descr'],
        'bah': ['bah descr'],
        'bat': ['bat descr'],
        'bai': ['bai descr'],
        'attr_docstring': ['attr_docstring descr'],
        'ad_multi': ['both targets docstring (ad_multi, ad_target)'],
        'ad_target': ['both targets docstring (ad_multi, ad_target)'],
        'c_multi': ['both targets comment (c_multi, c_target)'],
        'c_target': ['both targets comment (c_multi, c_target)'],
        'c_same_line_multi': ['both targets comment (c_same_line_multi, c_same_line_target)'],
        'c_same_line_target': ['both targets comment (c_same_line_multi, c_same_line_target)'],
    }


@mark.parametrize(
    'first, second, res',
    [
        (FOO_CLASSDEF.body[11], FOO_CLASSDEF.body[12], 0),
        (FOO_CLASSDEF.body[13], FOO_CLASSDEF.body[14], 1),
    ]
)
def test_neigborhood_lines_counter(first, second, res):
    assert _count_neighbor_newlines(FOO_LINES, first, second) == res
