# todo.py -- A todo list program.
import math
import sys
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
#from PyQt5 import Qt3DCore

class Connectable(object):
    """Connectable notifies another Connectable when it has connected or disconnected."""
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
    """Field holds a value and is a member of a field group.

    Field notifies all registered listeners when it changes value.

    """
    def __init__(self, initialValue=None, parent=None, name=""):
        if type(initialValue) == type(self):
            return initialValue
        self._value = initialValue
        self._parent = parent
        self._name = name

    def _satisfiesConstraint(self, value):
        raise NotImplementedError("Field is an abstract class which lacks a constraint")

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

def sign(n):
    return -1 if n < 0 else 1

class GraphicalEdge(QtWidgets.QGraphicsItemGroup, Connectable, FieldSet):
    X1 = Number
    Y1 = Number
    X2 = Number
    Y2 = Number
    
    def __init__(self, source=None, dest=None, radius=0, alpha=0):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        Connectable.__init__(self)
        FieldSet.__init__(self)
        self._source = source
        self._dest = dest
        self._radius = radius
        self._alpha = alpha
        self.X1.setValue(self._source.x() if source else 0)
        self.Y1.setValue(self._source.y() if source else 0)
        self.X2.setValue(self._dest.x() if dest else 0)
        self.Y2.setValue(self._dest.y() if dest else 0)
        # self._line = QtWidgets.QGraphicsLineItem(self._source.x() if source else 0,
        #                                          self._source.y() if source else 0,
        #                                          self._dest.x() if dest else 0,
        #                                          self._dest.y() if dest else 0)
        self._line = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        # self._arrow1 = QtWidgets.QGraphicsLineItem(self._dest.x() if dest else 0,
        #                                            self._dest.y() if dest else 0,
        #                                            )
        self._arrow1 = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._arrow2 = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        
        arrowstroke1 = QtGui.QBrush(QtCore.Qt.SolidPattern)
        arrowstroke1.setColor(QtCore.Qt.black)

        arrowstroke2 = QtGui.QBrush(QtCore.Qt.SolidPattern)
        arrowstroke2.setColor(QtCore.Qt.black)
        
        pen = QtGui.QPen(arrowstroke1, 2)
        self._arrow1.setPen(pen)

        pen = QtGui.QPen(arrowstroke2, 2)
        self._arrow2.setPen(pen)
        
        self.addToGroup(self._line)
        self.addToGroup(self._arrow1)
        self.addToGroup(self._arrow2)
        self._updateLines()

    def _updateLines(self):
        assert self._source
        
        x1 = self._source.x() + 50
        y1 = self._source.y() + 50
            
        if self._dest:
            x2 = self._dest.x() + 50
            y2 = self._dest.y() + 50
        else:
            x2 = self.X2.value()
            y2 = self.Y2.value()

        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            # TODO: hide arrows?
            return
        dr = (length - 50)/length
        
        cos = dx / length
        sin = dy / length
        acos = math.acos(cos)
        asin = math.asin(sin)
        alpha = self._alpha/2

        if dx >= 0:
            if dy >= 0:
                theta = acos # quadrant I
            else:
                theta = asin + 2*math.pi # quadrant IV
        else:
            if dy >= 0:
                theta = acos # quadrant II
            else:
                theta = math.pi - asin # quadrant III

        x1 += 50 * math.cos(theta)
        y1 += 50 * math.sin(theta)
        self.X1.setValue(x1)
        self.Y1.setValue(y1)
        if self._dest:
            x2 += 50 * math.cos(theta + math.pi)
            y2 += 50 * math.sin(theta + math.pi)
        self.X2.setValue(x2)
        self.Y2.setValue(y2)
        self._line.setLine(x1, y1, x2, y2)
        

        global message
        message.setText("dx = {0} dy = {1} r = {2} theta = {5} asin = {3} acos= {4}".format(dx, dy, length, asin, acos, theta))
        atheta = math.pi + theta - alpha
        ax = x2 + self._radius * math.cos(atheta)
        ay = y2 + self._radius * math.sin(atheta)
        self._arrow1.setLine(x2, y2, ax, ay)
        btheta = math.pi + theta + alpha
        bx = x2 + self._radius * math.cos(btheta)
        by = y2 + self._radius * math.sin(btheta)
        self._arrow2.setLine(x2, y2, bx, by)
