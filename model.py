import event
import random

_id = 0
def make_id():
    global _id
    _id += 1
    return _id

class VisibilitySuppressor(object):
    def __init__(self, suppressors=set()):
        self._suppressors = set(suppressors)
    
    def set_visible(self, is_visible, symbol):
        fn = self._suppressors.discard if is_visible else self._suppressors.add
        old_size = len(self._suppressors)
        fn(symbol)
        new_size = len(self._suppressors)
        if (old_size == 0 and new_size == 1) or (old_size == 1 and new_size == 0):
            self.visibility_changed()
    
    def visibility_changed(self):
        pass

    def is_visible(self):
        return not bool(self._suppressors)
    
    def suppressors(self):
        return set(self._suppressors)

class Edge(event.Emitter, VisibilitySuppressor):
    def __init__(self, first_id, second_id, suppressors=set()):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self, suppressors)
        self.id = make_id()
        self.first = first_id
        self.second = second_id
    
    def visibility_changed(self):
        self.emit("edge_changed", self.id)

class RelationException(Exception):
    def __init__(self, source_id, dest_id, relation_name, message):
        source_title = get_object(source_id).get_field("Title")
        dest_title = get_object(dest_id).get_field("Title")
        message = "Can't connect {0} to {1} by {2}: {3}".format(
            repr(source_title), repr(dest_title), repr(relation_name), message
        )
        super().__init__(message)

class LookupException(Exception):
    def __init__(self, message):
        super().__init__(message)

_edges = {}
def get_edge(edge_id):
    return _edges[edge_id]

def delete_edge(edge_id):
    del _edges[edge_id]

class Relation(event.Emitter, VisibilitySuppressor):
    def __init__(self, name, color=None, directed=True, acyclic=True, max_innodes=-1, max_outnodes=-1):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self)
        self.id = make_id()
        self.name = name
        self.color = color if color else Color.random()
        self.directed = directed
        self.acyclic = acyclic
        self._max_innodes = max_innodes
        self._max_outnodes = max_outnodes
        self.on_add = "do-nothing"
        self.on_delete = "do-nothing"
        self.reverse = False
        self._innodes = {}
        self._outnodes = {}
        self._forest = []
    
    def set_visible(self, is_visible, symbol=None):
        if symbol is None:
            symbol = self.id
        VisibilitySuppressor.set_visible(self, is_visible, symbol)
        for edge_id in self.all_edges():
            edge = get_edge(edge_id)
            edge.set_visible(is_visible, symbol)
    
    def __repr__(self):
        return "<Relation id={0} name={1}>".format(self.id, repr(self.name))

    def connect(self, srcid, dstid, source):
        edge = Edge(srcid, dstid, self.suppressors())
        self._connect(srcid, dstid, edge.id)
        if not self.directed:
            try:
                self._connect(dstid, srcid, edge.id)
            except RelationException as exception:
                self._disconnect(srcid, dstid)
                raise exception
        
        self._update_forest(srcid)
        self._update_forest(dstid)
        
        edge.add_listener("edge_changed", self._edge_changed)
        _edges[edge.id] = edge

        self.emit("edge_added", self.id, edge.id, srcid, dstid, source)
        return edge.id
    
    def _edge_changed(self, edge_id):
        self.emit("edge_changed", edge_id)
    
    def _update_forest(self, id):
        nodes = self.innodes if self.reverse else self.outnodes
        if len(nodes(id)) == 0:
            self._forest.append(id)
        elif id in self._forest:
            self._forest.remove(id)
    
    def innodes(self, id):
        return list(self._innodes.get(id, {}).keys())
    
    def outnodes(self, id):
        return list(self._outnodes.get(id, {}).keys())
    
    def disconnect(self, edge_id):
        edge = get_edge(edge_id)
        srcid = edge.first
        dstid = edge.second

        self._disconnect(srcid, dstid)
        if not self.directed:
            self._disconnect(dstid, srcid)
        self._update_forest(srcid)
        self._update_forest(dstid)

        edge.remove_listener("edge_changed", self._edge_changed)
        self.emit("edge_removed", edge.id)
        del _edges[edge.id]
    
    def roots(self):
        return list(self._forest)
    
    def is_tree(self):
        return self.directed and self._max_innodes > 1 and self._max_outnodes == 1

    def _connect(self, srcid, dstid, edge_id):
        outnodes = self._outnodes.get(srcid, {})
        innodes = self._innodes.get(dstid, {})
        if len(outnodes) == self._max_outnodes:
            raise RelationException(srcid, dstid, self.name, "Can't add more outnodes.")
        
        if len(innodes) == self._max_innodes:
            raise RelationException(srcid, dstid, self.name, "Can't add more innodes.")
        
        if self.acyclic and has_path(dstid, srcid, self.id):
            raise RelationException(srcid, dstid, self.name, "Relation is acyclic.")

        # TODO: Restrict the relation to certain types of objects.
        
        source_object = get_object(srcid)
        outnodes[dstid] = edge_id
        self._outnodes[srcid] = outnodes
        source_object.emit("object_changed", source_object.id)
        
        dest_object = get_object(dstid)
        innodes[srcid] = edge_id
        self._innodes[dstid] = innodes
        dest_object.emit("object_changed", dest_object.id)

    def _disconnect(self, srcid, dstid):
        del self._outnodes[srcid][dstid]
        if not self._outnodes[srcid]:
            del self._outnodes[srcid]
        source_object = get_object(srcid)
        source_object.emit("object_changed", source_object.id)

        del self._innodes[dstid][srcid]
        if not self._innodes[dstid]:
            del self._innodes[dstid]
        dest_object = get_object(dstid)
        dest_object.emit("object_changed", dest_object.id)

    def remove(self, id):
        """Remove all relations into and out of the given object"""
        edges = list(self.edges(id))
        for edge_id in edges:
            self.disconnect(edge_id)
    
    def edges(self, id):
        """Return all edges into and out of the given object"""
        innodes = dict(self._innodes.get(id, {}))
        outnodes = dict(self._outnodes.get(id, {}))
        for edge_id in innodes.values():
            yield edge_id
        for edge_id in outnodes.values():
            yield edge_id
    
    def all_edges(self):
        """Return all edges into and out of the given object"""
        innodes = dict(self._innodes)
        outnodes = dict(self._outnodes)
        visited = set()
        for dest_id, in_edges in innodes.items():
            for edge_id in in_edges.values():
                if not edge_id in visited:
                    yield edge_id
                    visited.add(edge_id)
        for dest_id, out_edges in outnodes.items():
            for edge_id in out_edges.values():
                if not edge_id in visited:
                    yield edge_id
                    visited.add(edge_id)
    
    def clear(self):
        for edge_id in self.all_edges():
            self.remove(edge_id)

