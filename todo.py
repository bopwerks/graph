# todo.py -- A todo list program.
import sys
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui

class Connectable(object):
    def __init__(self):
        self._connections = set()
        
    def connect(self, connectable):
        self._connections.add(connectable)
        connectable._connections.add(self)
        dispatch(MessageType.CONNECT, self, connectable)

    def disconnect(self, connectable):
        dispatch(MessageType.DISCONNECT, self, connectable)
        try:
            self._connections.remove(connectable)
        except KeyError:
            pass
        try:
            connectable._connections.remove(self)
        except KeyError:
            pass

    def connections(self):
        return self._connections

    def __del__(self):
        for receiver in self.connections():
            dispatch(MessageType.DISCONNECT, self, receiver)
        self._connections.clear()

class Field(object):
    def __init__(self, initialValue=None, parent=None, name=""):
        if type(initialValue) == type(self):
            return initialValue
        self._value = initialValue
        self._parent = parent
        self._name = name

    def _satisfiesConstraint(self, value):
        return True

    def setValue(self, value, sender=None):
        if not self._satisfiesConstraint(value):
            raise TypeError("Value {0} is not a {1}".format(value, self))
        self._value = value
        self._publish(sender if sender else self._parent)

    def value(self):
        return self._value

    def _publish(self, sender):
        assert self._value
        for receiver in self._parent.connections():
            if receiver is not sender:
                dispatch(MessageType.UPDATE, sender, receiver, self._name)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

class Number(Field):
    def __init__(self, initialValue=0.0, parent=None, name=""):
        super().__init__(initialValue, parent, name)

    def _satisfiesConstraint(self, value):
        return type(value) == int or type(value) == float

    def fromString(sval):
        try:
            value = float(sval)
        except ValueError:
            raise TypeError("String {0} cannot be converted to a number".format(repr(sval)))
        return Number(value)

class Boolean(Field):
    def __init__(self, initialValue=False, parent=None, name=""):
        super().__init__(initialValue, parent, name)

    def _satisfiesConstraint(self, value):
        return type(value) == int or type(value) == float

    def fromString(sval):
        sval = sval.lower()
        if sval == "true":
            return Boolean(True)
        elif sval == "false":
            return Boolean(False)
        else:
            raise TypeError("String {0} cannot be converted to a boolean".format(repr(sval)))

class Text(Field):
    def __init__(self, initialValue="", parent=None, name=""):
        super().__init__(initialValue, parent, name)

    def _satisfiesConstraint(self, value):
        return type(value) == str

    def fromString(sval):
        return Text(sval)

# TODO: Replace this with a function that generates a unique class
class Range(Field):
    def __init__(self, valuetype, minval, maxval, parent):
        assert valuetype == Text or valuetype == Number
        super().__init__(self, minval, parent)
        self._type = valuetype
        self._min = valuetype(minval)
        self._max = valuetype(maxval)

    def _satisfiesConstraint(self, value):
        return type(value) == valuetype and \
            self._min.value() <= value and \
            value <= self._max.value()

    def fromString(sval):
        assert False

class FieldSet(object):
    def __init__(self):
        for fieldname in self.__fields():
#            print("Adding instance of {0} named {1}".format(self.__getType(fieldname), fieldname))
            self.__dict__[fieldname] = self.__getType(fieldname)(parent=self, name=fieldname)

    def field(name):
        """Helper function"""
        field = self.__dict__.get(name, None)
        return (type(self), field)

    def fields(self):
        return [self.__dict__[f] for f in self.__fields()]

    def __fields(self):
        fields = []
        for fieldname in dir(type(self)):
            if fieldname.startswith("_"):
                continue
            T = self.__getType(fieldname)
            if not T:
                continue
#            print(T)
            if not issubclass(T, Field):
                continue
            fields.append(fieldname)
        return fields

    def __getType(self, fieldname):
        if fieldname not in type(self).__dict__:
            return None
        return type(self).__dict__[fieldname]

    def __str__(self):
        rval = "<{0}".format(self.__class__.__name__)
        for name in self.__fields():
            type = self.__getType(name)
            rval += " {0}={1}".format(name, type.__name__)
        rval += ">"
        return rval

class Node(FieldSet):
    Title = Text
    Urgent = Boolean
    Important = Boolean


