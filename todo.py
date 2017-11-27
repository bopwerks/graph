# todo.py -- A todo list program.
import math
import sys
import pprint
import traceback
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui

nodeid = 0
nodes = {} # maps node IDs to Node objects
qnodes = {} # maps node IDs to QNode objects

edgeid = 0
edges = {} # maps edge IDs to Edge objects
qedges = {} # maps edge IDs to QEdge objects

def nodeFromQNode(gnode):
    return nodes[gnode.id]

def qnodeFromNode(node):
    return qnodes[node.id]

def distance(x, y):
    return math.sqrt(x**2 + y**2)

def angle(dx, dy):
    r = distance(dx, dy)
    if dx >= 0:
        if dy >= 0:
            theta = math.acos(dx/r) # quadrant I
        else:
            theta = math.asin(dy/r) + 2*math.pi # quadrant IV
    else:
        if dy >= 0:
            theta = math.acos(dx/r) # quadrant II
        else:
            theta = math.pi - math.asin(dy/r) # quadrant III
    return theta

class QArrow(QtWidgets.QGraphicsItemGroup):
    def __init__(self, radius=0, angle=0, color=QtCore.Qt.black):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        self._radius = radius
        self._angle = angle
        self._line = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._arrow1 = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._arrow2 = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        stroke.setColor(color)

        pen = QtGui.QPen(stroke, 2)
        self._arrow1.setPen(pen)

        pen = QtGui.QPen(stroke, 2)
        self._arrow2.setPen(pen)
        
        self.addToGroup(self._line)
        self.addToGroup(self._arrow1)
        self.addToGroup(self._arrow2)
        self._updateLines()

    def _updateLines(self):
        line = self._line.line()
        x1 = line.x1()
        y1 = line.y1()
        x2 = line.x2()
        y2 = line.y2()

        self._line.setLine(x1, y1, x2, y2)
        
        dx = x2 - x1
        dy = y2 - y1
        if not distance(dx, dy):
            return
        
        theta = angle(dx, dy)
        atheta = math.pi + theta - self._angle/2
        ax = x2 + self._radius * math.cos(atheta)
        ay = y2 + self._radius * math.sin(atheta)
        self._arrow1.setLine(x2, y2, ax, ay)
        
        btheta = math.pi + theta + self._angle/2
        bx = x2 + self._radius * math.cos(btheta)
        by = y2 + self._radius * math.sin(btheta)
        self._arrow2.setLine(x2, y2, bx, by)

    def line(self):
        return self._line.line()
    
    def setLine(self, x1, y1, x2, y2):
        self._line.setLine(x1, y1, x2, y2)
        self._updateLines()

class QEdge(QArrow):
    def __init__(self, origin, dest, radius=0, angle=0):
        QArrow.__init__(self, radius=radius, angle=angle)
        self._origin = origin
        self._dest = dest
        self._origin.addListener(self)
        self._dest.addListener(self)
        self._setArrows()

    def _setArrows(self):
        # TODO: compute edge of nodes for position
        dx = self._dest.x() - self._origin.x()
        dy = self._dest.y() - self._origin.y()
        if not distance(dx, dy):
            return
        theta = angle(dx, dy)
        cos = math.cos(theta)
        sin = math.sin(theta)
        x1 = self._origin.x() + 50 + 50 * cos
        y1 = self._origin.y() + 50 + 50 * sin
        x2 = self._dest.x() + 50 - 50 * cos
        y2 = self._dest.y() + 50 - 50 * sin
        self.setLine(x1, y1, x2, y2)

    def onNodeUpdate(self, node):
        assert node is self._origin or node is self._dest
        self._setArrows()

    def fromArrow(arrow, origin, dest):
        line = arrow.line()
        edge = QEdge(origin, dest, radius=arrow._radius, angle=arrow._angle)
        edge.setLine(line.x1(), line.y1(), line.x2(), line.y2())
        edge._setArrows()
        return edge
        
