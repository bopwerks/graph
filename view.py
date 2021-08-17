# graph.py -- A network layout program.
import math
import lang
import log
import model
import event
import sys
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import QColorDialog, QHBoxLayout, QListWidget, QMessageBox, QPushButton, QTextEdit, QTreeView, QWidget

zvalue_max = 0.0
zvalue_increment = 1.0
newedge = None

no_selected_item = None

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

        color = model.relation_get_color(relation_id)
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        stroke.setColor(QtGui.QColor(color.r, color.g, color.b))
        self._thickpen = QtGui.QPen(stroke, 2)
        self._thinpen = QtGui.QPen(stroke, 1)

        self._line = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._line.setPen(self._thinpen)
        self._arrow1 = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._arrow1.setPen(self._thickpen)
        self._arrow2 = QtWidgets.QGraphicsLineItem(0, 0, 0, 0)
        self._arrow2.setPen(self._thickpen)

        self.addToGroup(self._line)
        self.addToGroup(self._arrow1)
        self.addToGroup(self._arrow2)
        self._updateLines()
    
    def setColor(self, color):
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        stroke.setColor(color)
        self._thickpen = QtGui.QPen(stroke, 2)
        self._thinpen = QtGui.QPen(stroke, 1)
        self._line.setPen(self._thinpen)
        self._arrow1.setPen(self._thickpen)
        self._arrow2.setPen(self._thickpen)
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

def boundary(dest_node, source_node, line):
    dest_pos = dest_node.pos()
    dest_bounding_rect = dest_node.boundingRect()
    top = dest_pos.y()
    left = dest_pos.x()
    bottom = top + dest_bounding_rect.height()
    right = left + dest_bounding_rect.width()

    m = line.dy() / line.dx() if line.dx() else 0
    p0 = source_node.pos() + midpoint(source_node)
    x0 = p0.x()
    y0 = p0.y()

    vectors = []
    for side in (right, left):
        y1 = m * (side - x0) + y0
        if top <= y1 and y1 <= bottom:
            vectors.append(QtCore.QPointF(side, y1))
    
    for side in (top, bottom):
        x1 = ((side - y0)/m + x0) if m else x0
        if left <= x1 and x1 <= right:
            vectors.append(QtCore.QPointF(x1, side))
    
    def distance(q):
        r = q - p0
        return math.sqrt(QtCore.QPointF.dotProduct(r, r))
    vectors.sort(key=distance)
    return vectors[0]

class QObjectDelegate(object):
    def __init__(self, qedge):
        self.qedge = qedge
    
    def object_moved(self, qobject):
        self.qedge.object_moved()

class QEdge(QArrow):
    def __init__(self, relation_id, edge_id, origin, dest, radius=20, angle=math.pi/6):
        QArrow.__init__(self, relation_id, radius=radius, angle=angle)
        self._edge_id = edge_id
        self.setZValue(-1.0)
        self._origin = origin
        self._dest = dest
        self._origin.add_listener("graphical_object_changed", self._onNodeUpdate)
        self._dest.add_listener("graphical_object_changed", self._onNodeUpdate)
        self._relation_id = relation_id
        self._setArrows()
        is_visible = model.edge_is_visible(edge_id)
        self.setVisible(is_visible)
    
    def set_color(self, color):
        self.setColor(QtGui.QColor(color.r, color.g, color.b))
    
    def delete(self):
        self._origin.remove_listener("graphical_object_changed", self._onNodeUpdate)
        self._dest.remove_listener("graphical_object_changed", self._onNodeUpdate)
        model.edge_delete(self._edge_id)

    def _setArrows(self):
        start = self._origin.pos() + midpoint(self._origin)
        end = self._dest.pos() + midpoint(self._dest)
        self.setLine(start.x(), start.y(), end.x(), end.y())
        end = boundary(self._dest, self._origin, self._line.line())
        self.setLine(start.x(), start.y(), end.x(), end.y())

    def select(self):
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        color = model.relation_get_color(self._relation_id)
        stroke.setColor(QtGui.QColor(color.r, color.g, color.b))
        pen = QtGui.QPen(stroke, 2)
        self._line.setPen(pen)

    def unselect(self):
        stroke = QtGui.QBrush(QtCore.Qt.SolidPattern)
        color = model.relation_get_color(self._relation_id)
        stroke.setColor(QtGui.QColor(color.r, color.g, color.b))
        pen = QtGui.QPen(stroke, 1)
        self._line.setPen(pen)

    def _onNodeUpdate(self, node):
        assert node is self._origin or node is self._dest
        self._setArrows()

    def mousePressEvent(self, event):
        button = event.button()
        mouse = event.pos()
        pos = self.scenePos()
        scene = event.scenePos()

        if button != QtCore.Qt.LeftButton:
            event.ignore()
            return

        for view in self.scene().views():
            view.set_selected_item(self)

