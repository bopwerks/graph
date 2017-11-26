# todo.py -- A todo list program.
import math
import sys
import pprint
import traceback
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui

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
        self.__connections = set()

    def _satisfiesConstraint(self, value):
        return True
#        raise NotImplementedError("Field is an abstract class which lacks a constraint")

    def setValue(self, value, sender=None):
#        print("{0}'s {1} was set by {2}".format(self._parent, self._name, sender))
        if not self._satisfiesConstraint(value):
            raise TypeError("Value {0} is not a {1}".format(value, self))
        self._value = value
        self._publish(sender, self._name)
        if self._parent:
            self._parent._childUpdated(self, sender)

    def value(self):
        return self._value

    def connectField(self, connectable):
        self.__connections.add(connectable)
        connectable.__connections.add(self)
        dispatch(self, connectable, "connect")

    def disconnectField(self, connectable):
        dispatch(self, connectable, "disconnect")
        try:
#            print("Removing connection!")
            self.__connections.remove(connectable)
        except KeyError:
            pass
        try:
#            print("Removing connections from other!")
            connectable.__connections.remove(self)
        except KeyError:
            pass

    def _childUpdated(self, child, sender):
#        print("Child {0} in parent {1} updated value".format(child, self))
        # A child Field's setValue() publishes to other Fields that are directly
        # connected to it. The sender of the message will be of the type of the field.
        # If a Field has a parent, it calls this function additional messages will
        # be sent with the parent as the sender.
        self._publish(sender, child._name)
        self._publish(sender, "")

    # def __del__(self):
    #     print("Called {0}__del__()".format(type(self)))
    #     traceback.print_stack()
    #     for receiver in self._connections:
    #         dispatch(self, receiver, "disconnect")
    #     print("Clearing connections!")
    #     self._connections.clear()

    def _publish(self, sender, name):
#        print("Called {0}::_publish({1}, {2})".format(self, sender, repr(name)))
#        print("{0}::connections = {0}".format(self, self.__connections))
        for receiver in self.__connections:
            if receiver is not sender:
                # print("{0} dispatching {1}->{2} name={3}".format(self, sender,
                #                                                  receiver,
                #                                                  name))
                dispatch(self, receiver, name)

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

class FieldGroup(Field):
    def __init__(self, parent=None, name=""):
        Field.__init__(self, parent, name=name)
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
        for fieldname in dir(type(self)):
            if fieldname.startswith("_"):
                continue
            T = self.__getType(fieldname)
            if not T or type(T) != type:
                continue
            if not issubclass(T, Field):
                continue
            fields.append(fieldname)
        return fields

    def __getType(self, fieldname):
        if fieldname not in type(self).__dict__:
            return None
        return type(self).__dict__[fieldname]

class Environment(FieldGroup):
    selectedNode = Field
    
    def __init__(self, parent=None, name=""):
        FieldGroup.__init__(self, parent, name)


env = Environment(None, "Environment")
dispatchtab = {}

def insert(sender, receiver, message, action):
    tab = dispatchtab
    if sender not in tab:
        tab[sender] = {}
    tab = tab[sender]
    if receiver not in tab:
        tab[receiver] = {}
    tab = tab[receiver]
    if message not in tab:
        tab[message] = set()
    actions = tab[message]
    actions.add(action)

def actions(sender, receiver, message):
    tab = dispatchtab
    return tab.get(sender, {}).get(receiver, {}).get(message, [])

def update(sender, receiver, message=""):
    # print("{1} will be notified when a {0}'s {2} is updated".format(sender,
    #                                                                 receiver,
    #                                                                 fieldname))
    def decorate(action):
        insert(sender, receiver, message, action)
        return action
    return decorate

def connect(sender, receiver):
    # print("{1} will be notified when a {0} connects".format(sender,
    #                                                         receiver))
    def decorate(action):
        insert(sender, receiver, "connect", action)
        return action
    return decorate

def disconnect(sender, receiver):
    # print("{1} will be notified when a {0} disconnects".format(sender,
    #                                                            receiver))
    def decorate(action):
        insert(sender, receiver, "disconnect", action)
        return action
    return decorate

def dispatch(sender, receiver, message):
#    print("dispatch({0}, {1}, {2})".format(sender, receiver, repr(message)))
#    print("Actions: {0}".format(A))
    A = actions(type(sender), type(receiver), message)
    for action in A:
#        print("Executing action {0}".format(action))
        action(sender, receiver)

def set_value(fieldset, fieldname, value):
    assert isinstance(fieldset, FieldGroup)
    assert fieldname in fieldset.__dict__
    assert isinstance(fieldset.__dict__[fieldname], Field)
    return fieldset.__dict__[fieldname].setValue(value)

def get_value(fieldset, fieldname):
    return fieldset.__dict__[fieldname].value()

class Edge(FieldGroup):
    Weight = Number
    
    def __init__(self, source, dest, value=None):
        FieldGroup.__init__(self)

def sign(n):
    return -1 if n < 0 else 1