class Node(object):
    def __init__(self, title="", urgent=True, important=True, id=0):
        self.id = 0
        self._title = title
        self._urgentp = urgent
        self._importantp = important
        self._innodes = 0
        self._outnodes = 0
        self._listeners = set()

    def _publish(self):
        for obj in self._listeners:
            obj.onNodeUpdate(self)

    def addListener(self, obj):
        self._listeners.add(obj)

    def removeListener(self, obj):
        self._listeners.remove(obj)

    def setUrgent(self, urgentp):
        self._urgentp = urgentp
        self._publish()

    def urgent(self):
        return self._urgentp

    def setImportant(self, importantp):
        self._importantp = importantp
        self._publish()

    def important(self):
        return self._importantp

    def id(self):
        return self._id

    def title(self):
        return self._title

    def setTitle(self, title):
        self._title = title
        self._publish()

    def innodes(self):
        return self.Innodes.value()

    def outnodes(self):
        return self.Outnodes.value()

    def __hash__(self):
        return (hash(self._title) ^
                hash(self._urgentp) ^
                hash(self._importantp))

selectedNode = None
newedge = None
message = None
editor = None

def makeNode(title="", isurgent=False, isimportant=False):
    """Adds a node to the graph and displays it on the canvas."""
    global nodeid
    nodeid += 1
    
    node = Node(title, isurgent, isimportant)
    node.id = nodeid
    nodes[node.id] = node

    qnode = QNode(title)
    qnode.id = nodeid
    qnodes[node.id] = qnode

    node.addListener(qnode)
    return (node, qnode)

class QNode(QtWidgets.QGraphicsItemGroup):
    def __init__(self, title=""):
        QtWidgets.QGraphicsItemGroup.__init__(self)

        self._ellipse = QtWidgets.QGraphicsEllipseItem(0, 0, 100, 100)
        strokebrush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        fillbrush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        fillbrush.setColor(QtCore.Qt.lightGray)
        self._ellipse.setBrush(fillbrush)
        self._unhighlight()
        self.addToGroup(self._ellipse)
        
        self._text = QtWidgets.QGraphicsSimpleTextItem(title)
        self._text.setPos(25, 25)
        self.addToGroup(self._text)
        
        self._dx = 0
        self._dy = 0
        self._movedp = False
        self._listeners = set()
        self.setPos(0, 0)

    def addListener(self, obj):
        self._listeners.add(obj)

    def _publish(self):
        for obj in self._listeners:
            obj.onNodeUpdate(self)

    def onNodeUpdate(self, node):
        self._text.setText(node.title())

    def x(self):
        return self.pos().x()

    def y(self):
        return self.pos().y()

    def _highlight(self):
        brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        pen = QtGui.QPen(brush, 4)
        self._ellipse.setPen(pen)
        self._highlightedp = True

    def _unhighlight(self):
        brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        pen = QtGui.QPen(brush, 1)
        self._ellipse.setPen(pen)
        self._highlightedp = False
        
    def mousePressEvent(self, event):
        global selectedNode
        global editor
        
        button = event.button()
        mouse = event.pos()
        pos = self.scenePos()
        scene = event.scenePos()
        
        if button == QtCore.Qt.RightButton:
            global newedge
            assert not newedge
            newedge = QArrow(angle=math.pi/6, radius=20)
            newedge.setLine(pos.x() + 50,
                            pos.y() + 50,
                            scene.x(),
                            scene.y())
            self.scene().addItem(newedge)
        elif button == QtCore.Qt.LeftButton:
            editor.setNode(nodeFromQNode(self))
            if selectedNode is not self:
                if selectedNode:
                    qnode = qnodeFromNode(selectedNode)
                    qnode._unhighlight()
                self._highlight()
            self._dx = scene.x() - pos.x()
            self._dy = scene.y() - pos.y()

    def mouseReleaseEvent(self, event):
        global newedge
        global env
        global editor
        global selectedNode
        
        scene = event.scenePos()
        mouse = event.pos()
        
        if newedge:
            transform = QtGui.QTransform()
            nodes = [n for n in self.scene().items(scene) if isinstance(n, QNode)]
            destNode = nodes[0] if nodes else None
            self.scene().removeItem(newedge)
            if destNode and destNode is not self: # hovering over another node
                # TODO: make an edge
                edge = QEdge.fromArrow(newedge, self, destNode)
                self.scene().addItem(edge)
            newedge = None
        elif not self._movedp:
            if selectedNode is self:
                editor.setNode(None)
                selectedNode = None
                self._unhighlight()
            else:
                selectedNode = self
                editor.setNode(nodeFromQNode(self))
                self._highlight()
        else:
            selectedNode = self
            editor.setNode(nodeFromQNode(self))
            
        self._movedp = False

    def _highlighted():
        return self._highlightedp

    def mouseMoveEvent(self, event):
        global destNode
        global newedge
        
        self._movedp = True
        
        scene = event.scenePos()
        mouse = event.pos()
        pos = self.scenePos()

        if newedge:
            line = newedge.line()
            newedge.setLine(line.x1(), line.y1(), scene.x(), scene.y())
        else:
            newpos = QtCore.QPointF(scene.x() - self._dx, scene.y() - self._dy)
            self.setPos(newpos)
            self._publish()