class QCollectionFilterDock(QtWidgets.QDockWidget):
    def __init__(self, title):
        QtWidgets.QDockWidget.__init__(self, title)
        self.to_be_deleted = False
    
    def setWidget(self, widget):
        super().setWidget(widget)
        self.id = widget.id
    
    def closeEvent(self, event):
        if not self.to_be_deleted:
            event.ignore()
            self.to_be_deleted = True
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            def delete():
                model.object_filter_delete(self.id)
            timer.timeout.connect(delete)
            timer.start(0)

class QObjectFilter(QtWidgets.QTableWidget, model.Delegate):
    def __init__(self, object_filter_id):
        QtWidgets.QTableWidget.__init__(self)
        model.Delegate.__init__(self)
        self.id = object_filter_id
        self.predicate = model.object_filter_get_predicate(object_filter_id)
        self._matches = set()
        self._matches_list = []

        self.setColumnCount(2)
        header_class = QtWidgets.QTableWidgetItem("Class")
        header_class.setTextAlignment(QtCore.Qt.AlignLeft)
        self.setHorizontalHeaderItem(0, header_class)

        header_title = QtWidgets.QTableWidgetItem("Title")
        header_title.setTextAlignment(QtCore.Qt.AlignLeft)
        self.setHorizontalHeaderItem(1, header_title)

        for object_id in model.get_objects():
            self.object_created(object_id, "view")

        model.add_delegate(self)
    
    def insert_object(self, object_id, row):
        class_id = model.object_get_class(object_id)
        class_name = model.class_get_name(class_id)
        class_item = QtWidgets.QTableWidgetItem(class_name)
        class_item.setFlags(class_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 0, class_item)

        object_name = model.object_get_name(object_id)
        object_item = QtWidgets.QTableWidgetItem(object_name)
        object_item.setFlags(object_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
        self.setItem(row, 1, object_item)
    
    def object_created(self, object_id, source):
        self._matches_list.append(object_id)
        self._matches.add(object_id)
        nrows = len(self._matches_list)
        row = nrows - 1
        self.setRowCount(nrows)
        self.insert_object(object_id, row)
    
    def object_changed(self, object_id, source):
        if not self.predicate(object_id):
            self.object_deleted(object_id, source)
        elif object_id in self._matches:
            row = self._matches_list.index(object_id)
            self.insert_object(object_id, row)
        else:
            self.object_created(object_id, source)
    
    def object_deleted(self, object_id, source):
        if object_id in self._matches:
            row = self._matches_list.index(object_id)
            self.removeRow(row)
            self._matches_list.remove(object_id)
            self._matches.remove(object_id)

    def closeEvent(self, event):
        model.remove_delegate(self)

def make_edge(edge_id):
    relation_id = model.edge_get_relation(edge_id)
    source_object_id = model.edge_get_source_object(edge_id)
    dest_object_id = model.edge_get_destination_object(edge_id)
    source_grob = get_object(source_object_id)
    dest_grob = get_object(dest_object_id)
    graphical_edge = QEdge(relation_id, edge_id, source_grob, dest_grob)
    qedges[edge_id] = graphical_edge
    return graphical_edge

class QNodeProxy(QtWidgets.QGraphicsProxyWidget, event.Emitter):
    def __init__(self, widget, id):
        QtWidgets.QGraphicsProxyWidget.__init__(self)
        event.Emitter.__init__(self)
        self.setWidget(widget)
        self.id = id
        self._dx = 0
        self._dy = 0
    
    def __repr__(self):
        return "{0}({1})".format(type(self).__name__, repr(self.widget()))
    
    def delete(self):
        model.object_delete(self.widget().id)

    def _connect(self, newedge, source_proxy, dest_proxy):
        source_widget = source_proxy.widget()
        dest_widget = dest_proxy.widget()
        try:
            model.edge_new(newedge.id, source_widget.id, dest_widget.id)
        except model.RelationException as exception:
            QMessageBox.critical(None, "Error", exception.args[0])

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
            for view in self.scene().views():
                view.set_selected_item(self)
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
        pass

    def object_changed(self, object_id):
        self.widget().object_changed(object_id)

class QNodeWidget(QtWidgets.QFrame, event.Emitter):
    def __init__(self, object_id):
        QtWidgets.QFrame.__init__(self)
        #self.setMaximumWidth(300)
        self.setFrameShape(QtWidgets.QFrame.Box)
        self.setFrameShadow(QtWidgets.QFrame.Plain)
        self.setAutoFillBackground(True)
        self._layout = QtWidgets.QVBoxLayout(self)

        self._pixmap = QtGui.QPixmap("./pic.jpg")
        self._image = QtWidgets.QLabel()
        #policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        #self._image.setSizePolicy(policy)
        self._image.setPixmap(self._pixmap)
        self._image.setScaledContents(True)
        #self._image.setMaximumHeight(200)
        self._image.setMaximumWidth(300)
        self._image.setMaximumHeight(200)
        self._layout.addWidget(self._image)

        self.id = object_id
        self._text = QtWidgets.QLabel()
        # label.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)
        font = self._text.font()
        font.setPointSize(20)
        self._text.setFont(font)
        self._text.setWordWrap(True)
        self._layout.addWidget(self._text)
        self.object_changed(object_id)
    
    def __repr__(self):
        return "{0}({1})".format(type(self).__name__, repr(self.id))

    def object_changed(self, object_id):
        # Set background color
        palette = self.palette()
        color = model.object_get_color(object_id)
        bgcolor = QtGui.QColor(color.r, color.g, color.b)
        palette.setColor(self.backgroundRole(), bgcolor)
        self.setPalette(palette)

        # Set label
        object_name = model.object_get_name(object_id)
        self._text.setText(object_name)

        self.emit("object_changed", object_id)

def midpoint(qgraphicsitem):
    r = qgraphicsitem.boundingRect()
    x = r.width() / 2
    y = r.height() / 2
    p = QtCore.QPointF(x, y)
    return p

class QNodeView(QtWidgets.QGraphicsView):
    def __init__(self, scene, edit):
        super().__init__(scene)
        self._edit = edit
        scene.setSceneRect(0, 0, self.width(), self.height())
        self.setAcceptDrops(True)
        brush = QtGui.QBrush(QtGui.QColor(64, 64, 64))
        self.setBackgroundBrush(brush)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self._selected_item = no_selected_item

    def get_selected_item(self):
        return self._selected_item

    def set_selected_item(self, item):
        if self._selected_item and self._selected_item is not item:
            self._selected_item.unselect()
        self._selected_item = item
        if item:
            item.select()
        self._edit(item)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()
        class_id = int(event.mimeData().text())
        object = make_object(class_id)
        self.scene().addItem(object)
        self.set_selected_item(object)

        # Position the object so the cursor lies over its center
        position = self.mapToScene(event.pos())
        mid_position = position - midpoint(object)
        object.setPos(mid_position)

        # Allow the user to delete the node immediately after adding by pressing backspace
        self.setFocus()

    def keyPressEvent(self, event):
        selected_item = self.get_selected_item()
        key = event.key()
        if key == QtCore.Qt.Key_Space:
            rect = self.scene().itemsBoundingRect()
            self.scene().setSceneRect(rect)
        elif selected_item and key in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            self.set_selected_item(no_selected_item)
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
        selected_item = self.get_selected_item()
        if not self.itemAt(event.pos()) and selected_item:
            self.set_selected_item(no_selected_item)

def make_graphical_object(object_id):
    qnode = QNodeWidget(object_id)
    proxy = QNodeProxy(qnode, object_id)
    qnodes[object_id] = proxy
    qnode.add_listener("object_changed", proxy._object_changed)
    return proxy

def make_object(class_id):
    object_id = model.object_new(class_id, source="view")
    graphical_object = make_graphical_object(object_id)
    object_is_visible = model.object_is_visible(object_id)
    graphical_object.setVisible(object_is_visible)
    return graphical_object

def get_object(object_id):
    return qnodes[object_id]

def get_edge(edge_id):
    return qedges[edge_id]

class QNodeSceneDelegate(model.Delegate):
    def __init__(self, scene):
        model.Delegate.__init__(self)
        self.scene = scene
    
    def object_created(self, object_id, source):
        if source == "model":
            # TODO: Position in a suitable place
            graphical_object = make_graphical_object(object_id)
            model_object = model.get_object(object_id)
            graphical_object.setVisible(model_object.is_visible())
            self.scene.addItem(graphical_object)

    def object_deleted(self, object_id, source):
        object = get_object(object_id)
        self.scene.removeItem(object)
    
    def object_changed(self, object_id, source):
        graphical_object = get_object(object_id)
        graphical_object.object_changed(object_id)
        is_visible = model.object_is_visible(object_id)
        graphical_object.setVisible(is_visible)

    def edge_created(self, edge_id, source):
        if source == "model":
            graphical_edge = make_edge(edge_id)
            self.scene.addItem(graphical_edge)
    
    def edge_changed(self, edge_id, source):
        graphical_edge = get_edge(edge_id)
        is_visible = model.edge_is_visible(edge_id)
        graphical_edge.setVisible(is_visible)
        color = model.edge_get_color(edge_id)
        graphical_edge.set_color(color)

    def edge_deleted(self, edge_id, source):
        edge = get_edge(edge_id)
        self.scene.removeItem(edge)

class QNodeScene(QtWidgets.QGraphicsScene):
    def __init__(self):
        super().__init__()
        model.add_delegate(QNodeSceneDelegate(self))

class QClassListDelegate(model.Delegate):
    def __init__(self, class_list):
        model.Delegate.__init__(self)
        self.class_list = class_list
    
    def class_created(self, class_id, source):
        class_name = model.class_get_name(class_id)
        class_is_visible = model.class_is_visible(class_id)
        item = QtWidgets.QListWidgetItem(class_name)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, class_id)
        item.setCheckState(QtCore.Qt.Checked if class_is_visible else QtCore.Qt.Unchecked)
        self.class_list.addItem(item)
        self.class_list.setCurrentItem(item)
    
    def class_deleted(self, class_id, source):
        row = self.class_list._id_to_row(class_id)
        self.class_list.takeItem(row)

    def class_changed(self, class_id, source):
        item = self.class_list._id_to_item(class_id)
        class_name = model.class_get_name(class_id)
        item.setText(class_name)

