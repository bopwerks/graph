import event
import random
import lang
import log

_id = 0
def make_id():
    global _id
    _id += 1
    return _id

class Color(object):
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b
    
    @staticmethod
    def random():
        rand = lambda: random.randint(0, 255)
        return Color(rand(), rand(), rand())
    
    @staticmethod
    def from_color(color):
        return Color(color.r, color.g, color.b)

class VisibilitySuppressor(object):
    def __init__(self, suppressors=set()):
        self._suppressors = set(suppressors)
    
    def set_visible(self, is_visible, symbol):
        fn = self._suppressors.discard if is_visible else self._suppressors.add
        old_size = len(self._suppressors)
        fn(symbol)
        new_size = len(self._suppressors)
        for entity in self.suppressable_entities():
            entity.set_visible(is_visible, symbol)
        if (old_size == 0 and new_size == 1) or (old_size == 1 and new_size == 0):
            self.visibility_changed()
    
    def visibility_changed(self):
        pass

    def is_visible(self):
        return not bool(self._suppressors)
    
    def suppressors(self):
        return set(self._suppressors)

# Classes

class Class(event.Emitter, VisibilitySuppressor):
    def __init__(self, name, color, *fields):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self)
        self.id = make_id()
        self.name = name
        self.color = color
        self.fields = fields
        self.objects = set()
    
    def suppressable_entities(self):
        for object_id in set(self.objects):
            yield __id_entity_map[object_id]
    
    def __repr__(self):
        return "Class({0})".format(repr(self.name))

def class_new(name, *custom_fields):
    klass = Class(name, Color.random())
    __id_entity_map[klass.id] = klass
    __type_id_map[Class].append(klass.id)
    __emit.class_created(klass.id)
    return klass.id

def get_class(class_id):
    return __id_entity_map[class_id]

def get_classes():
    return list(__type_id_map[Class])

def class_delete(class_id):
    klass = get_class(class_id)
    for object_id in set(klass.objects):
        object_delete(object_id)
    __emit.class_deleted(class_id)
    __type_id_map[Class].remove(class_id)
    del __id_entity_map[class_id]

# Objects

class Object(event.Emitter, VisibilitySuppressor):
    def __init__(self, klass, suppressors, *values):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self, suppressors)
        self.id = make_id()
        self.name = "New {0}".format(klass.name)
        self.klass = klass
        self.fields = []
    
    def visibility_changed(self):
        self.emit("object_changed", self.id)
    
    def suppressable_entities(self):
        for relation in relations:
            for edge_id in get_object_edges(self.id, relation.id):
                yield __id_entity_map[edge_id]

    def __repr__(self):
        return "<Object id={0} title={1}>".format(self.id, repr(self.title))

def object_new(class_id, *values, source="model"):
    klass = get_class(class_id)
    object = Object(klass, klass.suppressors(), *values)

    __id_entity_map[object.id] = object
    object.klass.objects.add(object.id)
    __type_id_map[Object].add(object.id)
    __emit.object_created(object.id)

    return object.id

def get_object(object_id):
    return __id_entity_map[object_id]

def get_objects():
    return list(__type_id_map[Object])

def object_delete(object_id, source="model"):
    object = get_object(object_id)
    for relation_id in __type_id_map[Relation]:
        object_delete_edges(object_id, relation_id)
        
    __emit.object_deleted(object_id)
    __type_id_map[Object].remove(object_id)
    object.klass.objects.remove(object_id)
    del __id_entity_map[object_id]

    def innodes(self, id):
        return list(self._innodes.get(id, {}).keys())

def object_get_innodes(object_id, relation_id):
    relation = get_relation(relation_id)
    return list(relation.innodes.get(object_id, {}).keys())

def object_get_outnodes(object_id, relation_id):
    relation = get_relation(relation_id)
    return list(relation.outnodes.get(object_id, {}).keys())

def object_delete_edges(object_id, relation_id):
    relation = get_relation(relation_id)
    edge_ids = list(object_get_edges(object_id, relation_id))
    for edge_id in edge_ids:
        relation.disconnect(edge_id)

def object_get_edges(object_id, relation_id):
    object = get_object(object_id)
    relation = get_relation(relation_id)
    innode_ids = dict(relation.innodes.get(id, {})).values()
    for edge_id in innode_ids:
        yield edge_id
    outnode_ids = dict(relation.outnodes.get(id, {})).values()
    for edge_id in outnode_ids:
        yield edge_id

def object_get_color(object_id):
    object = get_object(object_id)
    return object.klass.color

# Relations

class RelationException(Exception):
    def __init__(self, source_id, dest_id, relation_name, message):
        source_title = get_object(source_id).get_field("Title")
        dest_title = get_object(dest_id).get_field("Title")
        message = "Can't connect {0} to {1} by {2}: {3}".format(
            repr(source_title), repr(dest_title), repr(relation_name), message
        )
        super().__init__(message)