class QNodeView(QtWidgets.QGraphicsView):
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

class QNodeScene(QtWidgets.QGraphicsScene):
    def __init__(self):
        super().__init__()
        self._nodes = []
        
    def addNode(self, node):
        self._nodes.append(node)
        gnode = QNode()
        node.connectField(gnode)
        self.addItem(gnode)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, title):
        super().__init__()

        # set size to 70% of screen
        self.resize(QtWidgets.QDesktopWidget().availableGeometry(self).size() * 0.7)

        # set up scene
        global message
        
        self._scene = QNodeScene()
        self._scene.setSceneRect(-500, -500, 500, 500)
        
        message = QtWidgets.QGraphicsSimpleTextItem("blah blah blah")
        message.setPos(-200, -60)
        self._scene.addItem(message)

        # add the scene to the view
        self._view = QNodeView(self._scene)
        self._view.setSceneRect(0, 0, 500, 500)

        # make the view the main widget of the window
        self.setCentralWidget(self._view)

        # add a dock with a list
        self._dock = QtWidgets.QDockWidget("Task Editor")
        global editor
        self._editor = QNodeEditor()
        editor = self._editor
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
        global editor
        global selectedNode
        node, qnode = makeNode()
        self._scene.addItem(qnode)
        if selectedNode:
            selectedNode._unhighlight()
        editor.setNode(node)

def checkstate(val):
    return QtCore.Qt.Checked if bool(val) else QtCore.Qt.Unchecked

class QNodeEditor(QtWidgets.QFrame):
    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        self._title = QtWidgets.QTextEdit()
        self._urgent = QtWidgets.QCheckBox()
        self._important = QtWidgets.QCheckBox()

        self._layout = QtWidgets.QFormLayout()
        self._layout.addRow("&Title", self._title)
        self._layout.addRow("&Urgent", self._urgent)
        self._layout.addRow("&Important", self._important)
        self.setLayout(self._layout)
        
        self._clear()
        self._setEnabled(False)
        
        self._title.textChanged.connect(self._onTitleChange)
        self._urgent.stateChanged.connect(self._onUrgentChange)
        self._important.stateChanged.connect(self._onImptChange)
        
    def setNode(self, node):
        self._node = node
        if not self._node:
            self._clear()
            self._setEnabled(False)
        else:
            self._setEnabled(True)
            self._title.setText(self._node.title())
            self._urgent.setCheckState(checkstate(self._node.urgent()))
            self._important.setCheckState(checkstate(self._node.important()))

    def _clear(self):
        self._title.setText("")
        self._urgent.setCheckState(checkstate(False))
        self._important.setCheckState(checkstate(False))

    def _setEnabled(self, val):
        self._title.setDisabled(not val)
        self._urgent.setDisabled(not val)
        self._important.setDisabled(not val)

    def _onTitleChange(self):
        if self._node:
            self._node.setTitle(self._title.toPlainText())

    def _onUrgentChange(self, state):
        if self._node:
            self._node.setUrgent(bool(state))

    def _onImptChange(self, state):
        if self._node:
            self._node.setImportant(bool(state))

app = QtWidgets.QApplication(sys.argv)
win = MainWindow("To-Done")
win.show()
app.exec_()