class QClassList(QtWidgets.QListWidget):
    def __init__(self, edit):
        QtWidgets.QListWidget.__init__(self)
        self.delegate = QClassListDelegate(self)
        model.add_delegate(self.delegate)
        for class_id in model.get_classes():
            self.delegate.class_created(class_id, "view")
        self.clicked.connect(self._clicked)
        self._edit = edit
        self.setDragEnabled(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
    
    def _clicked(self, index):
        item = self.item(index.row())
        class_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        class_is_visible = model.class_is_visible(class_id)
        is_checked = item.checkState() == QtCore.Qt.Checked
        if class_is_visible != is_checked:
            model.class_set_visible(class_id, is_checked)
        self._edit(class_id)
    
    def _id_to_item(self, member_id):
        item = list(filter(
            lambda item: item.data(QtCore.Qt.ItemDataRole.UserRole) == member_id,
            [self.item(row) for row in range(self.count())]
        ))[0]
        return item
    
    def _id_to_row(self, member_id):
        row = list(filter(
            lambda row: self.item(row).data(QtCore.Qt.ItemDataRole.UserRole) == member_id,
            range(self.count())
        ))[0]
        return row

    def closeEvent(self, event):
        model.remove_delegate(self.delegate)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        mime_data = QtCore.QMimeData()
        class_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        mime_data.setText(str(class_id))
        drag = QtGui.QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec()

class QRelationListDelegate(model.Delegate):
    def __init__(self, relation_list):
        model.Delegate.__init__(self)
        self.relation_list = relation_list
    
    def relation_created(self, relation_id, source):
        relation_name = model.relation_get_name(relation_id)
        relation_is_visible = model.relation_is_visible(relation_id)
        item = QtWidgets.QListWidgetItem(relation_name)
        item.setData(QtCore.Qt.ItemDataRole.UserRole, relation_id)
        item.setCheckState(QtCore.Qt.Checked if relation_is_visible else QtCore.Qt.Unchecked)
        self.relation_list.addItem(item)
        self.relation_list.setCurrentItem(item)
        set_active_relation(relation_id)
    
    def relation_deleted(self, relation_id, source):
        row = self.relation_list._id_to_row(relation_id)
        self.relation_list.takeItem(row)

    def relation_changed(self, relation_id, source):
        item = self.relation_list._id_to_item(relation_id)
        relation_name = model.relation_get_name(relation_id)
        item.setText(relation_name)

class QRelationList(QtWidgets.QListWidget):
    def __init__(self, edit):
        super().__init__()
        self.delegate = QRelationListDelegate(self)
        model.add_delegate(self.delegate)
        for relation_id in model.get_relations():
            self.delegate.relation_created(relation_id, "view")
        self.clicked.connect(self._clicked)
        self._edit = edit

    def _clicked(self, index):
        item = self.item(index.row())
        relation_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        relation_is_visible = model.relation_is_visible(relation_id)
        is_checked = item.checkState() == QtCore.Qt.Checked
        if relation_is_visible != is_checked:
            model.relation_set_visible(is_checked)
        set_active_relation(relation_id)
        self._edit(relation_id)
    
    def _id_to_item(self, member_id):
        item = list(filter(
            lambda item: item.data(QtCore.Qt.ItemDataRole.UserRole) == member_id,
            [self.item(row) for row in range(self.count())]
        ))[0]
        return item
    
    def _id_to_row(self, member_id):
        row = list(filter(
            lambda row: self.item(row).data(QtCore.Qt.ItemDataRole.UserRole) == member_id,
            range(self.count())
        ))[0]
        return row

    def closeEvent(self, event):
        model.remove_delegate(self.delegate)

class QCollectionPalette(QtWidgets.QWidget):
    def __init__(self, list_widget):
        QtWidgets.QWidget.__init__(self)
        self._list: QListWidget = list_widget

        button_layout = QHBoxLayout()

        add_button = QPushButton("+")
        add_button.clicked.connect(self._on_add)
        button_layout.addWidget(add_button)

        del_button = QPushButton("-")
        del_button.clicked.connect(self._on_del)
        button_layout.addWidget(del_button)
        
        button_panel = QtWidgets.QWidget()
        button_panel.setLayout(button_layout)

        palette_layout = QtWidgets.QVBoxLayout()
        palette_layout.addWidget(button_panel)
        palette_layout.addWidget(list_widget)
        self.setLayout(palette_layout)
    
    def _on_add(self):
        self.on_add()

    def _on_del(self):
        self.on_delete(self._list.currentItem())
    
    def on_add(self, item):
        pass

    def on_delete(self, item):
        pass

class QClassPalette(QCollectionPalette):
    def __init__(self, edit):
        QCollectionPalette.__init__(self, QClassList(edit))
    
    def on_add(self):
        class_id = model.class_new("Class {0}".format(self._list.count()))
    
    def on_delete(self, item):
        class_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        model.class_delete(class_id)

class QRelationPalette(QCollectionPalette):
    def __init__(self, edit):
        QCollectionPalette.__init__(self, QRelationList(edit))
    
    def on_add(self):
        relation_id = model.relation_new("relation {0}".format(self._list.count()))
    
    def on_delete(self, item):
        relation_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
        model.relation_delete(relation_id)

def make_log_dock():
    fixed_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
    textbox = QTextEdit()
    textbox.setFont(fixed_font)
    textbox.setReadOnly(True)
    log.set_logger(QLogger(textbox))
    dock = QtWidgets.QDockWidget("Log Messages")
    dock.setWidget(textbox)
    return dock

def make_class_dock(editor):
    dock = QtWidgets.QDockWidget("Classes")
    def edit(class_id):
        class_editor = QClassEditor(class_id)
        editor.setWidget(class_editor)
    dock.setWidget(QClassPalette(edit))
    return dock

def make_relation_dock(editor):
    dock = QtWidgets.QDockWidget("Relations")
    edit = lambda relation: editor.setWidget(QRelationEditor(relation))
    dock.setWidget(QRelationPalette(edit))
    return dock

def make_object_dock(object_filter_id):
    filter_name = model.object_filter_get_name(object_filter_id)
    dock = QCollectionFilterDock(filter_name)
    dock.id = object_filter_id
    list = QObjectFilter(object_filter_id)
    dock.setWidget(list)
    return dock

def make_tag_dock():
    model = QTagModel()
    view = QTagView(model)
    dock = QtWidgets.QDockWidget("Tags")
    dock.setWidget(view)
    return dock

class QMainWindowDelegate(model.Delegate):
    def __init__(self, window):
        self.window = window
    
    def object_filter_created(self, id, source):
        self.window.add_object_filter(id)
    
    def object_filter_deleted(self, id, source):
        self.window.remove_object_filter(id)

class QMainWindow(QtWidgets.QMainWindow):
    def __init__(self, title):
        super().__init__()

        # set size to 70% of screen
        #self.resize(QtWidgets.QDesktopWidget().availableGeometry(self).size() * 0.7)
        self.setWindowTitle(title)
        scene = QNodeScene()
        def edit_entity(graphical_object):
            if graphical_object == no_selected_item:
                editor.setWidget(QtWidgets.QFrame())
            elif type(graphical_object) == QNodeProxy:
                object_id = graphical_object.id
                editor.setWidget(QObjectEditor(object_id))
        view = QNodeView(scene, edit_entity)
        self.setCentralWidget(view)

        # self.addDockWidget(QtCore.Qt.RightDockWidgetArea, make_tag_dock())
        editor = QtWidgets.QDockWidget("Editor")
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, editor)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, make_class_dock(editor))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, make_relation_dock(editor))
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, make_log_dock())

        self._toolbar = self.addToolBar("Task")
        self.add_button("&New Object", QtWidgets.QStyle.SP_FileIcon, self._on_button_click)

        model.add_delegate(QMainWindowDelegate(self))
        self._object_filters = {}
        self._last_object_filter = 0

        model.class_new("Tag")
        goal_class = model.class_new("Goal")
        model.class_new("Task")
        model.relation_new("precedes")
        model.relation_new(
            "is a child of",
            directed=True,
            acyclic=True,
            max_outnodes=1
        )
        model.object_filter_new("Test Filter", lambda object_id: True)
        model.class_add_field(goal_class, "Foo", model.Integer, 13)
        model.class_add_field(goal_class, "Bar", model.Bool, True)
        model.class_add_field(goal_class, "Baz", model.String, "Quux")
        model.class_add_field(goal_class, "Flufu", model.Float, 3.14)

    def add_button(self, text, icontype, callback):
        icon = self.style().standardIcon(icontype)
        action = QtWidgets.QAction(icon, text, self)
        action.triggered.connect(callback)
        action.setIconVisibleInMenu(True)
        self._toolbar.addAction(action)

    def add_object_filter(self, id):
        dock = make_object_dock(id)
        if not self._object_filters:
            self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
        else:
            last_id = max(map(lambda qfilter: qfilter.id, self._object_filters.values()))
            last_dock = self._object_filters[last_id]
            self.tabifyDockWidget(last_dock, dock)
        self._object_filters[id] = dock
    
    def remove_object_filter(self, id):
        dock = self._object_filters[id]
        dock.close()
        del self._object_filters[id]
    
    def _on_button_click(self, *args):
        model.object_filter_new(
            "Actionable {0}".format(len(self._object_filters)+1),
            lang.eval(lang.read("""
                (let ((relation-id
                        (find-first (lambda (relation-id)
                          (= (relation-name relation-id) "precedes")) (all-relations))))
                  (lambda (object-id)
                    (zero? (length (innodes object-id relation-id)))))
            """))
        )

