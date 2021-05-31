# graph.py -- A network layout program.
import math
import sys
import random
import model
import event
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QTreeView

zvalue_max = 0.0
zvalue_increment = 1.0
newedge = None
editor = None
nodelist = None

no_selected_item = None
__selected_item = no_selected_item
def get_selected_item():
    global __selected_item
    return __selected_item

def set_selected_item(item):
    global __selected_item
    if __selected_item and __selected_item is not item:
        __selected_item.unselect()
    __selected_item = item
    if item:
        item.select()

no_active_relation = 0
active_relation = no_active_relation
def set_active_relation(relation_id):
    global active_relation
    active_relation = relation_id

def get_active_relation():
    return active_relation

def is_relation_active():
    return active_relation > 0


qnodes = {} # maps node IDs to QNode objects
qedges = {} # maps (origin node id, destination node id, relation) to a QEdge


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
    def __init__(self, relation_id, radius=20, angle=math.pi/6):
        QtWidgets.QGraphicsItemGroup.__init__(self)
        self.id = relation_id
        self._radius = radius
        self._angle = angle

        relation = model.get_relation(relation_id)
        color = relation.color
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        stroke_color = QtGui.QColor(color.r, color.g, color.b)
        #palette.setColor(self.backgroundRole(), bgcolor)
        stroke.setColor(stroke_color)
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

    def setLine(self, x1, y1, x2, y2):
        self._line.setLine(x1, y1, x2, y2)
        self._updateLines()

class QEdge(QArrow):
    def __init__(self, relation_id, origin, dest, radius=20, angle=math.pi/6):
        QArrow.__init__(self, relation_id, radius=radius, angle=angle)
        self.setZValue(-1.0)
        self._origin = origin
        self._dest = dest
        self._origin.add_listener("graphical_object_changed", self._onNodeUpdate)
        self._dest.add_listener("graphical_object_changed", self._onNodeUpdate)
        self._setArrows()
    
    def delete(self):
        model.disconnect(self.id, self._origin.widget().id, self._dest.widget().id)

    def _setArrows(self):
        start = self._origin.pos() + midpoint(self._origin)
        end = self._dest.pos() + midpoint(self._dest)
        self.setLine(start.x(), start.y(), end.x(), end.y())

    def select(self):
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        relation = model.get_relation(self.id)
        color = relation.color
        stroke.setColor(QtGui.QColor(color.r, color.g, color.b))
        pen = QtGui.QPen(stroke, 2)
        self._line.setPen(pen)

    def unselect(self):
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        relation = model.get_relation(self.id)
        color = relation.color
        stroke.setColor(QtGui.QColor(color.r, color.g, color.b))
        pen = QtGui.QPen(stroke, 1)
        self._line.setPen(pen)

    def _onNodeUpdate(self, node):
        assert node is self._origin or node is self._dest
        self._setArrows()

    @staticmethod
    def fromArrow(arrow, origin, dest):
        edge = QEdge(arrow.id, origin, dest, radius=arrow._radius, angle=arrow._angle)
        return edge

    def mousePressEvent(self, event):
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

        set_selected_item(self)

class QCollectionFilter(QtWidgets.QTableWidget):
    def __init__(self, collection, predicate):
        #super().__init__(0, 2)
        super().__init__()

        self._predicate = predicate
        self._collection = collection
        self._matches = set()
        self._matches_list = []
        self._collection.add_listener("object_created", self._object_created)
        self._collection.add_listener("object_deleted", self._object_deleted)
        self._collection.add_listener("object_changed", self._object_changed)
        for object in collection:
            self._object_created(object.id, "view")

    def closeEvent(self, event):
        self._collection.remove_listener("object_created", self._object_created)
        self._collection.remove_listener("object_deleted", self._object_deleted)
        self._collection.remove_listener("object_changed", self._object_changed)

    def _object_created(self, object_id, source):
        object = self._collection.get_member(object_id)
        if self._predicate(object):
            # Add the object to the widget
            self._matches_list.append(object_id)
            self._matches.add(object_id)
            nrows = len(self._matches_list)
            row = nrows - 1
            self.setRowCount(nrows)
            self.member_added(object, row)

    def member_added(self, member, row):
        pass

    def _object_deleted(self, object_id):
        if object_id in self._matches:
            # Remove the object from the widget
            row = self._matches_list.index(object_id)
            self.removeRow(row)
            self._matches_list.remove(object_id)
            self._matches.remove(object_id)

    def _object_changed(self, object_id):
        if self._predicate(model.get_object(object_id)):
            if object_id in self._matches:
                # TODO: Update the object in the display
                # NB: Changing table items here will cause an infinite loop
                pass
            else:
                self._object_created(object_id, "view")
        else:
            self._object_deleted(object_id)

