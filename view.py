# graph.py -- A network layout program.
import math
import sys
import random
import model
import event
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication

selectedNode = None
selectedEdge = None
selectedRelation = None
newedge = None
editor = None
nodelist = None

qnodes = {} # maps node IDs to QNode objects
qedges = {} # maps (origin node id, destination node id, relation) to a QEdge

def random_color():
    colors = {
        "black": QtCore.Qt.black,
        "blue": QtCore.Qt.blue,
        "cyan": QtCore.Qt.cyan,
        "darkBlue": QtCore.Qt.darkBlue,
        "darkCyan": QtCore.Qt.darkCyan,
        "darkGray": QtCore.Qt.darkGray,
        "darkGreen": QtCore.Qt.darkGreen,
        "darkMagenta": QtCore.Qt.darkMagenta,
        "darkRed": QtCore.Qt.darkRed,
        "darkYellow": QtCore.Qt.darkYellow,
        "gray": QtCore.Qt.gray,
        "green": QtCore.Qt.green,
        "lightGray": QtCore.Qt.lightGray,
        "magenta": QtCore.Qt.magenta,
        "red": QtCore.Qt.red,
        # "white": QtCore.Qt.white,
        # "yellow": QtCore.Qt.yellow,
    }
    return [v for k, v in colors.items()][random.randint(0, len(colors)-1)]

def selectRelation(relation):
    assert relid in relations
    global selectedRelation
    selectedRelation = relid

def makeRelation(name, color, symmetric=False, transitive=True):
    global relationID
    global relations
    rel = model.Relation(name, color, symmetric, transitive)
    relations[relationID] = rel
    relationID += 1

def getState():
    state = {
        "nodeid": nodeid,
        "outnodes": outnodes,
        "innodes": innodes
    }
    state["nodes"] = {}
    for id, node in nodes.items():
        state["nodes"][id] = {
            "title": node.title(),
            "urgent": node.urgent(),
            "important": node.important(),
            "x": qnodes[id].x(),
            "y": qnodes[id].y()
        }
    return state

def saveState(path, state):
    assert path
    assert state
    print("STATE", state)
    with open(path, "w") as fp:
        fp.write(repr(state))

def loadState(path):
    assert path
    with open(path, "r") as fp:
        return eval(fp.read())

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
    def __init__(self, relation, radius=20, angle=math.pi/6):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        self._relation = relation
        self._radius = radius
        self._angle = angle
        
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        stroke.setColor(self._relation.color)
        thickpen = QtGui.QPen(stroke, 2)
        thinpen = QtGui.QPen(stroke, 1)
        
        self._line = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._line.setPen(thinpen)
        self._arrow1 = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._arrow1.setPen(thickpen)
        self._arrow2 = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._arrow2.setPen(thickpen)
        
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
    def __init__(self, relation, origin, dest, radius=20, angle=math.pi/6):
        QArrow.__init__(self, relation, radius=radius, angle=angle)
        self._relation = relation
        self._origin = origin
        self._dest = dest
        self._origin.addListener(self._onNodeUpdate)
        self._dest.addListener(self._onNodeUpdate)
        self._setArrows()

    def _setArrows(self):
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

    def _highlight(self):
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        stroke.setColor(self._relation.color)
        pen = QtGui.QPen(stroke, 2)
        self._line.setPen(pen)

    def _unhighlight(self):
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        stroke.setColor(self._relation.color)
        pen = QtGui.QPen(stroke, 1)
        self._line.setPen(pen)

    def _onNodeUpdate(self, node):
        assert node is self._origin or node is self._dest
        self._setArrows()

    def fromArrow(relation, arrow, origin, dest):
        line = arrow.line()
        edge = QEdge(relation, origin, dest, radius=arrow._radius, angle=arrow._angle)
        edge.setLine(line.x1(), line.y1(), line.x2(), line.y2())
        edge._setArrows()
        return edge

    def mousePressEvent(self, event):
        print("QEdge::mousePressEvent")
        global selectedEdge
        global selectedNode
        global editor
        
        button = event.button()
        mouse = event.pos()
        pos = self.scenePos()
        scene = event.scenePos()

        if button != QtCore.Qt.LeftButton:
            event.ignore()
            return

        if selectedNode:
            #selectedNode._unhighlight()
            selectedNode = None
            #editor.setNode(None)
            
        if selectedEdge is self:
            #self._unhighlight()
            selectedEdge = None
        else:
            if selectedEdge:
                selectedEdge._unhighlight()
            #self._highlight()
            selectedEdge = self