#        self._line.setLine(x1, y1, x2*dr, y2*dr)

    def source(self):
        return (self.X1.value(), self.Y1.value())

    def dest(self):
        return (self.X2.value(), self.Y2.value())

    def setDest(self, x2, y2):
        self.X2.setValue(x2)
        self.Y2.setValue(y2)
        self._updateLines()

    def setLine(self, x1, y1, x2, y2):
        self.X1.setValue(x1)
        self.Y1.setValue(y1)
        self.X2.setValue(x2)
        self.Y2.setValue(y2)
        self._updateLines()

    def setDestNode(self, dest):
        self._dest = dest
        self.setDest(dest.x(), dest.y())

class Node(Connectable, FieldSet):
    Title = Text
    Urgent = Boolean
    Important = Boolean
    Innodes = Number
    Outnodes = Number

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

    def innodes(self):
        return self.Innodes.value()

    def outnodes(self):
        return self.Outnodes.value()

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

sourceNode = None
newedge = None
message = None
editor = None
movedp = False
toggledp = False
scene = None

nodeid = 0
nodes = {} # maps node IDs to Node objects
gnodes = {} # maps node IDs to GraphicalNode objects

def nodeFromGraphicalNode(gnode):
    return nodes[gnode.id]

def makeNode(title="", isurgent=False, isimportant=False):
    """Adds a node to the graph and displays it on the canvas."""
    global nodeid
    nodeid += 1
    
    node = Node(title, isurgent, isimportant)
    node.id = nodeid
    nodes[node.id] = node

    gnode = GraphicalNode(title)
    gnode.id = nodeid
    gnodes[node.id] = gnode

    gnode.connect(node)

    # TODO: select the graphical node

    global scene
    scene.addItem(gnode)

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
        strokebrush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        fillbrush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        fillbrush.setColor(QtCore.Qt.lightGray)
        pen = QtGui.QPen(strokebrush, 2)
        self._ellipse.setPen(pen)
        self._ellipse.setBrush(fillbrush)
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

    def setTitle(self, text, sender):
        self.Text.setValue(text, sender)
        self._text.setText(text)

    def _highlight(self):
        brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        pen = QtGui.QPen(brush, 4)
        self._ellipse.setPen(pen)

    def _unhighlight(self):
        brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        pen = QtGui.QPen(brush, 1)
        self._ellipse.setPen(pen)
        
    def mousePressEvent(self, event):
        scene = event.scenePos()
        mouse = event.pos()
        pos = self.scenePos()

        button = event.button()
        global sourceNode
        if button == QtCore.Qt.RightButton:
            global newedge
            assert not newedge
            newedge = GraphicalEdge(self, alpha=math.pi/6, radius=20)
            newedge.setLine(pos.x() + 50,
                            pos.y() + 50,
                            scene.x(),
                            scene.y())
            self.connect(newedge)
            self.scene().addItem(newedge)
            sourceNode = self
        elif button == QtCore.Qt.LeftButton:
            self._highlight()
            self.Selected.setValue(True)
            self._dx = scene.x() - pos.x()
            self._dy = scene.y() - pos.y()

    def mouseReleaseEvent(self, event):
        scene = event.scenePos()
        mouse = event.pos()
        global newedge
        global sourceNode
        global movedp
        global editor
        global toggledp
        
        if newedge:
            transform = QtGui.QTransform()
            nodes = [n for n in self.scene().items(scene) if isinstance(n, GraphicalNode)]
            destNode = nodes[0] if nodes else None
            if destNode:
                newedge.setDestNode(destNode)
                destNode.connect(newedge)
            else:
                newedge.disconnect(self)
                self.scene().removeItem(newedge)
            newedge = None
        elif movedp:
            self.Selected.setValue(False)
            self.X.setValue(scene.x() - self._dx)
            self.Y.setValue(scene.y() - self._dy)
            sourceNode = None
            self._unhighlight()
        elif not toggledp:
            # update editor
            node = nodeFromGraphicalNode(self)
            print("Connecting editor to {0}".format(node))
            node.connect(editor)
            toggledp = True
        else:
            toggledp = False
            self._unhighlight()
            node = nodeFromGraphicalNode(self)
            print("Disconnecting editor from {0}".format(node))
            self.disconnect(node)
        movedp = False

    def mouseMoveEvent(self, event):
        scene = event.scenePos()
        mouse = event.pos()
        pos = self.scenePos()

        global destNode
        global movedp

        movedp = True
        
        #print("Child at ({4}, {5})  got mouse move at ({0}, {1}), scene ({2}, {3})".format(mouse.x(), mouse.y(), scene.x(), scene.y(), pos.x(), pos.y()))
        global newedge
        if newedge:
            newedge.setDest(scene.x(), scene.y())
            #newedge.setDest(scene.x() - self._dx, scene.y() - self._dy)
        else:
            newpos = QtCore.QPointF(scene.x() - self._dx, scene.y() - self._dy)
            self.setPos(newpos)
            self.X.setValue(newpos.x())
            self.Y.setValue(newpos.y())