class QObjectFilter(QCollectionFilter):
    def __init__(self, collection, predicate):
        super().__init__(collection, predicate)
        self.setColumnCount(2)
        header_class = QtWidgets.QTableWidgetItem("Class")
        header_class.setTextAlignment(QtCore.Qt.AlignLeft)
        self.setHorizontalHeaderItem(0, header_class)
        header_title = QtWidgets.QTableWidgetItem("Title")
        header_title.setTextAlignment(QtCore.Qt.AlignLeft)
        self.setHorizontalHeaderItem(1, header_title)
        self.cellChanged.connect(self._cellChanged)

    def member_added(self, member, row):
        class_name = member.klass.name
        object_title = member.get_field("Title")
        class_item = QtWidgets.QTableWidgetItem(class_name)
        class_item.setFlags(class_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 0, class_item)
        object_item = QtWidgets.QTableWidgetItem(object_title)
        self.setItem(row, 1, object_item)

    def _cellChanged(self, row, col):
        object_id = self._matches_list[row]
        object = model.get_object(object_id)
        item = self.item(row, col)
        object.set_field("Title", item.text())

def make_graphical_edge(relation_id, source_object_id, dest_object_id):
    source_grob = get_object(source_object_id)
    dest_grob = get_object(dest_object_id)
    graphical_edge = QEdge(relation_id, source_grob, dest_grob)
    relation = model.get_relation(relation_id)
    graphical_edge.setVisible(relation.visible)
    qedges[(relation_id, source_object_id, dest_object_id)] = graphical_edge
    return graphical_edge

class QNodeProxy(QtWidgets.QGraphicsProxyWidget, event.Emitter):
    def __init__(self, widget):
        QtWidgets.QGraphicsProxyWidget.__init__(self)
        event.Emitter.__init__(self)
        self.setWidget(widget)
        self._dx = 0
        self._dy = 0

    def x(self):
        return self.pos().x()

    def y(self):
        return self.pos().y()

    def setPosition(self, x, y):
        self.setPos(x, y)
        self.emit()
    
    def delete(self):
        model.delete_object(self.widget().id)

    def _connect(self, newedge, source_proxy, dest_proxy):
        global qedges
        source_widget = source_proxy.widget()
        dest_widget = dest_proxy.widget()

        model.connect(newedge.id, source_widget.id, dest_widget.id)
        #qedge = make_graphical_edge(newedge.id, source_widget.id, dest_widget.id)
        # qedge = QEdge.fromArrow(newedge, source_proxy, dest_proxy)
        # relation = model.get_relation(newedge.id)
        # qedge.setVisible(relation.visible)
        # qedges[(source_widget.id, dest_widget.id, newedge.id)] = qedge
        #self.scene().addItem(qedge)

    def _getTarget(self, event):
        nodes = [n for n in self.scene().items(event.scenePos()) if isinstance(n, QNodeProxy)]
        return nodes[0] if nodes else None
    
    def _focus(self):
        """Place the object in front of all others."""
        global zvalue_max
        zvalue_max = max(self.zValue(), zvalue_max) + zvalue_increment
        self.setZValue(zvalue_max)

    def select(self):
        self._focus()
        self.widget().setLineWidth(2)
    
    def unselect(self):
        self.widget().setLineWidth(0)

    def mousePressEvent(self, event):
        global selectedEdge
        global editor

        button = event.button()
        mouse = event.pos()
        pos = self.scenePos()
        scene = event.scenePos()

        if button == QtCore.Qt.LeftButton:
            set_selected_item(self)
            self._dx = scene.x() - pos.x()
            self._dy = scene.y() - pos.y()
        elif button == QtCore.Qt.RightButton and is_relation_active():
            global newedge
            newedge = QArrow(get_active_relation())
            self.scene().addItem(newedge)

        # Tell containing scene that we're handling this mouse event
        # so we don't initiate a canvas drag.
        event.accept()

    def mouseReleaseEvent(self, event):
        global newedge
        global editor

        if newedge:
            target = self._getTarget(event)
            self.scene().removeItem(newedge)
            if target and target is not self: # hovering over another node
                self._connect(newedge, self, target)
            newedge = None

        event.accept()

    def mouseMoveEvent(self, event):
        global newedge

        scene = event.scenePos()
        mouse = event.pos()
        pos = self.scenePos()

        if newedge:
            start = self.pos() + midpoint(self)
            newedge.setLine(start.x(), start.y(), scene.x(), scene.y())
        else:
            newpos = QtCore.QPointF(scene.x() - self._dx, scene.y() - self._dy)
            self.setPos(newpos)
            self.emit("graphical_object_changed", self)
        event.accept()

    def _object_changed(self, object_id):
        object = model.get_object(object_id)
        self.setVisible(object.get_field("Visible"))