class Relation(event.Emitter, VisibilitySuppressor):
    def __init__(self, name, color=None, directed=True, acyclic=True, max_innodes=-1, max_outnodes=-1):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self)
        self.id = make_id()
        self.name = name
        self.color = color if color else Color.random()
        self.directed = directed
        self.acyclic = acyclic
        self.max_innodes = max_innodes
        self.max_outnodes = max_outnodes
        self.on_add = "do-nothing"
        self.on_delete = "do-nothing"
        self.reverse = False
        self.innodes = {}
        self.outnodes = {}
        self.forest = []
    
    def suppressable_entities(self):
        for edge_id in get_relation_edges(self.id):
            yield __id_entity_map[edge_id]
    
    def __repr__(self):
        return "<Relation id={0} name={1}>".format(self.id, repr(self.name))

def relation_new(name, *args, **kwargs):
    relation = Relation(name, *args, **kwargs)
    __id_entity_map[relation.id] = relation
    __type_id_map[Relation].append(relation.id)
    __emit.relation_created(relation.id)
    return relation.id

def get_relation(relation_id):
    return __id_entity_map[relation_id]

def get_relations():
    return list(__type_id_map[Relation])

def relation_delete(relation_id):
    __emit.relation_deleted(relation_id)
    relation_clear_edges(relation_id)
    __type_id_map[Relation].remove(relation_id)
    del __id_entity_map[relation_id]

def relation_get_edges(relation_id):
    relation = get_relation(relation_id)
    innodes = dict(relation.innodes)
    outnodes = dict(relation.outnodes)
    visited = set()
    for dest_id, in_edges in innodes.items():
        in_edges = list(in_edges.values())
        for edge_id in in_edges:
            if not edge_id in visited:
                yield edge_id
                visited.add(edge_id)
    for dest_id, out_edges in outnodes.items():
        out_edges = list(out_edges.values())
        for edge_id in out_edges:
            if not edge_id in visited:
                yield edge_id
                visited.add(edge_id)

def relation_get_color(relation_id):
    relation = get_relation(relation_id)
    return Color.from_color(relation.color)

def relation_clear_edges(relation_id):
    for edge_id in relation_get_edges(relation_id):
        edge_delete(edge_id)

def relation_roots(relation_id):
    relation = get_relation(relation_id)
    return list(relation.forest)

def relation_is_tree(relation_id):
    relation = get_relation(relation_id)
    return relation.directed and relation.max_innodes > 1 and relation.max_outnodes == 1

# Edges

class Edge(event.Emitter, VisibilitySuppressor):
    def __init__(self, relation_id, src_id, dst_id, suppressors=set()):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self, suppressors)
        self.id = make_id()
        self.relation_id = relation_id
        self.src_id = src_id
        self.dst_id = dst_id
    
    def visibility_changed(self):
        self.emit("edge_changed", self.id)

def edge_new(relation_id, srcid, dstid, source="model"):
    relation = get_relation(relation_id)
    edge = Edge(relation_id, srcid, dstid, relation.suppressors())
    _edge_connect(relation_id, srcid, dstid, edge.id)
    if not relation.directed:
        try:
            _edge_connect(relation_id, dstid, srcid, edge.id)
        except RelationException as exception:
            _edge_disconnect(relation_id, srcid, dstid)
            raise exception
    
    _edge_update_forest(relation_id, srcid)
    _edge_update_forest(relation_id, dstid)
    
    __type_id_map[Edge].add(edge.id)
    __id_entity_map[edge.id] = edge
    __emit.edge_created(edge.id)
    try:
        lang.eval(lang.read(relation.on_add))(edge.id)
    except Exception as e:
        log.error(e.message)
    return edge.id

def _edge_update_forest(relation_id, object_id):
    relation = get_relation(relation_id)
    nodes = object_get_innodes if relation.reverse else object_get_outnodes
    if len(nodes(object_id, relation_id)) == 0:
        relation.forest.append(object_id)
    elif object_id in relation.forest:
        relation.forest.remove(object_id)

def _edge_connect(relation_id, srcid, dstid, edge_id):
    relation = get_relation(relation_id)
    outnodes = relation.outnodes.get(srcid, {})
    innodes = relation.innodes.get(dstid, {})
    if len(outnodes) == relation.max_outnodes:
        raise RelationException(srcid, dstid, relation.name, "Can't add more outnodes.")
    
    if len(innodes) == relation.max_innodes:
        raise RelationException(srcid, dstid, relation.name, "Can't add more innodes.")
    
    if relation.acyclic and has_path(dstid, srcid, relation_id):
        raise RelationException(srcid, dstid, relation.name, "Relation is acyclic.")

    # TODO: Restrict the relation to certain types of objects.
    
    source_object = get_object(srcid)
    outnodes[dstid] = edge_id
    relation.outnodes[srcid] = outnodes
    __emit.object_changed(srcid)
    
    dest_object = get_object(dstid)
    innodes[srcid] = edge_id
    relation.innodes[dstid] = innodes
    __emit.object_changed(dstid)