class Field(object):
    def __init__(self, name, type, initial_value):
        self.name = name
        self.type = type
        self.initial_value = initial_value
    
    def is_valid(self, value):
        return self.type == type(value)

    def __repr__(self):
        return "Field({0}, {1}, {2})".format(repr(self.name), repr(self.type), repr(self.initial_value))

class Integer(Field):
    def __init__(self, name, initial_value):
        super().__init__(name, int, initial_value)
    
    def is_valid(self, value):
        return type(value) == int

class Float(Field):
    def __init__(self, name, initial_value):
        super().__init__(name, float, initial_value)
    
    def is_valid(self, value):
        return type(value) == float

class String(Field):
    def __init__(self, name, initial_value):
        super().__init__(name, str, initial_value)

def noop():
    pass
class Control(object):
    def __init__(self, name, code=None):
        self.name = name
        self.code = code

class CheckBox(Control):
    def __init__(self, name, checked=False):
        super().__init__(name)

class Class(event.Emitter, VisibilitySuppressor):
    def __init__(self, name, color, *fields):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self)
        self.id = make_id()
        self.name = name
        self.color = color
        self.fields = fields
    
    def set_visible(self, is_visible, symbol=None):
        if symbol is None:
            symbol = self.id
        VisibilitySuppressor.set_visible(self, is_visible, symbol)
        for object in objects.by_class(self.id):
            object.set_visible(is_visible, symbol)
    
    def __repr__(self):
        return "Class({0})".format(repr(self.name))
        # return "Class({0}, {1})".format(repr(self.name), ', '.join(map(repr, self.fields))) 

def is_field(f):
    return issubclass(type(f), Field)

def is_control(f):
    return issubclass(type(f), Control)