class GraphicalEdge(QtWidgets.QGraphicsItemGroup, FieldGroup):
    X1 = Number
    Y1 = Number
    X2 = Number
    Y2 = Number
    
    def __init__(self, source=None, dest=None, radius=0, alpha=0):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        FieldGroup.__init__(self)
        self._source = source
        self._dest = dest
        self._radius = radius
        self._alpha = alpha
        self.X1.setValue(self._source.x() if source else 0)
        self.Y1.setValue(self._source.y() if source else 0)
        self.X2.setValue(self._dest.x() if dest else 0)
        self.Y2.setValue(self._dest.y() if dest else 0)
        self._line = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
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

class Node(FieldGroup):
    Title = Text
    Urgent = Boolean
    Important = Boolean
    Innodes = Number
    Outnodes = Number

    def __init__(self, title="", urgent=True, important=True):
        FieldGroup.__init__(self, None)
        
        self.Title.setValue(title)
        self.Urgent.setValue(urgent, None)
        self.Important.setValue(important, None)
        self.Innodes.setValue(0, None)
        self.Outnodes.setValue(0, None)

    def setUrgent(self, urgentp, sender):
        self.Urgent.setValue(urgentp, sender)

    def urgent(self):
        return self.Urgent.value()

    def setImportant(self, importantp, sender=None):
        self.Important.setValue(importantp, sender if sender else self)

    def important(self):
        return self.Important.value()

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
                hash(self.Urgent) ^
                hash(self.Important))

class NodeTableModel(QtCore.QAbstractTableModel):
    def __init__(self):
        super().__init__()
        self._nodes = []

    def addNode(self, node):
        self._nodes.append(node)
        self.connectField(node)

    def onNodeUpdate(self, node):
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

def graphicalNodeFromNode(node):
    return gnodes[node.id]

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

    node.connectField(gnode)

    # TODO: select the graphical node

    global scene
    scene.addItem(gnode)

class GraphicalNode(QtWidgets.QGraphicsItemGroup, FieldGroup):
    X        = Number
    Y        = Number
    Selected = Boolean
    Text     = Text
    
    def __init__(self, title=""):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        FieldGroup.__init__(self, None)

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
        self.Selected.setValue(False, self)
        self._dx = 0
        self._dy = 0
        self._id = 0
        self._movedp = False

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
            self.connectField(newedge)
            self.scene().addItem(newedge)
        elif button == QtCore.Qt.LeftButton:
            global env
            selectedNode = env.selectedNode.value()
            if selectedNode is not self:
                if selectedNode:
                    gnode = graphicalNodeFromNode(selectedNode)
                    gnode._unhighlight()
                    editor.disconnectField(selectedNode)
                self._highlight()
#                node = nodeFromGraphicalNode(self)
#                env.selectedNode.setValue(node)
#            self._highlight()
            self._dx = scene.x() - pos.x()
            self._dy = scene.y() - pos.y()

    def mouseReleaseEvent(self, event):
        scene = event.scenePos()
        mouse = event.pos()
        global newedge
        global toggledp
        global env
        global editor
        
        if newedge:
            transform = QtGui.QTransform()
            nodes = [n for n in self.scene().items(scene) if isinstance(n, GraphicalNode)]
            destNode = nodes[0] if nodes else None
            if destNode:
                newedge.setDestNode(destNode)
                destNode.connectField(newedge)
            else:
                newedge.disconnectField(self)
                self.scene().removeItem(newedge)
            newedge = None
        elif not self._movedp:
            node = nodeFromGraphicalNode(self)
            if env.selectedNode.value() is node:
                editor.disconnectField(node)
                env.selectedNode.setValue(None)
                self._unhighlight()
            else:
                env.selectedNode.setValue(nodeFromGraphicalNode(self))
                self._highlight()
        else:
            self.X.setValue(scene.x() - self._dx, None)
            self.Y.setValue(scene.y() - self._dy, None)
            node = nodeFromGraphicalNode(self)
            env.selectedNode.setValue(node)
            editor.connectField(node)
            
#            self._unhighlight()
#            node = nodeFromGraphicalNode(self)
#            print("Disconnecting editor from {0}".format(node))
#            self.disconnectField(node)
        self._movedp = False

    def mouseMoveEvent(self, event):
        scene = event.scenePos()
        mouse = event.pos()
        pos = self.scenePos()

        global destNode
        self._movedp = True
        
        #print("Child at ({4}, {5})  got mouse move at ({0}, {1}), scene ({2}, {3})".format(mouse.x(), mouse.y(), scene.x(), scene.y(), pos.x(), pos.y()))
        global newedge
        if newedge:
            newedge.setDest(scene.x(), scene.y())
            #newedge.setDest(scene.x() - self._dx, scene.y() - self._dy)
        else:
            newpos = QtCore.QPointF(scene.x() - self._dx, scene.y() - self._dy)
            self.setPos(newpos)
            self.X.setValue(newpos.x(), None)
            self.Y.setValue(newpos.y(), None)