class GraphicalNodeView(QtWidgets.QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self._selected = False
        self._listeners = []
        #self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self._dx = 0
        self._dy = 0

    def wheelEvent(self, event):
        point = event.angleDelta()
        dy = point.y()
        #print("({0}, {1})".format(point.x(), point.y()))
        if dy > 0:
            self.scale(1.1, 1.1)
        elif dy < 0:
            self.scale(1/1.1, 1/1.1)

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
#        print("Selected node: {0}".format(sourceNode))
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
        global message
        
        #self._scene = QtWidgets.QGraphicsScene()
        global scene
        scene = GraphicalNodeScene()
        scene.setSceneRect(0, 0, 500, 500)
        message = QtWidgets.QGraphicsSimpleTextItem("blah blah blah")
        message.setPos(-200, -60)
        scene.addItem(message)

        # add the scene to the view
        self._view = GraphicalNodeView(scene)
        self._view.setSceneRect(0, 0, 500, 500)

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
        # self._nodeset = NodeSet()
        # self._nodeset.add(self._node1)
        # self._nodeset.add(self._node2)
        #self._list = GraphicalNodeList(self._nodeset)
        global editor
        editor = NodeEditor()
        #lines = ['a', 'b', 'c']
        #self._list.addItems(lines)
        self._dock.setWidget(editor)
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
        makeNode()
        # node = Node("")
        # gnode = GraphicalNode("")
        # self._nodes.add(node)
        # node.connect(gnode)
        # self._scene.addItem(gnode)

class GraphicalNodeList(QtWidgets.QListWidget, Connectable):
    def __init__(self, nodeset):
        QtWidgets.QListWidget.__init__(self)
        Connectable.__init__(self)
        self._nodeset = nodeset
        self.connect(self._nodeset)
        self.addItems([str(node) for node in self._nodeset.nodes()])
    
class NodeEditor(QtWidgets.QFrame, FieldSet, Connectable):
    Title = Text
    Urgent = Boolean
    Important = Boolean
    
    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        FieldSet.__init__(self)
        Connectable.__init__(self)
        self._layout = QtWidgets.QFormLayout()
        
        self._title = QtWidgets.QTextEdit()
        self._title.textChanged.connect(self.onTitleChange)
        self._layout.addRow("&Title", self._title)
        
        self._urgent = QtWidgets.QCheckBox()
        self._urgent.stateChanged.connect(self.onUrgentChange)
        checkedp = QtCore.Qt.Checked if self.Urgent.value() else QtCore.Qt.Unchecked
        self._urgent.setCheckState(checkedp)
        self._layout.addRow("&Urgent", self._urgent)

        self._impt = QtWidgets.QCheckBox()
        self._impt.stateChanged.connect(self.onImptChange)
        checkedp = QtCore.Qt.Checked if self.Urgent.value() else QtCore.Qt.Unchecked
        self._impt.setCheckState(checkedp)
        self._layout.addRow("&Important", self._impt)

        self.setLayout(self._layout)

    def onTitleChange(self):
        self.Title.setValue(self._title.toPlainText(), self)

    def onUrgentChange(self, state):
        self.Urgent.setValue(bool(state), self)

    def onImptChange(self, state):
        self.Important.setValue(bool(state), self)

    def setTitle(self, title, sender):
        self._title.setText(title)
        self.Title.setValue(title, sender)

    def title(self):
        return self.Title.value()

    def setUrgent(self, urgentp, sender):
        self.Urgent.setValue(urgentp, sender)
        checkedp = QtCore.Qt.Checked if self.Urgent.value() else QtCore.Qt.Unchecked
        self._urgent.setCheckState(checkedp)

    def setImportant(self, urgentp, sender):
        self.Important.setValue(urgentp, sender)
        checkedp = QtCore.Qt.Checked if self.Important.value() else QtCore.Qt.Unchecked
        self._impt.setCheckState(checkedp)

############

@update(Node, "Title", GraphicalNode)
def node_title_updated_for_graphical_node(node, gnode):
    print("Updating graphical node title to {0}".format(node.title()))
    print("{0} {1}".format(type(node), type(gnode)))
    gnode.setTitle(node.title(), node)

@connect(NodeEditor, Node)
def node_editor_connected_to_node(editor, node):
    editor.setTitle(node.title(), node)
    editor.setUrgent(node.urgent(), node)
    editor.setImportant(node.important(), node)

@update(NodeEditor, "Title", GraphicalNode)
def node_editor_updates_graphical_node(editor, gnode):
    gnode.setTitle(editor.title(), editor)

@update(NodeEditor, "Title", Node)
def node_editor_change_title(editor, node):
    print("Setting node title to {0}".format(editor.title()))
    node.setTitle(editor.title(), editor)

# @update(GraphicalNode, "X", Node)
# def graphical_node_x_changed(gnode, node):
#     node.setTitle("({0}, {1})".format(gnode.x(), gnode.y()))

# @update(GraphicalNode, "Y", Node)
# def graphical_node_y_changed_for_node(gnode, node):
#     node.setTitle("({0}, {1})".format(gnode.x(), gnode.y()))

@update(GraphicalNode, "X", GraphicalEdge)
def graphical_node_x_changed_for_graphical_edge(gnode, gedge):
    if gnode is gedge._source:
        gedge.X1.setValue(gnode.x(), gnode)
        gedge.Y1.setValue(gnode.y(), gnode)
        gedge._updateLines()
    elif gnode is gedge._dest:
        gedge.X2.setValue(gnode.x(), gnode)
        gedge.Y2.setValue(gnode.y(), gnode)
        gedge._updateLines()
    else:
        assert False

#@update(Node, "Title", GraphicalNode)
#def node_title_updated_to_graphical_node(node, gnode):
#    print("Updating graphical node title to {0}".format(node.title()))
#    print("{0} {1}".format(type(node), type(gnode)))
#    gnode.setText(node.title())

@connect(Node, GraphicalNode)
def node_connects_to_graphical_node(node, gnode):
    gnode.setTitle(node.title(), node)

@connect(Node, Edge)
def node_connects_to_edge(node, edge):
    if node is edge._source:
        node.Outnodes.setValue(node.outnodes() + 1)
    elif node is edge._dest:
        node.Innodes.setValue(node.innodes() + 1)
    else:
        assert False

@connect(Edge, Node)
def edge_connects_to_node(edge, node):
    if node is edge._source:
        node.Outnodes.setValue(node.outnodes() + 1)
    elif node is edge._dest:
        node.Innodes.setValue(node.innodes() + 1)
    else:
        assert False

@disconnect(Node, Edge)
def node_disconnects_from_edge(node, edge):
    if node is edge._source:
        node.Outnodes.setValue(node.outnodes() - 1)
    elif node is edge._dest:
        node.Innodes.setValue(node.innodes() - 1)
    else:
        assert False

@disconnect(Edge, Node)
def edge_disconnects_from_node(edge, node):
    if node is edge._source:
        node.Outnodes.setValue(node.outnodes() - 1)
    elif node is edge._dest:
        node.Innodes.setValue(node.innodes() - 1)
    else:
        assert False

@connect(GraphicalNode, GraphicalEdge)
def graphical_node_connects_to_graphical_edge(gnode, gedge):
    if gnode is gedge._source:
        gedge.X1.setValue(gnode.x(), gnode)
        gedge.Y1.setValue(gnode.y(), gnode)
        gedge._updateLines()
    elif gnode is gedge._dest:
        gedge.X2.setValue(gnode.x(), gnode)
        gedge.Y2.setValue(gnode.y(), gnode)
        gedge._updateLines()
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

