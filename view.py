# graph.py -- A network layout program.
import math
import lang
import log
import model
import event
from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
from PyQt5.QtWidgets import QColorDialog, QHBoxLayout, QListWidget, QMessageBox, QPushButton, QTextEdit, QTreeView, QWidget

zvalue_max = 0.0
zvalue_increment = 1.0
newedge = None

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
        model.disconnect(self.id, self._edge_id)

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

        set_selected_item(self)

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
                model.delete_object_filter(self.id)
            timer.timeout.connect(delete)
            timer.start(0)

class QCollectionFilter(QtWidgets.QTableWidget):
    def __init__(self, collection, object_filter_id):
        #super().__init__(0, 2)
        super().__init__()
        self.id = object_filter_id
        filter = model.get_object_filter(object_filter_id)
        self._predicate = filter.predicate
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
        if self._predicate(object_id):
            # Add the object to the widget
            self._matches_list.append(object_id)
            self._matches.add(object_id)
            nrows = len(self._matches_list)
            row = nrows - 1
            self.setRowCount(nrows)
            self.member_added(object, row)

    def member_added(self, member, row):
        pass

    def member_changed(self, member, row):
        pass

    def _object_deleted(self, object_id, source):
        if object_id in self._matches:
            # Remove the object from the widget
            row = self._matches_list.index(object_id)
            self.removeRow(row)
            self._matches_list.remove(object_id)
            self._matches.remove(object_id)

    def _object_changed(self, object_id):
        object = self._collection.get_member(object_id)
        if self._predicate(object_id):
            if object_id in self._matches:
                row = self._matches_list.index(object_id)
                self.member_changed(object, row)
            else:
                self._object_created(object_id, "view")
        else:
            self._object_deleted(object_id, "view")

class QObjectFilter(QCollectionFilter):
    def __init__(self, collection, object_filter_id):
        super().__init__(collection, object_filter_id)
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

    def member_changed(self, member, row):
        # When cellChanged is connected to to self._cellChanged, calls to self.setItem()
        # call the target object's set_field() method, which in turn calls its object_changed
        # event handler, which would then result in this callback being invoked repeatedly.
        # We temporarily disconnect the handler to prevent this behavior.
        self.cellChanged.disconnect(self._cellChanged)
        self.member_added(member, row)
        self.cellChanged.connect(self._cellChanged)

    def _cellChanged(self, row, col):
        object_id = self._matches_list[row]
        object = model.get_object(object_id)
        item = self.item(row, col)
        object.set_field("Title", item.text())

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
    def __init__(self, widget):
        QtWidgets.QGraphicsProxyWidget.__init__(self)
        event.Emitter.__init__(self)
        self.setWidget(widget)
        self._dx = 0
        self._dy = 0
    
    def __repr__(self):
        return "{0}({1})".format(type(self).__name__, repr(self.widget()))
    
    def delete(self):
        model.delete_object(self.widget().id)

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
    def __init__(self, scene):
        super().__init__(scene)
        scene.setSceneRect(0, 0, self.width(), self.height())
        self.setAcceptDrops(True)
        brush = QtGui.QBrush(QtGui.QColor(64, 64, 64))
        self.setBackgroundBrush(brush)
        self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        event.acceptProposedAction()
        class_id = int(event.mimeData().text())
        class_name = model.class_get_name(class_id)
        object = make_object(class_id, "New {0}".format(class_name))
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
    qnode.add_listener("object_changed", proxy._object_changed)
    return proxy

def make_object(class_id, *args):
    object_id = model.object_new(class_id, *args, source="view")
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

    # def member_added(self, relation):
    #     set_active_relation(relation.id)
    
    # def member_removed(self):
    #     remaining_members = self.members()
    #     active_relation = remaining_members[0] if remaining_members else no_active_relation
    #     set_active_relation(active_relation)

    # def member_clicked(self, member, is_checked):
    #     set_active_relation(member.id)
    #     if member.is_visible() != is_checked:
    #         member.set_visible(is_checked)
    #     self._edit(member)

# class QCollectionPalette(QtWidgets.QWidget):
#     def __init__(self, list_widget):
#         QtWidgets.QWidget.__init__(self)
#         self._list: QListWidget = list_widget

#         button_layout = QHBoxLayout()

#         add_button = QPushButton("+")
#         add_button.clicked.connect(self._on_add)
#         button_layout.addWidget(add_button)

#         del_button = QPushButton("-")
#         del_button.clicked.connect(self._on_del)
#         button_layout.addWidget(del_button)
        
#         button_panel = QtWidgets.QWidget()
#         button_panel.setLayout(button_layout)

#         palette_layout = QtWidgets.QVBoxLayout()
#         palette_layout.addWidget(button_panel)
#         palette_layout.addWidget(list_widget)
#         self.setLayout(palette_layout)
    
#     def _on_add(self):
#         self.on_add()

#     def _on_del(self):
#         self.on_delete(self._list.currentItem())
    
#     def on_add(self, item):
#         pass

#     def on_delete(self, item):
#         pass

# class QClassPalette(QCollectionPalette):
#     def __init__(self, edit):
#         QCollectionPalette.__init__(self, QClassList(edit))
    