class MessageType(object):
    CONNECT    = 1
    DISCONNECT = 2
    UPDATE     = 3

dispatchtab = {
    MessageType.CONNECT:    {},
    MessageType.DISCONNECT: {},
    MessageType.UPDATE:     {}
}

def update(sender, fieldname, receiver):
    def decorate(action):
        table = dispatchtab[MessageType.UPDATE]
        if sender not in table:
            table[sender] = {}
        table = table[sender]
        if fieldname not in table:
            table[fieldname] = {}
        table = table[fieldname]
        if receiver not in table:
            table[receiver] = set()
        table[receiver].add(action)
#        print(dispatchtab)
        return action
    return decorate

def connect(sender, receiver):
    def decorate(action):
        table = dispatchtab[MessageType.CONNECT]
        if sender not in table:
            table[sender] = {}
        table = table[sender]
        if receiver not in table:
            table[receiver] = set()
        table[receiver].add(action)
#        print(dispatchtab)
        return action
    return decorate

def disconnect(sender, receiver):
    def decorate(action):
        table = dispatchtab[MessageType.DISCONNECT]
        if sender not in table:
            table[sender] = {}
        table = table[sender]
        if receiver not in table:
            table[receiver] = set()
        table[receiver].add(action)
#        print(dispatchtab)
        return action
    return decorate

def dispatch(message, sender, receiver, field=""):
#    print("dispatch({0}, {1}, {2}, {3})".format(repr(message),
#          repr(sender), repr(receiver), repr(field)))
    actions = dispatchtab.get(message, {}).get(type(sender), {})
    if field:
        actions = actions.get(field, {}).get(type(receiver), [])
    else:
        actions = actions.get(type(receiver), [])
    for action in actions:
        action(sender, receiver)



class Person(Connectable, FieldSet):
    Name = Text
    Age = Number

    def __init__(self):
        Connectable.__init__(self)
        FieldSet.__init__(self)

class GraphicalPerson(Connectable):
    def __init__(self):
        Connectable.__init__(self)

@update(Person, "Name", GraphicalPerson)
def onNameUpdate(person, gperson):
    print("GraphicalPerson notified that Person name is now {0}".format(person.Name.value()))

@update(Person, "Age", GraphicalPerson)
def onAgeUpdate(person, gperson):
    print("GraphicalPerson notified that Person age is now {0}".format(person.Age.value()))

@disconnect(Person, GraphicalPerson)
def onPersonDisconnect(person, gperson):
    print("GraphicalPerson notified that Person disconnected")

def set_value(fieldset, fieldname, value):
    assert isinstance(fieldset, FieldSet)
    assert fieldname in fieldset.__dict__
    assert isinstance(fieldset.__dict__[fieldname], Field)
    return fieldset.__dict__[fieldname].setValue(value)

def get_value(fieldset, fieldname):
    return fieldset.__dict__[fieldname].value()

#print("Making a Person")
p = Person()

#print("Setting name to Jesse")
p.Name.setValue("Jesse")

#print("Setting age to 29")
p.Age.setValue(29)

#print("Making a GraphicalPerson")
gp = GraphicalPerson()

#print("Connecting Person to GraphicalPerson")
p.connect(gp)

#print("Setting age to 30")
p.Age.setValue(30)

#print("Disconnecting Person from GraphicalPerson")
p.disconnect(gp)

#print("Setting age to 40")
p.Age.setValue(40)

#print("Disconnecting GraphicalPerson from Person")
gp.disconnect(p)

#print("Setting name to John")
p.Name.setValue("John")

#print("Deleting GraphicalPerson")
del gp

#print("Setting age to 42")
p.Age.setValue(42)

NODES = set()
EDGES = set()

class Edge(object):
    def __init__(self, source, dest, value=None, *listeners):
        EDGES.add(self)
        self._source = source
        self._dest = dest
        self._value = value
        self._listeners = set(listeners)

    def source(self):
        return self._source

    def destination(self):
        return self._dest

    def value(self):
        return self._value

    def addListener(self, listener):
        self._listeners.add(listener)

    def setValue(self, value, setter):
        self._value = value
        node = self.other(setter)
        if node:
            node.onEdgeUpdate(setter)
            return
        for listener in listeners:
            if listener != setter:
                setter.onEdgeUpdate(setter)

    def onNodeUpdate(self, node):
        # TODO: use node's value to compute new value
        newvalue = None
        self.setValue(newvalue, node)

    def other(self, requester):
        if requester is self._source:
            return self._dest
        elif requester is self._dest:
            return self._source
        else:
            return None