class QNodeWidget(QtWidgets.QFrame, event.Emitter):
    def __init__(self, id):
        QtWidgets.QFrame.__init__(self)
        #self.setMaximumWidth(300)
        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setFrameShadow(QtWidgets.QFrame.Plain)
        self.setAutoFillBackground(True)
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

        self.id = id
        self._text = QtWidgets.QLabel()
        # label.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)
        font = self._text.font()
        font.setPointSize(20)
        self._text.setFont(font)
        self._text.setWordWrap(True)
        self._layout.addWidget(self._text)
        self.onNodeUpdate(id)

    def onNodeUpdate(self, object_id):
        object = model.get_object(object_id)

        # Set background color
        palette = self.palette()
        color = object.get_field("Color")
        bgcolor = QtGui.QColor(color.r, color.g, color.b)
        palette.setColor(self.backgroundRole(), bgcolor)
        self.setPalette(palette)

        # Set label
        self._text.setText(object.get_field("Title"))

        self.emit("object_changed", object_id)

def midpoint(qgraphicsitem):
    r = qgraphicsitem.boundingRect()
    x = r.width() / 2
    y = r.height() / 2
    p = QtCore.QPointF(x, y)
    return p

class QNodeView(QtWidgets.QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        scene.setSceneRect(0, 0, self.width(), self.height())
        self.setAcceptDrops(True)
        brush = QtGui.QBrush(QtGui.QColor(64, 64, 64))
        self.setBackgroundBrush(brush)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def _removeEdge(self, e):
        global qedges
        self.scene().removeItem(e)
        e._origin.remove_listener(e._onNodeUpdate)
        e._dest.remove_listener(e._onNodeUpdate)
        e._relation.disconnect(e._origin.id, e._dest.id)
        del qedges[(e._origin.id, e._dest.id, e._relation)]

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()
        class_id = int(event.mimeData().text())
        klass = model.get_class(class_id)
        object = make_object(class_id, "New {0}".format(klass.name))
        self.scene().addItem(object)
        set_selected_item(object)

        # Position the object so the cursor lies over its center
        position = self.mapToScene(event.pos())
        mid_position = position - midpoint(object)
        object.setPos(mid_position)

        # Allow the user to delete the node immediately after adding by pressing backspace
        self.setFocus()

    def keyPressEvent(self, event):
        selected_item = get_selected_item()
        key = event.key()
        if key == QtCore.Qt.Key_Space:
            rect = self.scene().itemsBoundingRect()
            self.scene().setSceneRect(rect)
        elif selected_item and key in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            set_selected_item(no_selected_item)
            selected_item.delete()

    def wheelEvent(self, event):
        point = event.angleDelta()
        dy = point.y()
        if dy > 0:
            self.scale(1.1, 1.1)
        elif dy < 0:
            self.scale(1/1.1, 1/1.1)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        selected_item = get_selected_item()
        if not self.itemAt(event.pos()) and selected_item:
            set_selected_item(no_selected_item)

def make_graphical_object(object_id):
    qnode = QNodeWidget(object_id)
    proxy = QNodeProxy(qnode)
    qnodes[object_id] = proxy
    object = model.get_object(object_id)
    object.add_listener("object_changed", qnode.onNodeUpdate)
    qnode.add_listener("object_changed", proxy._object_changed)
    return proxy

def make_object(klass, *args):
    object_id = model.make_object(klass, *args, source="view")
    graphical_object = make_graphical_object(object_id)
    return graphical_object

def get_object(object_id):
    return qnodes[object_id]

def delete_object(object_id):
    pass

def get_edge(relation_id, src_id, dst_id):
    return qedges[(relation_id, src_id, dst_id)]

class QNodeScene(QtWidgets.QGraphicsScene):
    def __init__(self, objects, relations):
        super().__init__()
        self._objects = objects
        self._relations = relations
        self._objects.add_listener("object_created", self._object_created)
        self._objects.add_listener("object_deleted", self._object_deleted)
        self._relations.add_listener("objects_connected", self._objects_connected)
        self._relations.add_listener("objects_disconnected", self._objects_disconnected)
        #self._collection.add_listener("object_changed", self._object_changed)

    def _object_created(self, object_id, source):
        if source == "model":
            # TODO: Position in a suitable place
            graphical_object = make_graphical_object(object_id)
            self.addItem(graphical_object)

    def _object_deleted(self, object_id):
        object = get_object(object_id)
        self.removeItem(object)
        # TODO: Remove edges connected to the object

    def _objects_connected(self, rel_id, src_id, dst_id, source):
        if source == "model":
            graphical_edge = make_graphical_edge(rel_id, src_id, dst_id)
            self.addItem(graphical_edge)

    def _objects_disconnected(self, rel_id, src_id, dst_id):
        edge = get_edge(rel_id, src_id, dst_id)
        self.removeItem(edge)

class QCollectionList(QtWidgets.QListWidget):
    def __init__(self, collection):
        QtWidgets.QListWidget.__init__(self)
        self._collection = collection
        self._collection.add_listener("object_created", self._object_created)
        self._collection.add_listener("object_deleted", self._object_deleted)
        self._collection.add_listener("object_changed", self._object_changed)
        for member in collection:
            self._object_created(member.id, "view")
        self.clicked.connect(self._clicked)

    def members(self):
        return list(map(
            lambda row: self.item(row).data(QtCore.Qt.ItemDataRole.UserRole),
            range(self.count())
        ))

    def _clicked(self, index):
        item = self.item(index.row())
        member_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        member = self._collection.get_member(member_id)
        is_checked = item.checkState() == QtCore.Qt.Checked
        self.member_clicked(member, is_checked)

    def member_added(self, member):
        pass
    
    def member_removed(self):
        pass

    def member_clicked(self, member, is_checked):
        pass

    def _object_created(self, member_id, source):
        member = self._collection.get_member(member_id)
        item = QtWidgets.QListWidgetItem(member.name)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, member_id)
        item.setCheckState(QtCore.Qt.Checked if member.visible else QtCore.Qt.Unchecked)
        self.addItem(item)
        self.setCurrentItem(item)
        self.member_added(member)
    
    def _id_to_item(self, member_id):
        item = list(filter(
            lambda item: item.data(QtCore.Qt.ItemDataRole.UserRole) == member_id,
            [self.item(row) for row in range(self.count())]
        ))[0]
        return item

    def _object_deleted(self, member_id):
        item = self._id_to_item(member_id)
        self._members.remove(member_id)
        self.takeItem(item.row())
        self.member_removed()

    def _object_changed(self, member_id):
        item = self._id_to_item(member_id)
        member = self._collection.get_member(member_id)
        item.setText(member.name)

        # TODO: Implement drag and drop from this list to the graph

    def closeEvent(self, event):
        self._collection.remove_listener("object_created", self._object_created)
        self._collection.remove_listener("object_deleted", self._object_deleted)
        self._collection.remove_listener("object_changed", self._object_changed)

