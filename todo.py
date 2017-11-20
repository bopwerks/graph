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
        for receiver in self._parent.connections():
            if receiver is not sender:
                dispatch(MessageType.UPDATE, sender, receiver, self._name)

    def __str__(self):
        return str(self._value)

    def __repr__(self):
        return repr(self._value)

    def __hash__(self):
        return hash(self._value)

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
        return type(value) == bool

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
        for fieldname in self._fields():
#            print("Adding instance of {0} named {1}".format(self.__getType(fieldname), fieldname))
            self.__dict__[fieldname] = self.__getType(fieldname)(parent=self, name=fieldname)

    def field(name):
        """Helper function"""
        field = self.__dict__.get(name, None)
        return (type(self), field)

    def fields(self):
        return [self.__dict__[f] for f in self._fields()]

    def _fields(self):
        fields = []
#        print(type(self))
#        print(dir(type(self)))
        for fieldname in dir(type(self)):
            if fieldname.startswith("_"):
                continue
            T = self.__getType(fieldname)
            if not T or type(T) != type:
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
        for name in self._fields():
            type = self.__getType(name)
            rval += " {0}={1}".format(name, type.__name__)
        rval += ">"
        return rval

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

def set_value(fieldset, fieldname, value):
    assert isinstance(fieldset, FieldSet)
    assert fieldname in fieldset.__dict__
    assert isinstance(fieldset.__dict__[fieldname], Field)
    return fieldset.__dict__[fieldname].setValue(value)

def get_value(fieldset, fieldname):
    return fieldset.__dict__[fieldname].value()

class Edge(Connectable, FieldSet):
    Weight = Number
    
    def __init__(self, source, dest, value=None):
        Connectable.__init__(self)
        FieldSet.__init__(self)

class GraphicalEdge(QtWidgets.QGraphicsItemGroup, Connectable, FieldSet):
    X1 = Number
    Y1 = Number
    X2 = Number
    Y2 = Number
    
    def __init__(self, source, dest):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        Connectable.__init__(self)
        FieldSet.__init__(self)
        self._source = source
        self._dest = dest
        self.X1.setValue(self._source.x())
        self.Y1.setValue(self._source.y())
        self.X2.setValue(self._dest.x())
        self.Y2.setValue(self._dest.y())
        self._line = QtWidgets.QGraphicsLineItem(self._source.x(),
                                                 self._source.y(),
                                                 self._dest.x(),
                                                 self._dest.y())
        self.addToGroup(self._line)


class Node(Connectable, FieldSet):
    Title = Text
    Urgent = Boolean
    Important = Boolean

#    __node_id = 0
    def __init__(self, title="", urgent=True, important=True):
        Connectable.__init__(self)
        FieldSet.__init__(self)
#        Node.__node_id += 1
#        self._id = Node.__node_id
        
        self.Title.setValue(title)
        self.Urgent.setValue(urgent)
        self.Important.setValue(important)
        self._edges = set()

    def setUrgent(self, urgentp, sender):
        self.Urgent.setValue(urgentp, sender)

    def urgent(self):
        return self.Urgent.value()

    def setImportant(self, importantp, sender=None):
        self.Important.setValue(importantp, sender if sender else self)

    def important(self):
        return self.Important.getValue()

    def id(self):
        return self._id

    def title(self):
        return self.Title.value()

    def setTitle(self, title, sender=None):
        return self.Title.setValue(title, sender if sender else self)

    def __hash__(self):
        return (hash(self.Title) ^
#                hash(self._id) ^
                hash(self.Urgent) ^
                hash(self.Important))

    def __str__(self):
        return "Node({0}, {1}, {2})".format(repr(self.Title),
                                            repr(self.Urgent),
                                            repr(self.Important))


class NodeTableModel(QtCore.QAbstractTableModel, Connectable):
    def __init__(self):
        super().__init__()
        self._nodes = []

    def addNode(self, node):
        self._nodes.append(node)
        self.connect(node)

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

selectedNode = None