class GraphicalEdge(QtWidgets.QGraphicsItemGroup):
    def __init__(self):
        super().__init__()
        self._x1 = 0
        self._y1 = 0
        self._x2 = 0
        self._y2 = 0
        self._line = QGraphicsLineItem(0, 0, 0, 0)

    def onEdgeUpdate(self, edge):
        # TODO: update graphics according to edge data
        self._line
        pass

class Node(object):
    __node_id = 0
    def __init__(self, title="", urgent=True, important=True, *listeners):
        Node.__node_id += 1
        self._id = Node.__node_id
        self._title = title
        self._urgentp = urgent
        self._importantp = important
        self._listeners = set(listeners)
        self._edges = set()
        self._publish(self)
        NODES.add(self)

    def addListener(self, listener):
        self._listeners.add(listener)
        listener.onNodeUpdate(self)

    def setUrgent(self, urgentp, sender):
        self._urgentp = urgentp
        self._publish(sender)

    def urgent(self):
        return self._urgentp

    def setImportant(self, importantp, sender):
        self._importantp = importantp
        self._publish(sender)

    def important(self):
        return self._importantp

    def id(self):
        return self._id

    def setId(self, id, sender):
        self._id = id
        self._publish(sender)

    def title(self):
        return self._title

    def setTitle(self, title, sender):
        self._title = title
        self._publish(sender)

#    def onEdgeUpdate(self, updater):
#            if edge is not updater:

    def _publish(self, sender):
        for listener in self._listeners:
            if listener != sender:
                listener.onNodeUpdate(self)

    def __hash__(self):
        return (hash(self._title) ^
                hash(self._id) ^
                hash(self._urgentp) ^
                hash(self._importantp))

    def __str__(self):
        rval = "Node({0}, {1}, {2}".format(repr(self._title),
                                           repr(self._urgentp),
                                           repr(self._importantp))
        if self._listeners:
            rval += ", "
        for listener in self._listeners:
            rval += repr(listener)
        rval += ")"
        return rval

class NodeTableModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._nodes = []

    def addNode(self, node):
        self._nodes.append(node)
        node.addListener(self)

    def onNodeUpdate(self, node):
        #self.emit(QtCore.SIGNAL("dataChanged"))
        topleft = self.createIndex(0, 0)
        btmright = self.createIndex(2, len(self._nodes))
        self.dataChanged.emit(topleft, btmright)
        
    def rowCount(self, blerp):
        return len(self._nodes)

    def columnCount(self, blerp):
        return 3

    def data(self, index, blerp):
        row = index.row()
        field = { 0: "_title", 1: "_urgentp", 2: "_importantp" }[index.column()]
        return self._nodes[row].__dict__[field]

    def setData(self, index, value):
        node = self._nodes[index.row()]
        field = { 0: "setTitle", 1: "setUrgent", 2: "setImportant" }[index.column()]
        node.__dict__[field](node, value)

class GraphicalNode(QtWidgets.QGraphicsItemGroup):
    def __init__(self):
        super().__init__()
        self._ellipse = QtWidgets.QGraphicsEllipseItem(0, 0, 100, 100)
        self.addToGroup(self._ellipse)
        self._text = QtWidgets.QGraphicsSimpleTextItem("")
        self.addToGroup(self._text)
        self._selected = False
        self._dx = 0
        self._dy = 0
        self._id = 0

    def onNodeUpdate(self, node):
        self._id = node.id()
        self._text.setText(node.title())

    def mousePressEvent(self, event):
        self._selected = True
        mouse = event.scenePos()
        pos = self.scenePos()
        self._dx = mouse.x() - pos.x()
        self._dy = mouse.y() - pos.y()

    def mouseReleaseEvent(self, event):
        self._selected = False

    def mouseMoveEvent(self, event):
        mouse = event.scenePos()
        newpos = QtCore.QPointF(mouse.x() - self._dx, mouse.y() - self._dy)
        self.setPos(newpos)