class QNodePalette(QCollectionList):
    def __init__(self, collection):
        super().__init__(collection)
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)

    def member_clicked(self, member, is_checked):
        member.set_visible(is_checked)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        mime_data = QtCore.QMimeData()
        class_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        mime_data.setText(str(class_id))
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec()

class QRelationList(QCollectionList):
    def __init__(self, collection):
        super().__init__(collection)
        #self.clicked.connect(self._clicked)

    def member_added(self, relation):
        set_active_relation(relation.id)
    
    def member_removed(self):
        remaining_members = self.members()
        active_relation = remaining_members[0] if remaining_members else no_active_relation
        set_active_relation(active_relation)

    def member_clicked(self, relation, is_checked):
        set_active_relation(relation.id)
        # TODO: relation.set_visible(is_checked)

class QMainWindow(QtWidgets.QMainWindow):
    def __init__(self, title):
        super().__init__()

        global editor
        global nodelist

        # set size to 70% of screen
        #self.resize(QtWidgets.QDesktopWidget().availableGeometry(self).size() * 0.7)

        self._scene = QNodeScene(model.objects, model.relations)
        self._view = QNodeView(self._scene)
        self.setCentralWidget(self._view)

        self._tagmodel = QTagModel()
        self._tagview = QTagView(self._tagmodel)
        self._tagdock = QtWidgets.QDockWidget("Tags")
        self._tagdock.setWidget(self._tagview)

        self._list = QtWidgets.QDockWidget("Objects")
        show_actionable = model.eq(model.field("Innodes"), model.const(0))
        nodelist = QObjectFilter(model.objects, show_actionable)
        self._list.setWidget(nodelist)

        self._relationList = QtWidgets.QDockWidget("Relations")
        show_all = lambda member: True
        relationList = QRelationList(model.relations)
        self._relationList.setWidget(relationList)

        self.setWindowTitle(title)
        # self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._editor)

        self._palette = QtWidgets.QDockWidget("Classes")
        self._palette.setWidget(QNodePalette(model.classes))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._palette)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._relationList)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self._list)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self._tagdock)

        self._toolbar = self.addToolBar("Task")
        self._addButton("&New Object", QtWidgets.QStyle.SP_FileIcon, self._onNewNode)
        #self._addButton("&Save Graph", QtWidgets.QStyle.SP_DialogSaveButton, self._onSave)
        #self._addButton("&Load Graph", QtWidgets.QStyle.SP_DialogOpenButton, self._onLoad)
        self._toolbar.addSeparator()

    def _addButton(self, text, icontype, callback):
        assert self._toolbar
        icon = self.style().standardIcon(icontype)
        action = QtWidgets.QAction(icon, text, self)
        action.triggered.connect(callback)
        action.setIconVisibleInMenu(True)
        self._toolbar.addAction(action)
    
    def _onNewNode(self, *args):
        a = model.make_object(model.tag_class, "tag A")
        b = model.make_object(model.tag_class, "tag B")
        model.connect(model.precedes, a, b)

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