class Object(event.Emitter, VisibilitySuppressor):
    def __init__(self, klass, *values):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self, get_class(klass.id).suppressors())
        self.id = make_id()
        self.klass = klass
        self.fields = []
        self.tags = set()
        for i, field in enumerate(klass.fields):
            if i >= len(values):
                self.fields.append(field.initial_value)
            else:
                value = values[i]
                assert field.is_valid(value), "Expected {0}, got {1}".format(field.type, type(value))
                self.fields.append(value)

    def color(self):
        return self.klass.color
    
    def visibility_changed(self):
        self.emit("object_changed", self.id)
    
    def set_visible(self, is_visible, symbol=None):
        if symbol is None:
            symbol = self.id
        VisibilitySuppressor.set_visible(self, is_visible, symbol)
        # Hide edges pointing into and out of this object
        for relation in relations:
            for edge_id in relation.edges(self.id):
                edge = get_edge(edge_id)
                edge.set_visible(is_visible, symbol)

    def __repr__(self):
        return "<Object id={0} title={1}>".format(self.id, repr(self.get_field("Title")))
        # return "Object({0}, {1})".format(repr(self.klass), ', '.join(map(repr, self.fields)))

    def get_field(self, name):
        for i, field in enumerate(self.klass.fields):
            if field.name == name:
                return self.fields[i]
        assert False, "Can't find field {0} on object {1}".format(name, self.id)

    def set_field(self, name, value):
        for i, field in enumerate(self.klass.fields):
            if field.name == name:
                # TODO: Type-check value
                self.fields[i] = value
                if is_control(field):
                    self.fields[i].code(value)
                elif is_field(field):
                    self.emit("object_changed", self.id)
    
    def _class_changed(self, class_id):
        self.emit("object_changed", self.id)

class collection(list, event.Emitter):
    def __init__(self):
        list.__init__(self)
        event.Emitter.__init__(self)
    
    def append(self, object, source="model"):
        super().append(object)
        self.emit("object_created", object.id, source)
        object.add_listener("object_changed", self._object_changed)
        object.add_listener("class_changed", self._object_changed)
        object.add_listener("edge_added", self._edge_added)
        object.add_listener("edge_removed", self._edge_removed)
        object.add_listener("edge_changed", self._edge_changed)
        object.add_listener("relation_changed", self._relation_changed)
    
    def remove(self, object, source="model"):
        object.remove_listener("object_changed", self._object_changed)
        object.remove_listener("class_changed", self._object_changed)
        object.remove_listener("edge_added", self._edge_added)
        object.remove_listener("edge_removed", self._edge_removed)
        object.remove_listener("edge_changed", self._edge_changed)
        object.remove_listener("relation_changed", self._relation_changed)
        super().remove(object)
        self.emit("object_deleted", object.id, source)
    
    def _object_changed(self, object_id):
        self.emit("object_changed", object_id)

    def _edge_added(self, *args):
        self.emit("edge_added", *args)
    
    def _edge_removed(self, *args):
        self.emit("edge_removed", *args)
    
    def _edge_changed(self, *args):
        self.emit("edge_changed", *args)
    
    def _relation_changed(self, *args):
        self.emit("relation_changed", *args)
    
    def get_member(self, member_id):
        for member in self:
            if member.id == member_id:
                return member
        assert False, "No such member"

def _iter_objects(object_sets):
    for object_set in object_sets:
        for object in object_set:
            yield object

class collection_map(event.Emitter):
    def __init__(self):
        super().__init__()
        self._objects = {}
    
    def append(self, object, source):
        class_id = object.klass.id
        if class_id not in self._objects:
            self._objects[class_id] = set()
        self._objects[class_id].add(object)
        self.emit("object_created", object.id, source)
        object.add_listener("object_changed", self._object_changed)
    
    def remove(self, object, source):
        class_id = object.klass.id
        assert class_id in self._objects
        self._objects[class_id].remove(object)
        object.remove_listener("object_changed", self._object_changed)
        self.emit("object_deleted", object.id, source)
    
    def _object_changed(self, object_id):
        self.emit("object_changed", object_id)
    
    def by_class(self, class_id):
        return iter(self._objects.get(class_id, []))

    def __iter__(self):
        return _iter_objects(self._objects.values())
    
    def get_member(self, member_id):
        return get_object(member_id)

classes = collection()
objects = collection_map()
relations = collection()

def find_by_id(type, list, id):
    matches = [o for o in list if o.id == id]
    if len(matches) != 1:
        raise LookupException("Can't find {0} with id {1}".format(type, id))
    return matches[0]