class GraphicalNode(QtWidgets.QGraphicsItemGroup, Connectable, FieldSet):
    X        = Number
    Y        = Number
    Selected = Boolean
    Text     = Text
    
    def __init__(self, title=""):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        Connectable.__init__(self)
        FieldSet.__init__(self)

        self._ellipse = QtWidgets.QGraphicsEllipseItem(0, 0, 100, 100)
        self.addToGroup(self._ellipse)
        self._text = QtWidgets.QGraphicsSimpleTextItem(title)
        self._text.setPos(25, 25)
        self.addToGroup(self._text)
        self.Selected.setValue(False)
        self._dx = 0
        self._dy = 0
        self._id = 0

    def x(self):
        return self.X.value()

    def y(self):
        return self.Y.value()

    def setText(self, text):
        self.Text.setValue(text)
        self._text.setText(text)

    def mousePressEvent(self, event):
        selectedNode = self
        self.Selected.setValue(True)
        mouse = event.scenePos()
        pos = self.scenePos()
        self._dx = mouse.x() - pos.x()
        self._dy = mouse.y() - pos.y()
        event.accept()

    def mouseReleaseEvent(self, event):
        selectedNode = None
        mouse = event.scenePos()
        self.Selected.setValue(False)
        self.X.setValue(mouse.x() - self._dx)
        self.Y.setValue(mouse.y() - self._dy)
        event.accept()

    def mouseMoveEvent(self, event):
        mouse = event.scenePos()
        newpos = QtCore.QPointF(mouse.x() - self._dx, mouse.y() - self._dy)
        self.setPos(newpos)
        self.X.setValue(newpos.x())
        self.Y.setValue(newpos.y())
        event.accept()

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

    # def mousePressEvent(self, event):
    #     pos = event.pos()
    #     selecteditem = self.itemAt(pos.x(), pos.y())
    #     if selecteditem:
    #         event.ignore()
    #         return
    #     event.accept()

class GraphicalNodeScene(QtWidgets.QGraphicsScene):
    def __init__(self):
        super().__init__()
        self._nodes = []
        
    def addNode(self, node):
        self._nodes.append(node)
        gnode = GraphicalNode()
        node.connect(gnode)
        self.addItem(gnode)

#    def mousePressEvent(self, event):
#        print("Selected node: {0}".format(selectedNode))
#        event.ignore()

#    def onClick(self, event):
#        for node in self._nodes:
#            title = node.title()
#            node.setTitle(title[-1] + title[0:-1], self)

class NodeSet(Connectable):
    Size = Number
    Updated = Boolean
    
    def __init__(self):
        Connectable.__init__(self)
        self._nodes = set()

    def nodes(self):
        return list(self._nodes)

    def add(self, node):
        self._nodes.add(node)
        node.connect(self)

    def remove(self, node):
        self._nodes.remove(node)
        node.disconnect(self)

class NodeTableView(QtWidgets.QTableView):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.setModel(model)
        self.setSortingEnabled(True)
        model.dataChanged.connect(self.update)
        
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, title):
        super().__init__()

        self._nodes = NodeSet()

        # set size to 70% of screen
        self.resize(QtWidgets.QDesktopWidget().availableGeometry(self).size() * 0.7)

        # set up scene
        #self._scene = QtWidgets.QGraphicsScene()
        self._scene = GraphicalNodeScene()
        self._scene.setSceneRect(0, 0, 500, 500)

        # create and add a node to the scene
        self._node1 = Node("jesse")
        self._gnode1 = GraphicalNode("jesse")
        self._node1.connect(self._gnode1)
        self._scene.addItem(self._gnode1)
        
        self._node2 = Node("alyssa")
        self._gnode2 = GraphicalNode("alyssa")
        self._node2.connect(self._gnode2)
        self._scene.addItem(self._gnode2)
        
        self._edge = GraphicalEdge(self._gnode1, self._gnode2)
        self._gnode1.connect(self._edge)
        self._gnode2.connect(self._edge)
        self._scene.addItem(self._edge)

        # add the scene to the view
        #self._view = QtWidgets.QGraphicsView(self._scene)
        self._view = GraphicalNodeView(self._scene)
        #self._view.addClickListener(self._scene)

        # make the view the main widget of the window
        self.setCentralWidget(self._view)

        # add a dock with a list
        self._dock = QtWidgets.QDockWidget("Task Browser")
        #self._table = QtWidgets.QTableView(self._dock)
        #self._model = NodeTableModel()
        #self._model.addNode(self._node)
        #self._table.setModel(self._model)
        #self._table.resizeRowsToContents()
        #self._model.dataChanged.connect(self._table.update)
        #self._list = QtWidgets.QListWidget(self._dock)
        self._nodeset = NodeSet()
        self._nodeset.add(self._node1)
        self._nodeset.add(self._node2)
        self._list = GraphicalNodeList(self._nodeset)
        #lines = ['a', 'b', 'c']
        #self._list.addItems(lines)
        self._dock.setWidget(self._list)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._dock)

        self.setWindowTitle(title)

        self._toolbar = self.addToolBar("Node")
        print(self._toolbar)
        self._newIcon = QtGui.QIcon.fromTheme("document-new", QtGui.QIcon(":/images/new.png"))
        self._newAction = QtWidgets.QAction(self._newIcon, "&New", self)
        #self._newAction.setText("New")
        self._newAction.triggered.connect(self.newNode)

        #connect(newAct, &QAction::triggered, this, &MainWindow::newFile);
        self._toolbar.addAction(self._newAction)

    def newNode(self):
        node = Node("")
        gnode = GraphicalNode("")
        self._nodes.add(node)
        node.connect(gnode)
        self._scene.addItem(gnode)

