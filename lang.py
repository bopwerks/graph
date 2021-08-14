import operator
import model
import log
import io
import string

"""
;; Example code for implementing a "Tag" object whose checkbox field
;; changes the visibility of "tagged" (connected) objects.
(lambda (object-id checkedp)
  (let (tagged-objects (bfs object-id))
    (if checkedp
        (hide-objects tagged-objects object-id)
        (show-objects tagged-objects object-id))))
"""

class Env(dict):
    "An environment: a dict of {'var': val} pairs, with an outer Env."
    def __init__(self, parms=(), args=(), outer=None):
        self.update(zip(parms, args))
        self.outer = outer
    def find(self, var):
        "Find the innermost Env where var appears."
        return self if (var in self) else self.outer.find(var)

def standard_env():
    env = Env()
    env.update({
        '+': operator.add,
        '*': operator.mul,
        '/': operator.truediv,
        '>': operator.gt,
        '<': operator.lt,
        '>=': operator.ge,
        '<=': operator.le,
        '=': operator.eq
    })
    return env

global_env = standard_env()

class Procedure(object):
    "A user-defined Scheme procedure."
    def __init__(self, parms, body, env):
        self.parms, self.body, self.env = parms, body, env
    def __call__(self, *args):
        env = Env(self.parms, args, self.env)
        for expr in self.body:
            rval = eval(expr, env)
        return rval

def eval(expr, env=global_env):
    "Evaluate an expression."
    # N.B. We need to be able to run the Qt event loop concurrently.
    if type(expr) in (int, float, str):
        return expr
    elif type(expr) == Symbol:
        return env.find(expr.name)[expr.name]
    op, *args = expr
    if op == "lambda":
        return Procedure(args[0], args[1:], env)
    elif op == "quote":
        return args[0]
    elif op == "if":
        return eval(args[1], env) if eval(args[0], env) else eval(args[2], env)
    elif op == "or":
        for arg in args:
            result = eval(arg, env)
            if result:
                return True
    elif op == "and":
        for arg in args:
            result = eval(arg, env)
            if not result:
                return False
    elif op == "let":
        parms = [b[0] for b in args[0]]
        body = args[1:]
        args = [eval(b[1], env) for b in args[0]]
        return Procedure(parms, body, env)(*args)
    elif op == "define":
        if type(args[0]) == str:
            symbol = args[0]
            value = args[1]
        else:
            symbol = args[0][0]
            value = Procedure(args[0][1:], args[1:], env)
        env[symbol] = value
    else:
        proc = eval(op, env)
        args = [eval(arg, env) for arg in args]
        return proc(*args)

def builtin(arg):
    if callable(arg):
        global_env[arg.__name__] = arg
        return arg
    else:
        def rval(fn):
            global_env[arg] = fn
            return fn
        return rval

@builtin
def car(L):
    return L[0]
car = builtin(car)

@builtin
def cdr(L):
    return L[1:]

@builtin("null?")
def nullp(L):
    return not bool(L)

@builtin("list")
def _list(*args):
    return list(args)

@builtin
def square(x):
    return x * x

@builtin
def bfs(object_id, relation_ids):
    "Returns a list of IDs of all objects reachable from the given object via the given relations."
    pass

@builtin
def path(source_object_id, dest_object_id, relation_ids):
    "Returns a list of edges between the source and destination objects."
    pass

@builtin("not")
def _not(bool):
    not bool

@builtin("any")
def any(fn, L):
    for elt in L:
        if fn(elt):
            return True
    return False

@builtin("all")
def all(fn, L):
    for elt in L:
        if not fn(elt):
            return False
    return True

@builtin("has-path?")
def haspath(source_id, dest_id, relation_ids):
    return model.has_path(source_id, dest_id, *relation_ids)

@builtin("hide-object")
def hide_object(object_id, symbol):
    object = model.get_object(object_id)
    object.set_visible(False, symbol)

@builtin("show-object")
def show_object(object_id, symbol):
    object = model.get_object(object_id)
    object.set_visible(True, symbol)

@builtin("object-visible?")
def visiblep(object_id):
    object = model.get_object(object_id)
    return object.is_visible()

