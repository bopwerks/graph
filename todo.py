# todo.py -- A todo list program.
import math
import sys
import pprint
import traceback
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui

class QArrow(QtWidgets.QGraphicsItemGroup):
    def __init__(self, radius=0, angle=0, color=QtCore.Qt.black):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        self._radius = radius
        self._angle = angle
        self._x1 = 0
        self._y1 = 0
        self._x2 = 0
        self._y2 = 0
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

        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)
        if length == 0:
            # TODO: hide arrows?
            return
        
        cos = dx / length
        sin = dy / length
        acos = math.acos(cos)
        asin = math.asin(sin)
        angle = self._angle/2

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

        self._line.setLine(x1, y1, x2, y2)
        
        atheta = math.pi + theta - angle
        ax = x2 + self._radius * math.cos(atheta)
        ay = y2 + self._radius * math.sin(atheta)
        self._arrow1.setLine(x2, y2, ax, ay)
        
        btheta = math.pi + theta + angle
        bx = x2 + self._radius * math.cos(btheta)
        by = y2 + self._radius * math.sin(btheta)
        self._arrow2.setLine(x2, y2, bx, by)

    def line(self):
        return self._line.line()
    
    def setLine(self, x1, y1, x2, y2):
        self._line.setLine(x1, y1, x2, y2)
        self._updateLines()

class GraphicalEdge(QArrow):
    def __init__(self, source, dest, radius=0, angle=0):
        QArrow.__init__(self, radius=radius, angle=angle)
        self._source = source
        self._dest = dest
        self._source.addListener(self)
        self._dest.addListener(self)
        self._setArrows()

    def _setArrows(self):
        # TODO: compute edge of nodes for position
        self.setLine(self._source.x() + 50,
                     self._source.y() + 50,
                     self._dest.x() + 50,
                     self._dest.y() + 50)

    def onNodeUpdate(self, node):
        assert node is self._source or node is self._dest
        self._setArrows()

    def fromArrow(arrow, source, dest):
        line = arrow.line()
        edge = GraphicalEdge(source, dest, radius=arrow._radius, angle=arrow._angle)
        edge.setLine(line.x1(), line.y1(), line.x2(), line.y2())
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
movedp = False
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
    global scene
    nodeid += 1
    
    node = Node(title, isurgent, isimportant)
    node.id = nodeid
    nodes[node.id] = node

    gnode = GraphicalNode(title)
    gnode.id = nodeid
    gnodes[node.id] = gnode

    node.addListener(gnode)

    # TODO: select the graphical node
    scene.addItem(gnode)

class GraphicalNode(QtWidgets.QGraphicsItemGroup):
    def __init__(self, title=""):
        QtWidgets.QGraphicsItemGroup.__init__(self)

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
        
        self._selectedp = False
        self._dx = 0
        self._dy = 0
        self._id = 0
        self._movedp = False
        self.setPos(0, 0)
        self._listeners = set()

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

    def _unhighlight(self):
        brush = QtGui.QBrush(QtCore.Qt.SolidPattern)
        pen = QtGui.QPen(brush, 1)
        self._ellipse.setPen(pen)
        
    def mousePressEvent(self, event):
        scene = event.scenePos()
        mouse = event.pos()
        pos = self.scenePos()

        button = event.button()
        global selectedNode
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
            if selectedNode is not self:
                if selectedNode:
                    gnode = graphicalNodeFromNode(selectedNode)
                    gnode._unhighlight()
                    editor.setNode(None)
                self._highlight()
            self._dx = scene.x() - pos.x()
            self._dy = scene.y() - pos.y()

    def mouseReleaseEvent(self, event):
        scene = event.scenePos()
        mouse = event.pos()
        global newedge
        global env
        global editor
        
        if newedge:
            transform = QtGui.QTransform()
            nodes = [n for n in self.scene().items(scene) if isinstance(n, GraphicalNode)]
            destNode = nodes[0] if nodes else None
            self.scene().removeItem(newedge)
            if destNode and destNode is not self: # hovering over another node
                # TODO: make an edge
                edge = GraphicalEdge.fromArrow(newedge, self, destNode)
                self.scene().addItem(edge)
            newedge = None
        elif not self._movedp:
            node = nodeFromGraphicalNode(self)
            if selectedNode is node:
                editor.setNode(None)
                selectedNode = None
                self._unhighlight()
            else:
                selectedNode = nodeFromGraphicalNode(self)
                editor.setNode(selectedNode)
                self._highlight()
        else:
            selectedNode = nodeFromGraphicalNode(self)
            editor.setNode(selectedNode)
            
        self._movedp = False

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

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, title):
        super().__init__()

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
        self._dock = QtWidgets.QDockWidget("Task Editor")
        global editor
        editor = NodeEditor()
        global env
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

def checkstate(val):
    return QtCore.Qt.Checked if bool(val) else QtCore.Qt.Unchecked

class NodeEditor(QtWidgets.QFrame):
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
            self._title.setText(self._node.title())
            self._urgent.setCheckState(checkstate(self._node.urgent()))
            self._important.setCheckState(checkstate(self._node.important()))

    def _clear(self):
        self._title.setText("")
        self._urgent.setCheckState(checkstate(False))
        self._important.setCheckState(checkstate(False))

    def _setEnabled(self, val):
        self._title.setDisabled(val)
        self._urgent.setDisabled(val)
        self._important.setDisabled(val)

    def _onTitleChange(self):
        self._node.setTitle(self._title.toPlainText())

    def _onUrgentChange(self, state):
        self._node.setUrgent(bool(state))

    def _onImptChange(self, state):
        self._node.setImportant(bool(state))

#pp = pprint.PrettyPrinter(indent=4)
#pp.pprint(dispatchtab)

app = QtWidgets.QApplication(sys.argv)
win = MainWindow("To-Done")
win.show()
app.exec_()