class GraphicalNodeView(QtWidgets.QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self._selected = False
        self._listeners = []

    def wheelEvent(self, event):
        point = event.angleDelta()
        dy = point.y()
        #print("({0}, {1})".format(point.x(), point.y()))
        if dy > 0:
            self.scale(1.1, 1.1)
        elif dy < 0:
            self.scale(1/1.1, 1/1.1)

    def mousePressEvent(self, event):
        # self._selected = True
        # mouse = event.pos()
        # self._dx = mouse.x()
        # self._dy = mouse.y()
        #for node in self._nodes:
        #    title = node.title()
        #    node.setTitle(title[-1] + title[0:-1])
        for listener in self._listeners:
            listener.onClick(event)

    def addClickListener(self, listener):
        self._listeners.append(listener)

    # def mouseReleaseEvent(self, event):
    #     self._selected = False
        
    # def mouseMoveEvent(self, event):
    #     if not self._selected:
    #         return
    #     mouse = event.pos()
    #     #newpos = QtCore.QPointF(mouse.x() - self._dx, mouse.y() - self._dy)
    #     rect = self.sceneRect()
    #     x = -(mouse.x() - self._dx)
    #     y = (mouse.y() - self._dy)
    #     w = rect.width()
    #     h = rect.height()
    #     self.setSceneRect(x, y, w, h)

# task1 = Task("write todo app")
# task2 = Task("do dishes")
# task3 = Task("study")
# edge1 = before(task2, task1)
# edge2 = after(task2, task3)
# assert edge1 is edge(task1, task2)
# del edge(task1, task)
# all_tasks = tasks()

# breadth-first traversal
# marked = {}
# frontier = [task1]
# while frontier:
#     task = frontier.pop()
#     if task in  marked:
#         continue
#     marked[task] = True
#     print task
#     for neighbor in task.neighborsOfType(Task):
#         if neighbor not in marked:
#             frontier.insert(0, neighbor)
    
class GraphicalNodeScene(QtWidgets.QGraphicsScene):
    def __init__(self):
        super().__init__()
        self._nodes = []
        
    def addNode(self, node):
        self._nodes.append(node)
        gnode = GraphicalNode()
        node.addListener(gnode)
        self.addItem(gnode)

    def onClick(self, event):
        for node in self._nodes:
            title = node.title()
            node.setTitle(title[-1] + title[0:-1], self)

class NodeSet(object):
    def __init__(self):
        self._nodes = set()

    def nodes(self):
        return set(self._nodes)

    def addNode(self, node):
        self._nodes.add(node)

class NodeTableView(QtWidgets.QTableView):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.setModel(model)
        self.setSortingEnabled(True)
        model.dataChanged.connect(self.update)
        
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, title):
        super().__init__()

        # set size to 70% of screen
        self.resize(QtWidgets.QDesktopWidget().availableGeometry(self).size() * 0.7)

        # set up scene
        #self._scene = QtWidgets.QGraphicsScene()
        self._scene = GraphicalNodeScene()
        self._scene.setSceneRect(0, 0, 500, 500)

        # create and add a node to the scene
        self._node = Node("abc")
        print(self._node)
        self._scene.addNode(self._node)
        #self._node = GraphicalNode("hello")
        #self._scene.addItem(self._node)

        # add the scene to the view
        #self._view = QtWidgets.QGraphicsView(self._scene)
        self._view = GraphicalNodeView(self._scene)
        self._view.addClickListener(self._scene)

        # make the view the main widget of the window
        self.setCentralWidget(self._view)

        # add a dock with a list
        self._dock = QtWidgets.QDockWidget("Task Browserr")
        self._table = QtWidgets.QTableView(self._dock)
        self._model = NodeTableModel()
        self._model.addNode(self._node)
        self._table.setModel(self._model)
        self._table.resizeRowsToContents()
        #self._model.dataChanged.connect(self._table.update)
        #self._list = QtWidgets.QListWidget(self._dock)
        #lines = ['a', 'b', 'c']
        #self._list.addItems(lines)
        self._dock.setWidget(self._table)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._dock)

        self.setWindowTitle(title)
    
#app = QtWidgets.QApplication(sys.argv)
#win = MainWindow("To-Done")
#win.show()
#app.exec_()