class GraphicalNodeView(QtWidgets.QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self._selected = False
        self._listeners = []
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
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
        node.connectField(gnode)
        self.addItem(gnode)

class NodeSet(FieldGroup):
    Size = Number
    Updated = Boolean
    
    def __init__(self):
        FieldGroup.__init__(self)
        self._nodes = set()

    def nodes(self):
        return list(self._nodes)

    def add(self, node):
        self._nodes.add(node)
        node.connectField(self)

    def remove(self, node):
        self._nodes.remove(node)
        node.disconnectField(self)

class NodeTableView(QtWidgets.QTableView):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.setModel(model)
        self.setSortingEnabled(True)
        model.dataChanged.connectField(self.update)
        
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
        global env
        env.connectField(editor)
        #lines = ['a', 'b', 'c']
        #self._list.addItems(lines)
        self._dock.setWidget(editor)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._dock)

        self.setWindowTitle(title)

        self._toolbar = self.addToolBar("Node")
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

class GraphicalNodeList(QtWidgets.QListWidget, FieldGroup):
    def __init__(self, nodeset):
        QtWidgets.QListWidget.__init__(self)
        FieldGroup.__init__(self)
        self._nodeset = nodeset
        self.connectField(self._nodeset)
        self.addItems([str(node) for node in self._nodeset.nodes()])
    
class NodeEditor(QtWidgets.QFrame, FieldGroup):
    Title = Text
    Urgent = Boolean
    Important = Boolean
    
    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        FieldGroup.__init__(self)
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

    def disable(self):
        self._title.setDisabled(True)
        self._urgent.setDisabled(True)
        self._impt.setDisabled(True)

    def enable(self):
        self._title.setDisabled(False)
        self._urgent.setDisabled(False)
        self._impt.setDisabled(False)

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

@update(Node, GraphicalNode, "Title")
def node_title_updated_for_graphical_node(node, gnode):
#    print("Updating graphical node title to {0}".format(node.title()))
    gnode.setTitle(node.title(), node)

@connect(NodeEditor, Node)
def node_editor_connected_to_node(editor, node):
    print("NodeEditor connected to Node")
    editor.setTitle(node.title(), node)
    editor.setUrgent(node.urgent(), node)
    editor.setImportant(node.important(), node)

@update(NodeEditor, GraphicalNode, "Title")
def node_editor_updates_graphical_node(editor, gnode):
    gnode.setTitle(editor.title(), editor)

@update(NodeEditor, Node, "Title")
def node_editor_change_title(editor, node):
#    print("Setting node title to {0}".format(editor.title()))
    node.setTitle(editor.title(), editor)

# @update(GraphicalNode, Node)
# def graphical_node_changed_for_node(gnode, node):
#     node.setTitle("({0}, {1})".format(gnode.x(), gnode.y()))

@update(GraphicalNode, GraphicalEdge, "X")
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

@update(Node, GraphicalNode, "Title")
def node_title_updated_to_graphical_node(node, gnode):
#    print("Updating graphical node title to {0}".format(node.title()))
#    print("{0} {1}".format(type(node), type(gnode)))
    gnode.setTitle(node.title(), node)

@connect(Node, GraphicalNode)
def node_connects_to_graphical_node(node, gnode):
    gnode.setTitle(node.title(), node)

@connect(Node, Edge)
def node_connects_to_edge(node, edge):
    if node is edge._source:
        node.Outnodes.setValue(node.outnodes() + 1, edge)
    elif node is edge._dest:
        node.Innodes.setValue(node.innodes() + 1, edge)
    else:
        assert False

@connect(Edge, Node)
def edge_connects_to_node(edge, node):
    if node is edge._source:
        node.Outnodes.setValue(node.outnodes() + 1, edge)
    elif node is edge._dest:
        node.Innodes.setValue(node.innodes() + 1, edge)
    else:
        assert False

@disconnect(Node, Edge)
def node_disconnects_from_edge(node, edge):
    if node is edge._source:
        node.Outnodes.setValue(node.outnodes() - 1, None)
    elif node is edge._dest:
        node.Innodes.setValue(node.innodes() - 1, None)
    else:
        assert False

@disconnect(Edge, Node)
def edge_disconnects_from_node(edge, node):
    if node is edge._source:
        node.Outnodes.setValue(node.outnodes() - 1, None)
    elif node is edge._dest:
        node.Innodes.setValue(node.innodes() - 1, None)
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

@connect(Environment, NodeEditor)
def selected_node_changed(env, editor):
    node = env.selectedNode.value()
    if not node:
        editor.disable()
        return
    editor.enable()
    editor.setTitle(node.title(), env)
    editor.setUrgent(node.urgent(), env)
    editor.setImportant(node.important(), env)

@update(Environment, NodeEditor, "selectedNode")
def selected_node_changed(env, editor):
    node = env.selectedNode.value()
    if not node:
        editor.disable()
        return
    editor.enable()
    editor.setTitle(node.title(), env)
    editor.setUrgent(node.urgent(), env)
    editor.setImportant(node.important(), env)

#pp = pprint.PrettyPrinter(indent=4)
#pp.pprint(dispatchtab)

app = QtWidgets.QApplication(sys.argv)
win = MainWindow("To-Done")
win.show()
app.exec_()