#     def on_add(self):
#         class_id = model.make_class("Class {0}".format(self._list.count()))
    
#     def on_delete(self, item):
#         class_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
#         model.class_delete(class_id)

# class QRelationPalette(QCollectionPalette):
#     def __init__(self, relations, edit):
#         QCollectionPalette.__init__(self, QRelationList(relations, edit))
    
#     def on_add(self):
#         relation_id = model.relation_new("relation {0}".format(self._list.count()))
    
#     def on_delete(self, item):
#         relation_id = item.data(QtCore.Qt.ItemDataRole.UserRole)
#         model.relation_delete(relation_id)

def make_log_dock():
    textbox = QTextEdit()
    textbox.setReadOnly(True)
    log.set_logger(QLogger(textbox))
    dock = QtWidgets.QDockWidget("Log Messages")
    dock.setWidget(textbox)
    return dock

def make_class_dock(editor):
    dock = QtWidgets.QDockWidget("Classes")
    #edit = lambda class_id: editor.setWidget(QClassEditor(class_id))
    def edit(class_id):
        class_editor = QClassEditor(class_id)
        editor.setWidget(class_editor)
    #edit = None
    dock.setWidget(QClassList(edit))
    return dock

def make_relation_dock(editor):
    dock = QtWidgets.QDockWidget("Relations")
    edit = lambda relation: editor.setWidget(QRelationEditor(relation))
    dock.setWidget(QRelationList(edit))
    return dock

def make_object_dock(object_filter_id):
    filter_name = model.object_filter_get_name(object_filter_id)
    dock = QCollectionFilterDock(filter_name)
    dock.id = object_filter_id
    list = QObjectFilter(model.objects, object_filter_id)
    dock.setWidget(list)
    return dock

def make_tag_dock():
    model = QTagModel()
    view = QTagView(model)
    dock = QtWidgets.QDockWidget("Tags")
    dock.setWidget(view)
    return dock

class ObjectFilterDelegate(model.Delegate):
    def __init__(self, window):
        self.window = window
    
    def on_member_added(self, id):
        self.window.add_object_filter(id)
    
    def on_member_removed(self, id):
        self.window.remove_object_filter(id)

class QMainWindow(QtWidgets.QMainWindow):
    def __init__(self, title):
        super().__init__()

        # set size to 70% of screen
        #self.resize(QtWidgets.QDesktopWidget().availableGeometry(self).size() * 0.7)
        self.setWindowTitle(title)
        scene = QNodeScene()
        view = QNodeView(scene)
        self.setCentralWidget(view)

        # self.addDockWidget(QtCore.Qt.RightDockWidgetArea, make_tag_dock())
        editor = QtWidgets.QDockWidget("Editor")
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, editor)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, make_class_dock(editor))
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, make_relation_dock(editor))
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, make_log_dock())

        self._toolbar = self.addToolBar("Task")
        self.add_button("&New Object", QtWidgets.QStyle.SP_FileIcon, self._on_button_click)

        # model.object_filters.add_delegate(ObjectFilterDelegate(self))
        # self._object_filters = {}
        # self._last_object_filter = 0

        model.class_new("Tag")
        model.class_new("Goal")
        model.class_new("Task")
        model.relation_new("precedes")
        model.relation_new(
            "is a child of",
            directed=True,
            acyclic=True,
            max_outnodes=1
        )

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
        model.make_object_filter(
            "Actionable {0}".format(len(self._object_filters)+1),
            lang.eval(lang.read("""
                (let ((relation-id
                        (find-first (lambda (relation-id)
                          (= (relation-name relation-id) "has vocation")) (all-relations))))
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

        relation_on_add_handler = model.relation_get_on_add_handler(relation_id)
        self._on_add = QtWidgets.QTextEdit()
        self._on_add.setText(relation_on_add_handler)
        self._on_add.textChanged.connect(self._on_add_changed)
        self._layout.addRow("On Add", self._on_add)

        relation_on_delete_handler = model.relation_get_on_delete_handler(relation_id)
        self._on_delete = QtWidgets.QTextEdit()
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

class QClassEditor(QtWidgets.QFrame):
    def __init__(self, class_id):
        QtWidgets.QFrame.__init__(self)
        self._layout = QtWidgets.QFormLayout()
        self._class_id = class_id

        class_name = model.class_get_name(class_id)
        self._name = QtWidgets.QLineEdit(class_name)
        self._name.textChanged.connect(self._on_name_changed)
        self._layout.addRow("&Name", self._name)

        class_color = model.class_get_color(class_id)
        self._color = QColorWidget(QtGui.QColor(class_color.r, class_color.g, class_color.b))
        self._color.colorChanged.connect(self._on_color_changed)
        self._layout.addRow("&Color", self._color)

        self.setLayout(self._layout)
    
    def _on_name_changed(self):
        model.class_set_name(self._class_id, self._name.text())
    
    def _on_color_changed(self, color: QtGui.QColor):
        new_color = model.Color(color.red(), color.green(), color.blue())
        model.class_set_color(self._class_id, new_color)

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