@builtin("remove-if")
def remove_if(fn, L):
    return list(filter(lambda object: not fn(object), L))

@builtin("all-objects")
def all_objects():
    return list(map(lambda object: object.id, model.objects))

@builtin("apply-all")
def apply_all(fn, L):
    for elt in L:
        fn(L)

@builtin("map")
def _map(fn, L):
    return list(map(fn, L))

@builtin
def identity(arg):
    return arg

@builtin("zero?")
def zerop(arg):
    return arg == 0

@builtin
def length(L):
    return len(L)

@builtin("do-nothing")
def do_nothing(*args):
    pass

@builtin
def innodes(object_id, relation_id):
    "Returns the number of nodes with edges pointing to an object."
    try:
        innodes_list = list(model.object_get_innodes(object_id, relation_id))
    except:
        innodes_list = []
    return innodes_list

@builtin
def outnodes(object_id, relation_id):
    "Returns the number of nodes with edges pointing from an object."
    return list(model.outnodes(object_id, relation_id))

@builtin
def echo(*args):
    "Prints its symbolic and numeric arguments separated by a space."
    params = list(map(str, args))
    log.info(' '.join(params))

@builtin("make-object-filter")
def make_object_filter(title, predicate):
    return model.make_object_filter(title, predicate)

@builtin("delete-object-filter")
def delete_object_filter(object_filter_id):
    model.delete_object_filter(object_filter_id)

@builtin("find-first")
def find_first(predicate, L):
    for elt in L:
        if predicate(elt):
            return elt

@builtin("all-relations")
def all_relations():
    return model.get_relations()

@builtin("relation-name")
def relation_name(relation_id):
    return model.relation_get_name(relation_id)

@builtin("printf")
def printf(fmt, *args):
    log.info(fmt, *args)

class BufferedReader(object):
    def __init__(self, file):
        self.file = file
        self.buf = ""
        self.pos = 0
        self._eof = False
    
    def _fill(self):
        if self.pos == len(self.buf):
            self.buf = self.file.read(4096)
            self.pos = 0
            self._eof = not bool(self.buf)
        return not self._eof
    
    def peek(self):
        if not self._fill():
            return ''
        return self.buf[self.pos]
    
    def eof(self):
        return not self._fill()
    
    def get(self):
        if not self._fill():
            return ''
        ch = self.buf[self.pos]
        self.pos += 1
        return ch

class Lexer(object):
    def __init__(self, br):
        self.br = br
    
    def match_any(self, tokens):
        ch = self.br.get()
        if ch not in tokens:
            raise SyntaxError("Expected token in {0}, got {1}".format(tokens, ch))
    
    def match(self, str):
        for ch in str:
            self.match_any(ch)

# whitespace = " \r\n\t"
# letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
# digits = "0123456789"

symbol_start = string.ascii_letters + "!@#$%^&*-_+=|\~?<>/\\"
symbol_chars = symbol_start + string.digits

class State(object):
    COMMENT     = 1
    NUMBER      = 3
    QUOTE       = 4
    STRING      = 5
    SYMBOL      = 6
    WHITESPACE  = 7
    ESCAPE      = 8

def read_lexeme(br):
    state = State.WHITESPACE
    ch = br.peek()
    token = ""
    while True:
        if state == State.WHITESPACE:
            if br.eof():
                return Lexeme.eof()
            ch = br.peek()
            if ch == '#':
                state = State.COMMENT
            elif ch == '\'':
                br.get()
                return Lexeme.quote()
            elif ch == '"':
                state = State.STRING
                br.get()
            elif ch in string.ascii_letters or ch in symbol_start:
                state = State.SYMBOL
            elif ch in string.digits or ch == '.':
                state = State.NUMBER
            elif ch == '(':
                br.get()
                return Lexeme.left_paren()
            elif ch == ')':
                br.get()
                return Lexeme.right_paren()
            elif ch not in string.whitespace:
                raise SyntaxError("Unexpected character: {0}".format(ch))
            else:
                br.get()
        elif state == State.COMMENT:
            if br.eof():
                return Lexeme.eof()
            ch = br.get()
            if ch == '\n':
                state = State.WHITESPACE
        elif state == State.NUMBER:
            if br.eof():
                return Lexeme.number(token)
            ch = br.peek()
            if ch in string.digits:
                token += br.get()
            else:
                return Lexeme.number(token)
        elif state == State.STRING:
            if br.eof():
                return Lexeme.error("Unexpected EOF")
            ch = br.peek()
            if ch == '"':
                br.get()
                return Lexeme.string(token)
            elif ch == '\\':
                state = State.ESCAPE
            else:
                token += br.get()
        elif state == State.ESCAPE:
            if br.eof():
                return Lexeme.error("Unexpected EOF")
            token += br.get()
            state = State.STRING
        elif state == State.SYMBOL:
            if br.eof():
                return Lexeme.symbol(token)
            ch = br.peek()
            if ch in symbol_chars:
                token += br.get()
            else:
                return Lexeme.symbol(token)