class GraphicalNodeList(QtWidgets.QListWidget, Connectable):
    def __init__(self, nodeset):
        QtWidgets.QListWidget.__init__(self)
        Connectable.__init__(self)
        self._nodeset = nodeset
        self.connect(self._nodeset)
        self.addItems([str(node) for node in self._nodeset.nodes()])
    
@update(Node, "Title", GraphicalNode)
def node_title_updated_for_graphical_node(node, gnode):
    gnode.setText(node.title())

@update(GraphicalNode, "X", Node)
def graphical_node_x_changed(gnode, node):
    node.setTitle("({0}, {1})".format(gnode.x(), gnode.y()))

@update(GraphicalNode, "Y", Node)
def graphical_node_y_changed_for_node(gnode, node):
    node.setTitle("({0}, {1})".format(gnode.x(), gnode.y()))

@update(GraphicalNode, "X", GraphicalEdge)
def graphical_node_x_changed_for_graphical_edge(gnode, gedge):
    if gnode is gedge._source:
        gedge.X1.setValue(gnode.x(), gnode)
        gedge.Y1.setValue(gnode.y(), gnode)
        gedge._line.setLine(gedge.X1.value() + 50,
                            gedge.Y1.value() + 50,
                            gedge.X2.value() + 50,
                            gedge.Y2.value() + 50)
    elif gnode is gedge._dest:
        gedge.X2.setValue(gnode.x(), gnode)
        gedge.Y2.setValue(gnode.y(), gnode)
        gedge._line.setLine(gedge.X1.value() + 50,
                            gedge.Y1.value() + 50,
                            gedge.X2.value() + 50,
                            gedge.Y2.value() + 50)
    else:
        assert False

@connect(Node, GraphicalNode)
def node_connects_to_graphical_node(node, gnode):
    gnode.setText(node.title())

@connect(GraphicalNode, GraphicalEdge)
def graphical_node_connects_to_graphical_edge(gnode, gedge):
    if gnode is gedge._source:
        gedge.X1.setValue(gnode.x(), gnode)
        gedge.Y1.setValue(gnode.y(), gnode)
        gedge._line.setLine(gedge.X1.value() + 50,
                            gedge.Y1.value() + 50,
                            gedge.X2.value() + 50,
                            gedge.Y2.value() + 50)
    elif gnode is gedge._dest:
        gedge.X2.setValue(gnode.x(), gnode)
        gedge.Y2.setValue(gnode.y(), gnode)
        gedge._line.setLine(gedge.X1.value() + 50,
                            gedge.Y1.value() + 50,
                            gedge.X2.value() + 50,
                            gedge.Y2.value() + 50)
    else:
        assert False

@disconnect(GraphicalNode, GraphicalEdge)
def graphical_node_disconnects_from_graphical_edge(gnode, gedge):
    pass
    
app = QtWidgets.QApplication(sys.argv)
win = MainWindow("To-Done")
win.show()
app.exec_()

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
    
