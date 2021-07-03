import operator
import model

"""
;; Example code for implementing a "Tag" object whose checkbox field
;; changes the visibility of "tagged" (connected) objects.
(lambda (object-id checkedp)
  (let (tagged-objects (bfs object-id))
    (if checkedp
        (hide-objects tagged-objects object-id)
        (show-objects tagged-objects object-id))))
"""

def _tokenize(str):
    "Convert a string into a list of tokens."
    return str.replace('(', ' ( ').replace(')', ' ) ').split()

def _atom(token):
    "Numbers become numbers; every other token is a symbol."
    try: return int(token)
    except ValueError:
        try: return float(token)
        except ValueError:
            return str(token)

def _read_from_tokens(tokens):
    "Read an expression from a sequence of tokens."
    if len(tokens) == 0:
        raise SyntaxError('unexpected EOF')
    token = tokens.pop(0)
    if token == '(':
        L = []
        while tokens[0] != ')':
            L.append(_read_from_tokens(tokens))
        tokens.pop(0) # pop off ')'
        return L
    elif token == ')':
        raise SyntaxError('unexpected )')
    else:
        return _atom(token)

def read(str):
    "Convert a string into an s-expression."
    return _read_from_tokens(_tokenize(str))

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
    if type(expr) in (int, float):
        return expr
    elif type(expr) == str:
        return env.find(expr)[expr]
    op, *args = expr
    if op == "lambda":
        return Procedure(args[0], args[1:], env)
    elif op == "quote":
        return args[0]
    elif op == "if":
        return eval(args[1], env) if eval(args[0], env) else eval(args[2], env)
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

@builtin("all-objects")
def all_objects():
    return list(map(lambda object: object.id, model.objects))

# try:
#     print(eval(read("(if 0 2 3)")))
# except Exception as e:
#     print("Error: {0}".format(e))