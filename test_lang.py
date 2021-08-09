from nose.tools import *
import model
import lang
import io

# BufferedReader

def test_buffered_reader_input_empty_is_eof():
    with io.StringIO("") as fp:
        br = lang.BufferedReader(fp)
        assert br.eof() == True

def test_buffered_reader_input_nonempty_is_not_eof():
    with io.StringIO("c") as fp:
        br = lang.BufferedReader(fp)
        assert br.eof() == False

def test_buffered_reader_input_empty_peek():
    with io.StringIO("") as fp:
        br = lang.BufferedReader(fp)
        assert br.peek() == ''

def test_buffered_reader_input_nonempty_peek():
    with io.StringIO("c") as fp:
        br = lang.BufferedReader(fp)
        assert br.peek() == 'c'

def test_buffered_reader_peek_does_not_consume():
    with io.StringIO("cd") as fp:
        br = lang.BufferedReader(fp)
        br.peek()
        assert br.peek() == 'c'

def test_buffered_reader_input_empty_get():
    with io.StringIO("") as fp:
        br = lang.BufferedReader(fp)
        assert br.get() == ''

def test_buffered_reader_input_nonempty_get():
    with io.StringIO("c") as fp:
        br = lang.BufferedReader(fp)
        assert br.get() == 'c'

def test_buffered_reader_get_consumes():
    with io.StringIO("cd") as fp:
        br = lang.BufferedReader(fp)
        br.get()
        assert br.get() == 'd'

# Lexer

def test_read_lexeme_input_whitespace_only():
    with io.StringIO(" \t\n# hello world\n\t\n ") as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.type == lang.Lexeme.EOF

def test_read_lexeme_left_paren():
    with io.StringIO("(") as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.type == lang.Lexeme.LPAREN

def test_read_lexeme_right_paren():
    with io.StringIO(")") as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.type == lang.Lexeme.RPAREN

def test_read_lexeme_right_paren():
    with io.StringIO(")") as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.type == lang.Lexeme.RPAREN

def test_read_lexeme_number():
    with io.StringIO("1234") as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.type == lang.Lexeme.NUMBER

def test_read_lexeme_string_type():
    with io.StringIO('"hello world"') as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.type == lang.Lexeme.STRING

def test_read_lexeme_string_token():
    with io.StringIO('"hello world"') as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.token == "hello world"

def test_read_lexeme_string():
    with io.StringIO('"hello world"') as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.token == "hello world"

def test_read_lexeme_symbol_type():
    with io.StringIO('hello123') as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.type == lang.Lexeme.SYMBOL

def test_read_lexeme_symbol_token():
    with io.StringIO('hello123') as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.token == "hello123"

def test_read_lexeme_quote():
    with io.StringIO("'") as fp:
        br = lang.BufferedReader(fp)
        lexeme = lang.read_lexeme(br)
        assert lexeme.type == lang.Lexeme.QUOTE

# Reader

def test_read_string():
    with io.StringIO('"hello world"') as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        expr = lang.read_sexpr(lexer)
        assert expr == "hello world"

def test_read_number():
    with io.StringIO("1234") as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        expr = lang.read_sexpr(lexer)
        assert expr == 1234

def test_read_symbol_type():
    with io.StringIO("hello1234") as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        expr = lang.read_sexpr(lexer)
        assert type(expr) == lang.Symbol
        assert expr.name == "hello1234"

def test_read_symbol_name():
    with io.StringIO("hello1234") as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        expr = lang.read_sexpr(lexer)
        assert expr.name == "hello1234"

def test_read_empty_list():
    with io.StringIO('()') as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        expr = lang.read_sexpr(lexer)
        assert expr == []

def test_read_list_one_elt():
    with io.StringIO('(3)') as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        expr = lang.read_sexpr(lexer)
        assert expr == [3]

def test_read_list_multi_elt():
    with io.StringIO('(3 "hello world" )') as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        expr = lang.read_sexpr(lexer)
        assert expr == [3, "hello world"]

def test_read_list_nested_elt():
    with io.StringIO('(3 "hello world" (hello 123))') as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        expr = lang.read_sexpr(lexer)
        assert expr == [3, "hello world", [Symbol("hello"), 123]]

def test_read_list_nested_elt():
    with io.StringIO('(lambda (object-id) (zero? (length (innodes object-id 4))))') as fp:
        br = lang.BufferedReader(fp)
        lexer = lang.Lexer(br)
        actual_expr = lang.read_sexpr(lexer)
        expected_expr = [lang.Symbol("lambda"), [lang.Symbol("object-id")],
                            [lang.Symbol("zero?"),
                                [lang.Symbol("length"), [lang.Symbol("innodes"), lang.Symbol("object-id"), 4]]]]
        assert actual_expr == expected_expr

# Evaluator

def test_eq():
    expr = lang.read('(= 1 1)')
    rval = lang.eval(expr)
    assert rval == True

def test_all_relations():
    expected_relation_id = model.relation_new("blah")
    returned_relation_ids = lang.eval(lang.read('(all-relations)'))
    assert [expected_relation_id] == returned_relation_ids

def test_relation_name():
    expected_relation_name = "blah"
    relation_id = model.relation_new(expected_relation_name)
    actual_relation_name = lang.eval(lang.read('(relation-name {0})'.format(relation_id)))
    assert actual_relation_name == expected_relation_name

def test_find_first():
    expected_relation_id = model.relation_new("blah")
    expression = lang.read('(find-first (lambda (id) (= id {0})) (all-relations))'.format(expected_relation_id))
    actual_relation_id = lang.eval(expression)
    assert actual_relation_id == expected_relation_id

def test_blah():
    rval = lang.eval(lang.read("""
        (let ((relation-id
                (find-first (lambda (relation-id)
                              (= (relation-name relation-id) "precedes")) (all-relations))))
          (lambda (object-id)
            (zero? (length (innodes object-id relation-id)))))
    """))
    assert type(rval) == lang.Procedure

def test_and():
    assert lang.eval(lang.read("(and 1 2 3 0)")) == False