class Lexer(object):
    def __init__(self, br):
        self.br = br
        self.lexeme = read_lexeme(self.br)
    
    def accept(self):
        self.lexeme = read_lexeme(self.br)
    
    def match(self, lexeme_type):
        if self.lexeme.type != lexeme_type:
            raise SyntaxError("Expected lexeme {0}, got {1}".format(lexeme_type, self.lexeme.type))
        self.lexeme = read_lexeme(self.br)
    
    def peek(self):
        return self.lexeme

class Symbol(object):
    def __init__(self, name):
        self.name = name
    
    def __repr__(self):
        return self.name
    
    def __eq__(self, other):
        if type(other) == str:
            return self.name == other
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

def read_sexpr(lexer):
    lexeme = lexer.peek()
    typ = lexeme.type
    if typ == Lexeme.LPAREN:
        lexer.accept()
        return read_list(lexer)
    elif typ == Lexeme.SYMBOL:
        lexer.accept()
        return Symbol(lexeme.token)
    elif typ == Lexeme.NUMBER:
        lexer.accept()
        return int(lexeme.token)
    elif typ == Lexeme.STRING:
        lexer.accept()
        return lexeme.token
    else:
        raise SyntaxError("Unexpected lexeme: {0}".format(lexeme))

def read_list(lexer):
    L = []
    done = False
    while not done:
        lexeme = lexer.peek()
        if lexeme.type == Lexeme.EOF or lexeme.type == Lexeme.ERROR or lexeme.type == Lexeme.RPAREN:
            done = True
        else:
            L.append(read_sexpr(lexer))
    lexeme = lexer.peek()
    if lexeme.type != Lexeme.RPAREN:
        raise SyntaxError("Expected ')' lexeme, got {0}".format(lexeme))
    lexer.accept()
    return L

def read(file):
    if type(file) == str:
        with io.StringIO(file) as fp:
            br = BufferedReader(fp)
            lexer = Lexer(br)
            return read_sexpr(lexer)
    else:
        br = BufferedReader(file)
        lexer = Lexer(br)
        return read_sexpr(lexer)

class Lexeme(object):
    EOF    = 0
    LPAREN = 1
    NUMBER = 2
    QUOTE  = 3
    RPAREN = 4
    STRING = 5
    SYMBOL = 6
    ERROR  = 7

    def __init__(self, type, token, line=0):
        self.type = type
        self.token = token
        self.line = line
    
    @staticmethod
    def eof(line=0):
        return Lexeme(Lexeme.EOF, "", line)
    
    @staticmethod
    def quote(line=0):
        return Lexeme(Lexeme.QUOTE, "'", line)
    
    @staticmethod
    def left_paren(line=0):
        return Lexeme(Lexeme.LPAREN, "(", line)
    
    @staticmethod
    def right_paren(line=0):
        return Lexeme(Lexeme.RPAREN, ")", line)
    
    @staticmethod
    def number(token, line=0):
        return Lexeme(Lexeme.NUMBER, token, line)
    
    @staticmethod
    def string(token, line=0):
        return Lexeme(Lexeme.STRING, token, line)
    
    @staticmethod
    def symbol(token, line=0):
        return Lexeme(Lexeme.SYMBOL, token, line)
    
    @staticmethod
    def error(message, line=0):
        return Lexeme(Lexeme.ERROR, message, line)