def make_class(name, *custom_fields):
    default_fields = [
        Field("Title", str, ""),
    ]
    klass = Class(name, Color.random(), *default_fields, *custom_fields)
    classes.append(klass)
    return klass.id

def get_class(class_id):
    return find_by_id("class", classes, class_id)

def delete_class(class_id):
    global objects
    klass = get_class(class_id)
    object_ids = [o.id for o in objects if o.klass == klass]
    for object_id in object_ids:
        delete_object(object_id)
    classes.remove(klass)

def make_object(class_id, *values, source="model"):
    klass = get_class(class_id)
    object = Object(klass, *values)
    objects.append(object, source)
    klass.add_listener("class_changed", object._class_changed)
    return object.id

def get_objects_by_class(class_id):
    return objects.by_class(class_id)

def get_object(object_id):
    return find_by_id("object", objects, object_id)

def delete_object(object_id, source="model"):
    # Remove all relations involving this object
    for relation in relations:
        relation.remove(object_id)
    object = get_object(object_id)
    klass = object.klass
    klass.remove_listener("class_changed", object._class_changed)
    objects.remove(object, source)

def make_relation(name, *args, **kwargs):
    relation = Relation(name, *args, **kwargs)
    relations.append(relation)
    return relation.id

def get_relation(relation_id):
    return find_by_id("relation", relations, relation_id)

def delete_relation(relation_id):
    relation = get_relation(relation_id)
    relation.clear()
    relations.remove(get_relation(relation_id))

def connect(relation_id, src_id, dst_id, source="model"):
    relation = get_relation(relation_id)
    edge_id = relation.connect(src_id, dst_id, source)
    return edge_id

def disconnect(relation_id, *object_ids):
    relation = get_relation(relation_id)
    relation.disconnect(*object_ids)

class Color(object):
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b
    
    @staticmethod
    def random():
        rand = lambda: random.randint(0, 255)
        return Color(rand(), rand(), rand())

def class_id(id):
    return id

tag_class = make_class("Tag")

goal_class = make_class(
    "Goal",
)

task_class = make_class(
    "Task",
    Field("Urgent", bool, False),
    Field("Important", bool, False),
)

precedes = make_relation("precedes")

is_child_of = make_relation(
    "is a child of",
    directed=True,
    acyclic=True,
    max_outnodes=1
)

def outnodes(object_id, *relation_ids):
    outnode_ids = set()
    for relation_id in relation_ids:
        relation = get_relation(relation_id)
        if object_id in relation._outnodes:
            for outnode_id in relation._outnodes[object_id]:
                outnode_ids.add(outnode_id)
    return outnode_ids


def has_path(source_id, dest_id, *relation_ids):
    # Find a path from source to dest along the given relations
    frontier_queue = [source_id]
    frontier_set = set(frontier_queue)
    visited = set()
    while frontier_queue:
        object_id = frontier_queue.pop()
        frontier_set.remove(object_id)
        if object_id == dest_id:
            return True
        for neighbor_id in outnodes(object_id, *relation_ids):
            if neighbor_id not in frontier_set and neighbor_id not in visited:
                frontier_queue.insert(0, neighbor_id)
                frontier_set.add(neighbor_id)
    return False

def field(name):
    def fn(object):
        return object.get_field(name)
    return fn

def eq(lhs, rhs):
    def fn(object):
        return lhs(object) == rhs(object)
    return fn

def const(value):
    def fn(object):
        return value
    return fn

def has_type(klass):
    def fn(object):
        return object.klass.id == klass
    return fn

def has_path_to(dest_id, *relation_ids):
    def fn(source_object):
        return source_object.klass.id != tag_class and has_path(source_object.id, dest_id, *relation_ids)
    return fn

def land(*operands):
    def fn(object):
        for operand in operands:
            if not operand(object):
                return False
        return True
    return fn

def lor(*operands):
    def fn(object):
        for operand in operands:
            if operand(object):
                return True
        return False
    return fn

def innodes(object_id, relation_id):
    "Returns the number of nodes pointing the given node via the given edge type."
    relation: Relation = get_relation(relation_id)
    return relation.innodes(object_id)

def outnodes(object_id, relation_id):
    "Returns the number of nodes pointing the given node via the given edge type."
    relation: Relation = get_relation(relation_id)
    return relation.outnodes(object_id)