class QNodeList(QtWidgets.QTableWidget):
    def __init__(self):
        super().__init__(0, 3)
        self._nodes = []
        task = QtWidgets.QTableWidgetItem("Task")
        task.setTextAlignment(QtCore.Qt.AlignLeft)
        self.setHorizontalHeaderItem(0, task)
        impt = QtWidgets.QTableWidgetItem("Important")
        impt.setTextAlignment(QtCore.Qt.AlignLeft)
        self.setHorizontalHeaderItem(1, impt)
        urgent = QtWidgets.QTableWidgetItem("Urgent")
        urgent.setTextAlignment(QtCore.Qt.AlignLeft)
        self.setHorizontalHeaderItem(2, urgent)
        self.cellChanged.connect(self._onCellChanged)

    def _updateList(self):
        self.clearContents()
        # nodes = sorted([n for n in self._nodes if n.innodes() == 0],
        #                key=lambda n: (n.important(), n.urgent()), reverse=True)
        nodes = self._nodes
        row = 0
        self.setRowCount(len(nodes))
        for node in nodes:
            title = QtWidgets.QTableWidgetItem(node.title())
            self.setItem(row, 0, title)
            impt = QtWidgets.QTableWidgetItem()
            impt.setFlags(impt.flags() | QtCore.Qt.ItemIsUserCheckable)
            impt.setCheckState(QtCore.Qt.Checked if node.important() else QtCore.Qt.Unchecked)
            self.setItem(row, 1, impt)
            urgent = QtWidgets.QTableWidgetItem()
            urgent.setFlags(urgent.flags() | QtCore.Qt.ItemIsUserCheckable)
            urgent.setCheckState(QtCore.Qt.Checked if node.urgent() else QtCore.Qt.Unchecked)
            self.setItem(row, 2, urgent)
            row += 1
#        print("Finished printing set {0}".format(self._nodes))

    def add(self, node):
        assert node
        #node.addListener(self)
        self._nodes.append(node)
        self._updateList()
#        print(self._nodes)

    def remove(self, node):
#        print("Removing {0} from set {1}".format(node, self._nodes))
        assert node
        assert node in self._nodes
        #node.removeListener(self)
        self._nodes.remove(node)
        self._updateList()
#        print(self._nodes)

    def onNodeUpdate(self, node):
        self._updateList()

    def _onCellChanged(self, row, col):
        cell = self.item(row, col)
        node = self._nodes[row]
        if col == 0:
            node.setTitle(cell.text())
        elif col == 1:
            node.setImportant(True if cell.checkState() == QtCore.Qt.Checked else False)
        elif col == 2:
            node.setUrgent(True if cell.checkState() == QtCore.Qt.Checked else False)
        print(node)

class QRelationList(QtWidgets.QListWidget):
    def __init__(self):
        super().__init__()
        self._relations = []
        self.clicked.connect(self._onClicked)

    def _setRelationVisibility(self, relation, isvisible):
            global qedges
            for key, qedge in qedges.items():
                rel = key[2]
                if rel is relation:
                    qedge.setVisible(isvisible)

    def _onClicked(self, index):
        assert index
        global selectedRelation
        row = index.row()
        selectedRelation = self._relations[row]
        isvisible = selectedRelation.visible
        chosenVisibility = self.item(row).checkState() == QtCore.Qt.Checked
        if isvisible != chosenVisibility:
            selectedRelation.visible = chosenVisibility
            self._setRelationVisibility(selectedRelation, chosenVisibility)

    def length(self):
        return len(self._relations)

    def _updateList(self):
        self.clear()
        for relation in self._relations:
            item = QtWidgets.QListWidgetItem(relation.name, self)
            item.setCheckState(QtCore.Qt.Checked if relation.visible else QtCore.Qt.Unchecked)
            self.addItem(item)
#        print("Finished printing set {0}".format(self._nodes))

    def add(self, rel):
        assert rel
        # rel.addListener(self)
        self._relations.append(rel)
        self._updateList()