def make_tree(key, *children):
    parent = {
        "key": key,
        #"tag": model.make_tag(key),
        "children": children,
        "visible": True,
        "parent": None,
        "row": 0
    }
    row = 0
    for child in children:
        child["parent"] = parent
        child["row"] = row
        row += 1
    return parent

class QTagModel(QtCore.QAbstractItemModel):
    def __init__(self, relation=None, parent=None):
        super().__init__(parent)
        self._relation = relation
        self._root = make_tree("Engle",
            make_tree("David"),
            make_tree("Jana"),
            make_tree("Tara",
                make_tree("Ora"),
                make_tree("Daley")
            ),
            make_tree("Bri",
                make_tree("Mavrik")
            )
        )

    def headerData(self, section, orientation, role):
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return QtCore.QVariant()
        headers = {
            0: "Tag",
            1: "Visible",
        }
        return QtCore.QVariant(headers.get(section, "No Header"))

    def index(self, row, col, parent):
        if not self.hasIndex(row, col, parent):
            rval = QtCore.QModelIndex()
        else:
            parent_item = None
            if not parent.isValid():
                parent_item = self._root
            else:
                parent_item = parent.internalPointer()

            child_item = parent_item['children'][row]
            if child_item:
                rval = self.createIndex(row, col, child_item)
            else:
                rval = QtCore.QModelIndex()
        return rval

    def parent(self, index):
        if not index.isValid():
            rval = self.createIndex(self._root['row'], 0, self._root)
        else:
            child_item = index.internalPointer()
            parent_item = child_item['parent']
            if not parent_item:
                rval = QtCore.QModelIndex()
            else:
                rval = self.createIndex(parent_item['row'], 0, parent_item)
        return rval

    def rowCount(self, parent):
        if not parent.isValid():
            rval = len(self._root['children'])
        else:
            parent_item = parent.internalPointer()
            rval = len(parent_item['children'])
        return rval

    def columnCount(self, parent):
        return 2

    def data(self, index, role):
        if not index.isValid():
            rval = QtCore.QVariant()
        elif role == QtCore.Qt.ItemDataRole.CheckStateRole and index.column() == 1:
            item = index.internalPointer()
            rval = QtCore.Qt.Checked if item['visible'] else QtCore.Qt.Unchecked
        elif role != QtCore.Qt.ItemDataRole.DisplayRole:
            rval = QtCore.QVariant()
        elif not index.isValid():
            rval = self._root['key']
        elif index.column() == 0:
            rval = index.internalPointer()['key']
        else:
            rval = QtCore.QVariant()
        return rval

    def setData(self, index, value, role):
        if role == QtCore.Qt.ItemDataRole.CheckStateRole and index.column() == 1:
            item = index.internalPointer()
            item['visible'] = True if value == QtCore.Qt.Checked else False
            return True

    def flags(self, index):
        if not index.isValid():
            return 0
        flags = QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        if index.column() == 1:
            flags |= QtCore.Qt.ItemFlag.ItemIsUserCheckable
        return flags

class QTagView(QTreeView):
    def __init__(self, model):
        super().__init__()
        self.setModel(model)