def edge_delete(edge_id):
    edge = get_edge(edge_id)
    relation_id = edge.relation_id
    relation = get_relation(relation_id)
    srcid = edge.src_id
    dstid = edge.dst_id

    _edge_disconnect(relation, srcid, dstid)
    if not relation.directed:
        _edge_disconnect(relation, dstid, srcid)
    _edge_update_forest(relation_id, srcid)
    _edge_update_forest(relation_id, dstid)

    __emit.edge_deleted(edge_id)
    try:
        lang.eval(lang.read(relation.on_delete))(edge_id)
    except Exception as e:
        log.error(e.message)
    __type_id_map[Edge].remove(edge_id)
    del __id_entity_map[edge_id]

def _edge_disconnect(relation, srcid, dstid):
    del relation.outnodes[srcid][dstid]
    if not relation.outnodes[srcid]:
        del relation.outnodes[srcid]
    __emit.object_changed(srcid)

    del relation.innodes[dstid][srcid]
    if not relation.innodes[dstid]:
        del relation.innodes[dstid]
    __emit.object_changed(dstid)

def get_edge(edge_id):
    return __id_entity_map[edge_id]

def get_edges():
    return list(__type_id_map[Edge])

# Object Filters

class ObjectFilter(object):
    def __init__(self, title, predicate):
        self.id = make_id()
        self.title = title
        self.predicate = predicate

def object_filter_new(title, predicate):
    filter = ObjectFilter(title, predicate)
    __id_entity_map[filter.id] = filter
    __type_id_map[ObjectFilter].add(filter.id)
    return filter.id

def object_filter_get(object_filter_id):
    return __id_entity_map[object_filter_id]

def object_filter_delete(object_filter_id):
    __type_id_map[ObjectFilter].remove(object_filter_id)
    del __id_entity_map[object_filter_id]

# Event Handling

class Delegate(object):
    def object_created(self, id):
        pass

    def object_changed(self, id):
        pass

    def object_deleted(self, id):
        pass

    def class_created(self, id):
        pass

    def class_changed(self, id):
        pass

    def class_deleted(self, id):
        pass

    def relation_created(self, id):
        pass

    def relation_changed(self, id):
        pass

    def relation_deleted(self, id):
        pass

    def edge_created(self, id):
        pass

    def edge_changed(self, id):
        pass

    def edge_deleted(self, id):
        pass

class __SuperDelegate(Delegate):
    def __init__(self, delegates):
        Delegate.__init__(self)
        self.delegates = delegates

    def object_created(self, id):
        for delegate in self.delegates:
            delegate.object_created(id)

    def object_changed(self, id):
        for delegate in self.delegates:
            delegate.object_changed(id)

    def object_deleted(self, id):
        for delegate in self.delegates:
            delegate.object_deleted(id)

    def class_created(self, id):
        for delegate in self.delegates:
            delegate.class_created(id)

    def class_changed(self, id):
        for delegate in self.delegates:
            delegate.class_changed(id)

    def class_deleted(self, id):
        for delegate in self.delegates:
            delegate.class_deleted(id)

    def relation_created(self, id):
        for delegate in self.delegates:
            delegate.relation_created(id)

    def relation_changed(self, id):
        for delegate in self.delegates:
            delegate.relation_changed(id)

    def relation_deleted(self, id):
        for delegate in self.delegates:
            delegate.relation_deleted(id)

    def edge_created(self, id):
        for delegate in self.delegates:
            delegate.edge_created(id)

    def edge_changed(self, id):
        for delegate in self.delegates:
            delegate.edge_changed(id)

    def edge_deleted(self, id):
        for delegate in self.delegates:
            delegate.edge_deleted(id)

__delegates = set()
__emit = __SuperDelegate(__delegates)

def add_delegate(delegate: Delegate):
    __delegates.add(delegate)

def remove_delegate(delegate: Delegate):
    __delegates.remove(delegate)

# Helper Functions

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
        for neighbor_id in object_get_outnodes(object_id, *relation_ids):
            if neighbor_id not in frontier_set and neighbor_id not in visited:
                frontier_queue.insert(0, neighbor_id)
                frontier_set.add(neighbor_id)
    return False

# Top-Level Model Data Structures

__id_entity_map = {}
__type_id_map = {
    Class: [],
    Edge: set(),
    Object: set(),
    Relation: [],
}

def _get_entity(entity_id):
    return __id_entity_map[entity_id]

def delete(entity_id):
    entity = _get_entity(entity_id)
    entity_type = type(entity)
    type_delete_map = {
        Class: class_delete,
        Edge: edge_delete,
        Object: object_delete,
        Relation: relation_delete,
    }
    assert entity_type in type_delete_map
    type_delete_map[entity_type](entity_id)

def reset():
    while len(__id_entity_map) != 0:
        entity_id = list(__id_entity_map)[0]
        delete(entity_id)