#        print(self._nodes)

    def remove(self, rel):
#        print("Removing {0} from set {1}".format(node, self._nodes))
        assert rel
        assert rel in self._relation
        # rel.removeListener(self)
        self._relations.remove(rel)
        self._updateList()
#        print(self._nodes)

    def onNodeUpdate(self, node):
        self._updateList()

def makeNode(title="", isurgent=False, isimportant=False):
    """Adds a node to the graph and displays it on the canvas."""
    global nodeid
    nodeid += 1
    
    node = model.Node(title, isurgent, isimportant, nodeid)
    nodes[nodeid] = node

    qnode = QNodeWidget(nodeid)
    qnodes[nodeid] = qnode

    node.addListener(qnode.onNodeUpdate)
    return (node, QNodeProxy(qnode))

class QNodeProxy(QtWidgets.QGraphicsProxyWidget, event.Listener):
    def __init__(self, widget):
        QtWidgets.QGraphicsProxyWidget.__init__(self)
        self.setWidget(widget)

    def x(self):
        return self.pos().x()

    def y(self):
        return self.pos().y()

    def setPosition(self, x, y):
        self.setPos(x, y)
        self._publish()

    def _connect(self, relation, srcQNode, dstQNode):
        global newedge
        global qedges

        assert relation
        assert srcQNode
        assert dstQNode
        
        model.relation_connect(relation, srcQNode.id, dstQNode.id)

        qedge = QEdge.fromArrow(relation, newedge, srcQNode, dstQNode)
        qedge.setVisible(relation.visible)
        qedges[(srcQNode.id, dstQNode.id, relation)] = qedge
        self.scene().addItem(qedge)

    def _getTarget(self, event):
        nodes = [n for n in self.scene().items(event.scenePos()) if isinstance(n, QNodeProxy)]
        return nodes[0] if nodes else None
        
    def mousePressEvent(self, event):
        print("QNodeProxy::mousePressEvent")
        global selectedNode
        global selectedEdge
        global selectedRelation
        global editor
        
        button = event.button()
        mouse = event.pos()
        pos = self.scenePos()
        scene = event.scenePos()
        
        if selectedEdge:
            selectedEdge._unhighlight()
            selectedEdge = None
        
        if button == QtCore.Qt.RightButton:
            global newedge
            assert not newedge
            newedge = QArrow(selectedRelation, angle=math.pi/6, radius=20)
            x1 = self.pos().x() + 50
            y1 = self.pos().y() + 50
            dx = scene.x() - x1
            dy = scene.y() - y1
            r = distance(dx, dy)
            if r:
                theta = angle(dx, dy)
                x1 += 50 * math.cos(theta)
                y1 += 50 * math.sin(theta)
            newedge.setLine(x1, y1, scene.x(), scene.y())
            self.scene().addItem(newedge)
        elif button == QtCore.Qt.LeftButton:
            #editor.setNode(nodeFromQNode(self))
            if selectedNode is not self:
                if selectedNode:
                    qnode = qnodeFromNode(selectedNode.widget())
                    #qnode._unhighlight()
                #self._highlight()
            self._dx = scene.x() - pos.x()
            self._dy = scene.y() - pos.y()

        # Tell containing scene that we're handling this mouse event
        # so we don't initiate a canvas drag.
        # print("node Accepting!")
        event.accept()

    def mouseReleaseEvent(self, event):
        print("QNodeProxy::mouseReleaseEvent")        
        global newedge
        global editor
        global selectedNode
        global selectedRelation
        
        if newedge:
            target = self._getTarget(event)
            self.scene().removeItem(newedge)
            if target and target is not self: # hovering over another node
                self._connect(selectedRelation, self.widget(), target.widget())
            newedge = None
        elif not self._movedp:
            if selectedNode is self:
                selectedNode = None
                #editor.setNode(None)
                #self._unhighlight()
            else:
                selectedNode = self
               # editor.setNode(nodeFromQNode(self))
                #self._highlight()
        else:
            selectedNode = self
            #editor.setNode(nodeFromQNode(self))
            
        self._movedp = False
        event.accept()

    def mouseMoveEvent(self, event):
        print("QNodeProxy::mouseMoveEvent")
        global destNode
        global newedge
        
        self._movedp = True
        
        scene = event.scenePos()
        mouse = event.pos()
        pos = self.scenePos()

        if newedge:
            line = newedge.line()
            x1 = self.pos().x() + 50
            y1 = self.pos().y() + 50
            dx = scene.x() - x1
            dy = scene.y() - y1
            r = distance(dx, dy)
            if r:
                theta = angle(dx, dy)
                x1 += 50 * math.cos(theta)
                y1 += 50 * math.sin(theta)
            newedge.setLine(x1, y1, scene.x(), scene.y())
        else:
            newpos = QtCore.QPointF(scene.x() - self._dx, scene.y() - self._dy)
            self.setPos(newpos)
            self._publish()
        event.accept()

    def _highlighted():
        return self._highlightedp
    
