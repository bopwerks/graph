from nose.tools import *
from lang import *
import io

# BufferedReader

def test_buffered_reader_input_empty_is_eof():
    with io.StringIO("") as fp:
        br = BufferedReader(fp)
        assert br.eof() == True

def test_buffered_reader_input_nonempty_is_not_eof():
    with io.StringIO("c") as fp:
        br = BufferedReader(fp)
        assert br.eof() == False

def test_buffered_reader_input_empty_peek():
    with io.StringIO("") as fp:
        br = BufferedReader(fp)
        assert br.peek() == ''

def test_buffered_reader_input_nonempty_peek():
    with io.StringIO("c") as fp:
        br = BufferedReader(fp)
        assert br.peek() == 'c'

def test_buffered_reader_peek_does_not_consume():
    with io.StringIO("cd") as fp:
        br = BufferedReader(fp)
        br.peek()
        assert br.peek() == 'c'

def test_buffered_reader_input_empty_get():
    with io.StringIO("") as fp:
        br = BufferedReader(fp)
        assert br.get() == ''

def test_buffered_reader_input_nonempty_get():
    with io.StringIO("c") as fp:
        br = BufferedReader(fp)
        assert br.get() == 'c'

def test_buffered_reader_get_consumes():
    with io.StringIO("cd") as fp:
        br = BufferedReader(fp)
        br.get()
        assert br.get() == 'd'

# TODO: Lexer

def test_read_lexeme_input_whitespace_only():
    with io.StringIO(" \t\n# hello world\n\t\n ") as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.type == Lexeme.EOF

def test_read_lexeme_left_paren():
    with io.StringIO("(") as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.type == Lexeme.LPAREN

def test_read_lexeme_right_paren():
    with io.StringIO(")") as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.type == Lexeme.RPAREN

def test_read_lexeme_right_paren():
    with io.StringIO(")") as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.type == Lexeme.RPAREN

def test_read_lexeme_number():
    with io.StringIO("1234") as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.type == Lexeme.NUMBER

def test_read_lexeme_string_type():
    with io.StringIO('"hello world"') as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.type == Lexeme.STRING

def test_read_lexeme_string_token():
    with io.StringIO('"hello world"') as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.token == "hello world"

def test_read_lexeme_string():
    with io.StringIO('"hello world"') as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.token == "hello world"

def test_read_lexeme_symbol_type():
    with io.StringIO('hello123') as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.type == Lexeme.SYMBOL

def test_read_lexeme_symbol_token():
    with io.StringIO('hello123') as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.token == "hello123"

def test_read_lexeme_quote():
    with io.StringIO("'") as fp:
        br = BufferedReader(fp)
        lexeme = read_lexeme(br)
        assert lexeme.type == Lexeme.QUOTE

# TODO: Reader

def test_read_string():
    with io.StringIO('"hello world"') as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert expr == "hello world"

def test_read_number():
    with io.StringIO("1234") as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert expr == 1234

def test_read_symbol_type():
    with io.StringIO("hello1234") as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert type(expr) == Symbol
        assert expr.name == "hello1234"

def test_read_symbol_name():
    with io.StringIO("hello1234") as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert expr.name == "hello1234"

def test_read_empty_list():
    with io.StringIO('()') as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert expr == []

def test_read_list_one_elt():
    with io.StringIO('(3)') as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert expr == [3]

def test_read_list_multi_elt():
    with io.StringIO('(3 "hello world" )') as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert expr == [3, "hello world"]

def test_read_list_nested_elt():
    with io.StringIO('(3 "hello world" (hello 123))') as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert expr == [3, "hello world", [Symbol("hello"), 123]]
# (lambda (object-id) (zero? (length (innodes object-id 4))))

def test_read_list_nested_elt():
    with io.StringIO('(lambda (object-id) (zero? (length (innodes object-id 4))))') as fp:
        br = BufferedReader(fp)
        lexer = Lexer(br)
        expr = read_sexpr(lexer)
        assert expr == [
            Symbol("lambda"),
            [
                Symbol("object-id")
            ],
            [
                Symbol("zero?"),
                [
                    Symbol("length"),
                    [
                        Symbol("innodes"),
                        Symbol("object-id"),
                        4
                    ],
                ],
            ],
        ]

# Evaluator

def test_and():
    assert eval(read("(and 1 2 3 0)")) == False