class QColorWidget(QtWidgets.QPushButton):
    colorChanged = QtCore.pyqtSignal(QtGui.QColor)
    def __init__(self, color):
        QtWidgets.QPushButton.__init__(self)
        self._set_color(color)
        self.clicked.connect(self._on_click)
    
    def _set_color(self, color):
        palette = self.palette()
        palette.setColor(self.backgroundRole(), color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        self.setFlat(True)
        self.colorChanged.emit(color)
    
    def _on_click(self):
        color = QColorDialog.getColor()
        self._set_color(color)

class QLogger(object):
    def __init__(self, textbox: QTextEdit):
        self.textbox: QTextEdit = textbox
    
    def _write(self, message):
        self.textbox.append(message)
        scrollbar = self.textbox.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def info(self, message):
        self._write("INFO: {0}".format(message))
    
    def warn(self, message):
        self._write("WARN: {0}".format(message))
    
    def error(self, message):
        self._write("ERROR: {0}".format(message))

class QRelationEditor(QtWidgets.QFrame):
    def __init__(self, relation_id):
        QtWidgets.QFrame.__init__(self)
        self._layout = QtWidgets.QFormLayout()
        self._relation_id = relation_id

        relation_name = model.relation_get_name(relation_id)
        self._name = QtWidgets.QLineEdit(relation_name)
        self._name.textChanged.connect(self._on_name_changed)
        self._layout.addRow("&Name", self._name)

        relation_color = model.relation_get_color(relation_id)
        self._color = QColorWidget(QtGui.QColor(relation_color.r, relation_color.g, relation_color.b))
        self._color.colorChanged.connect(self._on_color_changed)
        self._layout.addRow("&Color", self._color)

        relation_is_directed = model.relation_is_directed(relation_id)
        self._directed = QtWidgets.QCheckBox()
        self._directed.setCheckState(relation_is_directed)
        self._directed.stateChanged.connect(self._on_directed_changed)
        self._layout.addRow("&Directed", self._directed)

        relation_is_acyclic = model.relation_is_acyclic(relation_id)
        self._acyclic = QtWidgets.QCheckBox()
        self._acyclic.setCheckState(relation_is_acyclic)
        self._acyclic.stateChanged.connect(self._on_acyclic_changed)
        self._layout.addRow("&Acyclic", self._acyclic)

        relation_is_reverse = model.relation_is_reverse(relation_id)
        self._reverse = QtWidgets.QCheckBox()
        self._reverse.setCheckState(relation_is_reverse)
        self._reverse.stateChanged.connect(self._on_reverse_changed)
        self._layout.addRow("&Reverse", self._reverse)

        relation_max_innodes = model.relation_get_max_innodes(relation_id)
        self._max_innodes = QtWidgets.QSpinBox()
        self._max_innodes.setMinimum(-1)
        self._max_innodes.setSingleStep(1)
        self._max_innodes.setSpecialValueText("No Limit")
        self._max_innodes.setValue(relation_max_innodes)
        self._layout.addRow("Max In-Nodes", self._max_innodes)
        # TODO: Add handler to check if the proposed value is valid before changing

        relation_max_outnodes = model.relation_get_max_outnodes(relation_id)
        self._max_outnodes = QtWidgets.QSpinBox()
        self._max_outnodes.setMinimum(-1)
        self._max_outnodes.setSingleStep(1)
        self._max_outnodes.setSpecialValueText("No Limit")
        self._max_outnodes.setValue(relation_max_outnodes)
        self._layout.addRow("Max Out-Nodes", self._max_outnodes)
        # TODO: Add handler to check if the proposed value is valid before changing

        fixed_font = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        relation_on_add_handler = model.relation_get_on_add_handler(relation_id)
        self._on_add = QtWidgets.QTextEdit()
        self._on_add.setFont(fixed_font)
        self._on_add.setText(relation_on_add_handler)
        self._on_add.textChanged.connect(self._on_add_changed)
        self._layout.addRow("On Add", self._on_add)

        relation_on_delete_handler = model.relation_get_on_delete_handler(relation_id)
        self._on_delete = QtWidgets.QTextEdit()
        self._on_delete.setFont(fixed_font)
        self._on_delete.setText(relation_on_delete_handler)
        self._on_delete.textChanged.connect(self._on_delete_changed)
        self._layout.addRow("On Delete", self._on_delete)

        self.setLayout(self._layout)
    
    def _on_name_changed(self):
        model.relation_set_name(self._relation_id, self._name.text())
    
    def _on_color_changed(self, color: QtGui.QColor):
        new_color = model.Color(color.red(), color.green(), color.blue())
        model.relation_set_color(self._relation_id, new_color)

    def _on_directed_changed(self, state):
        model.relation_set_directed(self._relation_id, bool(state))

    def _on_acyclic_changed(self, state):
        model.relation_set_acyclic(self._relation_id, bool(state))

    def _on_reverse_changed(self, state):
        model.relation_set_reverse(self._relation_id, bool(state))
    
    def _on_add_changed(self):
        model.relation_set_on_add_handler(self._relation_id, self._on_add.toPlainText())
    
    def _on_delete_changed(self):
        model.relation_set_on_delete_handler(self._relation_id, self._on_delete.toPlainText())

def make_field_initial_value_input(field_id):
    field_type = model.field_get_type(field_id)
    field_value = model.field_get_initial_value(field_id)

    if field_type == model.Integer:
        input = QtWidgets.QSpinBox()
        input.setSingleStep(1)
        INT_MIN = -(2**31)
        INT_MAX = (2**31) - 1
        input.setRange(INT_MIN, INT_MAX)
        input.setValue(field_value)
        def handler(value):
            model.field_set_initial_value(field_id, value)
        input.valueChanged.connect(handler)
    elif field_type == model.Float:
        input = QtWidgets.QLineEdit(str(field_value))
        restrict_to_floats = QtGui.QDoubleValidator()
        input.setValidator(restrict_to_floats)
        def handler(value):
            try:
                new_value = float(input.text())
                model.field_set_initial_value(field_id, new_value)
            except:
                pass
        input.textChanged.connect(handler)
    elif field_type == model.Bool:
        input = QtWidgets.QCheckBox()
        input.setCheckState(field_value)
        def handler(value):
            model.field_set_initial_value(field_id, bool(value))
        input.stateChanged.connect(handler)
    elif field_type == model.String:
        input = QtWidgets.QLineEdit(field_value)
        def handler(value):
            model.field_set_initial_value(field_id, input.text())
        input.textChanged.connect(handler)
    else:
        assert False, "Field type {0} is not accounted for.".format(field_type)

    return input

class QClassField(QtWidgets.QFrame):
    deleted = QtCore.pyqtSignal(QtWidgets.QFrame)

    def __init__(self, field_id):
        QtWidgets.QFrame.__init__(self)
        self._field_id = field_id
        field_layout = QtWidgets.QHBoxLayout()

        # Delete button
        delete_btn = QtWidgets.QPushButton("X")
        def delete_field():
            self.deleted.emit(self)
        delete_btn.clicked.connect(delete_field)
        field_layout.addWidget(delete_btn)

        info = QtWidgets.QFrame()
        info_layout = QtWidgets.QFormLayout()

        # Field name
        field_name = model.field_get_name(field_id)
        field_name_input = QtWidgets.QLineEdit(field_name)
        def set_field_name():
            model.field_set_name(field_id, field_name_input.text())
        field_name_input.textChanged.connect(set_field_name)
        info_layout.addRow("Name", field_name_input)

        # Field type
        field_type = model.field_get_type(field_id)
        field_type_input: QtWidgets.QComboBox = QtWidgets.QComboBox()
        valid_types = [model.Integer, model.Float, model.Bool, model.String]
        for type in valid_types:
            field_type_input.addItem(type.__name__, type)
        field_type_input.setCurrentIndex(valid_types.index(field_type))
        def set_field_type(field_type_index):
            model.field_set_type(field_id, valid_types[field_type_index])
            info_layout.removeRow(self._initial_value_input)
            self._initial_value_input = make_field_initial_value_input(field_id)
            info_layout.addRow("Initial Value", self._initial_value_input)
        field_type_input.currentIndexChanged.connect(set_field_type)
        info_layout.addRow("Type", field_type_input)

        self._initial_value_input = make_field_initial_value_input(field_id)
        info_layout.addRow("Initial Value", self._initial_value_input)

        info.setLayout(info_layout)
        field_layout.addWidget(info)
        self.setLayout(field_layout)

class QClassEditor(QtWidgets.QFrame):
    def __init__(self, class_id):
        QtWidgets.QFrame.__init__(self)
        self._class_id = class_id
        editor_layout = QtWidgets.QVBoxLayout()
        editor_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        common_fields = QtWidgets.QFrame()
        common_fields_layout = QtWidgets.QFormLayout()

        class_name = model.class_get_name(class_id)
        self._name = QtWidgets.QLineEdit(class_name)
        self._name.textChanged.connect(self._on_name_changed)
        common_fields_layout.addRow("&Name", self._name)

        class_color = model.class_get_color(class_id)
        self._color = QColorWidget(QtGui.QColor(class_color.r, class_color.g, class_color.b))
        self._color.colorChanged.connect(self._on_color_changed)
        common_fields_layout.addRow("&Color", self._color)

        common_fields.setLayout(common_fields_layout)
        editor_layout.addWidget(common_fields)
        
        def add_field(field_id):
            field = QClassField(field_id)
            def delete_field(widget):
                editor_layout.removeWidget(widget)
                widget.setHidden(True)
                # self.setLayout(editor_layout)
                model.field_delete(field_id)
            field.deleted.connect(delete_field)
            editor_layout.addWidget(field)
        
        def new_field():
            field_id = model.class_add_field(class_id, "New Field", model.Integer)
            add_field(field_id)

        add_field_button = QtWidgets.QPushButton("Add Field")
        add_field_button.clicked.connect(new_field)
        editor_layout.addWidget(add_field_button)

        for field_id in model.class_get_fields(class_id):
            add_field(field_id)
        self.setLayout(editor_layout)
    
    def _on_name_changed(self):
        model.class_set_name(self._class_id, self._name.text())
    
    def _on_color_changed(self, color: QtGui.QColor):
        new_color = model.Color(color.red(), color.green(), color.blue())
        model.class_set_color(self._class_id, new_color)

class QObjectEditor(QtWidgets.QFrame):
    def __init__(self, object_id):
        QtWidgets.QFrame.__init__(self)
        self._layout = QtWidgets.QFormLayout()
        self._object_id = object_id

        object_name = model.object_get_name(object_id)
        self._name = QtWidgets.QLineEdit(object_name)
        self._name.textChanged.connect(self._on_name_changed)
        self._layout.addRow("&Name", self._name)

        # We need this function to capture the value (not the reference)
        # of member_id in the loop below. Otherwise, all of the fields will
        # modify the same member.
        def make_int_changed_handler(member_id):
            def handler(value):
                model.member_set_value(member_id, value)
            return handler
        
        def make_bool_changed_handler(member_id):
            def handler(value):
                model.member_set_value(member_id, bool(value))
            return handler
        
        def make_str_changed_handler(member_id, input):
            def handler(value):
                model.member_set_value(member_id, input.text())
            return handler
        
        def make_float_changed_handler(member_id, input):
            def handler(value):
                try:
                    new_value = float(input.text())
                    model.member_set_value(member_id, new_value)
                except:
                    pass
            return handler

        member_ids = model.object_get_members(object_id)
        for member_id in member_ids:
            field_id = model.member_get_field(member_id)
            field_name = model.field_get_name(field_id)
            field_type = model.field_get_type(field_id)
            member_value = model.member_get_value(member_id)
            if field_type == model.Integer:
                input = QtWidgets.QSpinBox()
                input.setSingleStep(1)
                INT_MIN = -(2**31)
                INT_MAX = (2**31) - 1
                input.setRange(INT_MIN, INT_MAX)
                input.setValue(member_value)
                input.valueChanged.connect(make_int_changed_handler(member_id))
            elif field_type == model.Float:
                input = QtWidgets.QLineEdit(str(member_value))
                restrict_to_floats = QtGui.QDoubleValidator()
                input.setValidator(restrict_to_floats)
                input.textChanged.connect(make_float_changed_handler(member_id, input))
            elif field_type == model.Bool:
                input = QtWidgets.QCheckBox()
                input.setCheckState(member_value)
                input.stateChanged.connect(make_bool_changed_handler(member_id))
            elif field_type == model.String:
                input = QtWidgets.QLineEdit(member_value)
                input.textChanged.connect(make_str_changed_handler(member_id, input))
            self._layout.addRow(field_name, input)

        self.setLayout(self._layout)
    
    def _on_name_changed(self):
        model.object_set_name(self._object_id, self._name.text())

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
        self._root = make_tree("A",
            make_tree("B"),
            make_tree("C"),
            make_tree("D",
                make_tree("E"),
                make_tree("F")
            ),
            make_tree("G",
                make_tree("H")
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