class QNodeWidget(QtWidgets.QWidget, event.Listener):
    def __init__(self, id):
        QtWidgets.QWidget.__init__(self)
        #self.setMaximumWidth(300)
        self._layout = QtWidgets.QVBoxLayout(self)

        self._pixmap = QtGui.QPixmap(".\\pic.jpg")
        self._image = QtWidgets.QLabel()
        #policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        #self._image.setSizePolicy(policy)
        self._image.setPixmap(self._pixmap)
        self._image.setScaledContents(True)
        #self._image.setMaximumHeight(200)
        self._image.setMaximumWidth(300)
        self._image.setMaximumHeight(200)
        self._layout.addWidget(self._image)

        self._text = QtWidgets.QLabel()
        # label.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)
        font = self._text.font()
        font.setPointSize(20)
        self._text.setFont(font)
        self._text.setWordWrap(True)
        self._layout.addWidget(self._text)

        self.id = id
        
        #self._dx = 0
        #self._dy = 0
        #self._movedp = False
        #self.setPos(0, 0)

    def onNodeUpdate(self, node):
        self._text.setText(node.title())

class QNodeView(QtWidgets.QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        brush = QtGui.QBrush(QtGui.QColor(64, 64, 64))
        self.setBackgroundBrush(brush)
        self._selected = False
        self._listeners = []
        #self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        #self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        #self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

    def _removeEdge(self, e):
        global qedges
        self.scene().removeItem(e)
        e._origin.removeListener(e._onNodeUpdate)
        e._dest.removeListener(e._onNodeUpdate)
        e._relation.disconnect(e._origin.id, e._dest.id)
        del qedges[(e._origin.id, e._dest.id, e._relation)]

    def _isStageSelected(self):
        return not selectedEdge and not selectedNode
    
    def keyPressEvent(self, event):
        global selectedEdge
        global selectedNode
        global selectedRelation
        global qedges
        global nodelist
        
        key = event.key()
        if key == QtCore.Qt.Key_Space:
            rect = self.scene().itemsBoundingRect()
            self.scene().setSceneRect(rect)
            return
        if self._isStageSelected():
            return
        if key != QtCore.Qt.Key_Delete and key != QtCore.Qt.Key_Backspace:
            return

        if selectedEdge:
            self._removeEdge(selectedEdge)
            selectedEdge = None
        else:
            self.scene().removeItem(selectedNode)
            nodeid = selectedNode.id
            edgesToRemove = [v for k, v in qedges.items() if k[0] == nodeid or k[1] == nodeid]
            for e in edgesToRemove:
                self._removeEdge(e)
            nodelist.remove(nodeFromQNode(selectedNode))
            selectedNode = None
                
    def wheelEvent(self, event):
        point = event.angleDelta()
        dy = point.y()
        if dy > 0:
            self.scale(1.1, 1.1)
        elif dy < 0:
            self.scale(1/1.1, 1/1.1)


class QNodeScene(QtWidgets.QGraphicsScene):
    def __init__(self):
        QtWidgets.QGraphicsScene.__init__(self)


class QNodePalette(QtWidgets.QListWidget):
    def __init__(self):
        QtWidgets.QListWidget.__init__(self)
        # TODO: Add task and goal items to the list
        # TODO: Implement drag and drop from this list to the graph

class QMainWindow(QtWidgets.QMainWindow):
    def __init__(self, title):
        super().__init__()

        global editor
        global nodelist
        
        # set size to 70% of screen
        self.resize(QtWidgets.QDesktopWidget().availableGeometry(self).size() * 0.7)

        self._scene = QNodeScene()
        #self._scene.setSceneRect(0, 0, 100, 100)

        # add the scene to the view
        self._view = QNodeView(self._scene)
        # self._view.setSceneRect(0, 0, 500, 500)

        # make the view the main widget of the window
        self.setCentralWidget(self._view)

        # add a dock with a task editor
        # editor = QNodeEditor()
        # self._editor = QtWidgets.QDockWidget("Edit Object")
        # self._editor.setWidget(editor)

        self._list = QtWidgets.QDockWidget("Goals && Tasks")
        nodelist = QNodeList()
        self._list.setWidget(nodelist)

        self._relationList = QtWidgets.QDockWidget("Relations")
        relationList = QRelationList()
        self._relationList.setWidget(relationList)

        self.setWindowTitle(title)
        # self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._editor)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self._list)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._relationList)

        self._palette = QtWidgets.QDockWidget("Palette")
        self._palette.setWidget(QNodePalette())
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._palette)

        self._toolbar = self.addToolBar("Task")
        self._addButton("&New Object", QtWidgets.QStyle.SP_FileIcon, self._onNewNode)
        self._addButton("&Save Graph", QtWidgets.QStyle.SP_DialogSaveButton, self._onSave)
        self._addButton("&Load Graph", QtWidgets.QStyle.SP_DialogOpenButton, self._onLoad)
        # self._toolbar.addSeparator()

        # add relation selector
        # relsel = QtWidgets.QComboBox()
        for rel in model.getRelations():
            relationList.add(rel)
        if relationList.length() > 0:
            relationList.setCurrentRow(0)
        #     relsel.addItem(rel.name)
        self._selectRelation(0)
        # self._relationList.setCurrentRow(0)
        # relsel.currentIndexChanged.connect(self._selectRelation)
        # self._toolbar.addWidget(relsel)

    def _selectRelation(self, index):
        global selectedRelation
        selectedRelation = model.getRelations()[index]

    def _addButton(self, text, icontype, callback):
        assert self._toolbar
        icon = self.style().standardIcon(icontype)
        action = QtWidgets.QAction(icon, text, self)
        action.triggered.connect(callback)
        action.setIconVisibleInMenu(True)
        self._toolbar.addAction(action)

    def _onSave(self):
        filename = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", "", ".todo")
        print("Saving tasks to file: {0}".format(filename))
        print("State: {0}".format(getState()))
        # TODO: write graph to file
        saveState(filename[0] + filename[1], getState())

    def _onLoad(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Load file", "")
        if not filename[0]:
            return
        print("Loading tasks from file: {0}".format(filename))
        state = loadState(filename[0])
        self._scene.clear() # remove all qedges and qnodes from scene
        
        # set state vars
        global nodeid
        nodeid = state["nodeid"]

        global nodes
        nodes = {}
        
        global qnodes
        qnodes = {}
        
        newnodes = state["nodes"]
        for id, node in newnodes.items():
            nodes[id] = node.Node(title=node["title"],
                                  urgent=node["urgent"],
                                  important=node["important"],
                                  id=id)
            qnodes[id] = QNode(title=node["title"], id=id)
            qnodes[id].setPosition(node["x"], node["y"])
            self._scene.addItem(qnodes[id])
            nodes[id].addListener(qnodes[id])

        global outnodes
        outnodes = state["outnodes"]

        global innodes
        innodes = state["innodes"]

        # restore qedges
        for origin, dests in outnodes.items():
            for dest in dests:
                qedge = QEdge(qnodes[origin], qnodes[dest])
                qnodes[origin].addListener(qedge._onNodeUpdate)
                qnodes[dest].addListener(qedge._onNodeUpdate)
                self._scene.addItem(qedge)
    
    def _onNewNode(self):
        global editor
        global selectedNode
        global nodelist
        node, qnode = makeNode("New Task")
        nodelist.add(node)
        self._scene.addItem(qnode)
        # if selectedNode:
        #     selectedNode._unhighlight()
        selectedNode = qnode
        #selectedNode._highlight()
        # editor.setNode(node)

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
