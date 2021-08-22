import itertools
import event
import random
import lang
import log

_id = 0
def make_id():
    global _id
    _id += 1
    return _id

class TypeRepr(type):
    def __repr__(klass):
        return klass.__name__

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
    
    def __repr__(self):
        return "Color({0},{1},{2})".format(self.r, self.g, self.b)

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

class Class(event.Emitter, VisibilitySuppressor, metaclass=TypeRepr):
    def __init__(self, id, name, color):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self)
        self.id = id
        self.name = name
        self.color = color
        self.fields = []
        self.objects = set()
    
    def suppressable_entities(self):
        for object_id in set(self.objects):
            yield _get_object(object_id)
    
    def to_dict(self):
        return {
            "type": Class,
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "fields": list(self.fields),
            "objects": set(self.objects),
        }
    
    @staticmethod
    def from_dict(d):
        klass = Class(d["id"], d["name"], d["color"])
        klass.fields = d["fields"]
        klass.objects = d["objects"]
        return klass

def class_new(name, source="model"):
    id = make_id()
    klass = Class(id, name, Color.random())
    __id_entity_map[id] = klass
    __type_id_map[Class].append(id)
    _emit.class_created(id, source)
    return id

def _make_type_getter(expected_type):
    def getter(entity_id):
        entity = _get_entity(entity_id)
        assert type(entity) == expected_type
        return entity
    return getter

_get_class = _make_type_getter(Class)

def get_classes():
    return list(__type_id_map[Class])

def class_delete(class_id, source="model"):
    klass = _get_class(class_id)
    for object_id in set(klass.objects):
        object_delete(object_id)
    for field_id in list(klass.fields):
        field_delete(field_id)
    _emit.class_deleted(class_id, source)
    __type_id_map[Class].remove(class_id)
    del __id_entity_map[class_id]

def class_get_name(class_id):
    klass = _get_class(class_id)
    return klass.name

def class_set_name(class_id, name, source="model"):
    klass = _get_class(class_id)
    klass.name = name
    _emit.class_changed(class_id, source)
    for object_id in klass.objects:
        _emit.object_changed(object_id, source)

def class_is_visible(class_id):
    klass = _get_class(class_id)
    return klass.is_visible()

def class_set_visible(class_id, is_visible, symbol=None):
    klass: Class = _get_class(class_id)
    return klass.set_visible(is_visible, symbol if symbol else class_id)

def class_get_color(class_id):
    klass = _get_class(class_id)
    return Color.from_color(klass.color)

def class_set_color(class_id, color, source="model"):
    klass = _get_class(class_id)
    new_color = Color.from_color(color)
    klass.color = new_color
    for object_id in klass.objects:
        _emit.object_changed(object_id, source)

def class_get_fields(class_id):
    klass = _get_class(class_id)
    return list(klass.fields)

def class_add_field(class_id, field_name, field_type, initial_value=None, source="model"):
    klass = _get_class(class_id)
    field_id = make_id()
    field = Field(field_id, class_id, field_name, field_type, initial_value)
    __id_entity_map[field_id] = field
    __type_id_map[Field].add(field_id)
    klass.fields.append(field_id)
    for object_id in klass.objects:
        object = _get_object(object_id)
        member_id = make_id()
        member = Member(member_id, field_id)
        __id_entity_map[member_id] = member
        __type_id_map[Member].add(member_id)
        object.members.append(member_id)
    _emit.class_changed(class_id, source)
    for object_id in klass.objects:
        _emit.object_changed(object_id, source)
    return field_id

# Objects

class Object(event.Emitter, VisibilitySuppressor, metaclass=TypeRepr):
    def __init__(self, id, class_id, suppressors, name="New Object"):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self, suppressors)
        self.id = id
        self.name = name
        self.klass = class_id
        self.members = []
    
    def visibility_changed(self):
        _emit.object_changed(self.id, "model")
    
    def suppressable_entities(self):
        for relation_id in get_relations():
            for edge_id in object_get_edges(self.id, relation_id):
                yield _get_edge(edge_id)

    def to_dict(self):
        return {
            "type": Object,
            "id": self.id,
            "name": self.name,
            "class_id": self.klass,
            "members": self.members,
            "suppressors": self._suppressors,
        }
    
    @staticmethod
    def from_dict(d):
        object = Object(d["id"], d["class_id"], d["suppressors"], name=d["name"])
        object.members = d["members"]
        return object

def object_new(class_id, source="model"):
    klass = _get_class(class_id)
    object_id = make_id()
    object = Object(object_id, class_id, klass.suppressors(), name="New {0}".format(klass.name))

    __id_entity_map[object_id] = object
    klass.objects.add(object_id)
    __type_id_map[Object].add(object_id)
    
    for field_id in klass.fields:
        member_id = make_id()
        member = Member(member_id, field_id)
        __id_entity_map[member.id] = member
        __type_id_map[Member].add(member.id)
        object.members.append(member.id)

    _emit.object_created(object_id, source)

    return object_id

_get_object = _make_type_getter(Object)

def get_objects():
    return list(__type_id_map[Object])

def object_delete(object_id, source="model"):
    object = _get_object(object_id)
    for relation_id in __type_id_map[Relation]:
        object_delete_edges(object_id, relation_id)
    _emit.object_deleted(object_id, source)
    for member_id in list(object.members):
        __type_id_map[Member].remove(member_id)
        del __id_entity_map[member_id]
    object.members = []
    __type_id_map[Object].remove(object_id)
    klass = _get_class(object.klass)
    klass.objects.remove(object_id)
    del __id_entity_map[object_id]

def object_get_innodes(object_id, relation_id):
    relation = _get_relation(relation_id)
    return list(relation.innodes.get(object_id, {}).keys())

def object_get_outnodes(object_id, relation_id):
    relation = _get_relation(relation_id)
    return list(relation.outnodes.get(object_id, {}).keys())

def object_delete_edges(object_id, relation_id):
    relation = _get_relation(relation_id)
    edge_ids = list(object_get_edges(object_id, relation_id))
    for edge_id in edge_ids:
        edge_delete(edge_id)

def object_get_edges(object_id, relation_id):
    relation = _get_relation(relation_id)
    edge_ids = set()
    innode_ids = dict(relation.innodes.get(object_id, {})).values()
    for edge_id in innode_ids:
        edge_ids.add(edge_id)
    outnode_ids = dict(relation.outnodes.get(object_id, {})).values()
    for edge_id in outnode_ids:
        edge_ids.add(edge_id)
    return edge_ids

def object_get_color(object_id):
    object = _get_object(object_id)
    klass = _get_class(object.klass)
    return klass.color

def object_get_name(object_id):
    object = _get_object(object_id)
    return object.name

def object_set_name(object_id, name, source="model"):
    object = _get_object(object_id)
    object.name = name
    _emit.object_changed(object_id, source)

def object_is_visible(object_id):
    object = _get_object(object_id)
    return object.is_visible()

def object_get_class(object_id):
    object = _get_object(object_id)
    klass = _get_class(object.klass)
    return klass.id

def object_get_members(object_id):
    object = _get_object(object_id)
    return list(object.members)

# Fields

class Field(object, metaclass=TypeRepr):
    def __init__(self, id, class_id, name, type, initial_value=None):
        self.id = id
        self.name = name
        self.klass = class_id
        self.type = type
        self.initial_value = initial_value if type.is_valid(initial_value) else type.initial_value
    
    def convert(self, value):
        return self.type.convert(value)
    
    def is_valid(self, value):
        return type(value) == self.type

    def to_dict(self):
        return {
            "type": Field,
            "id": self.id,
            "name": self.name,
            "class_id": self.klass,
            "field_type": self.type,
            "initial_value": self.initial_value,
        }
    
    @staticmethod
    def from_dict(d):
        object = Field(d["id"], d["class_id"], d["name"], d["field_type"], d["initial_value"])
        return object

_get_field = _make_type_getter(Field)

def field_get_name(field_id):
    field = _get_field(field_id)
    return field.name

def field_set_name(field_id, name, source="model"):
    field = _get_field(field_id)
    field.name = name
    klass = _get_class(field.klass)
    _emit.class_changed(klass.id, source)
    for object_id in klass.objects:
        _emit.object_changed(object_id, source)

def field_get_type(field_id):
    field = _get_field(field_id)
    return field.type

def field_get_initial_value(field_id):
    field = _get_field(field_id)
    return field.initial_value

def field_set_initial_value(field_id, value):
    field = _get_field(field_id)
    if not field.type.is_valid(value):
        raise InvalidTypeException()
    field.initial_value = value

def make_str_to(type_or_field):
    def str_to(old_value):
        try:
            new_value = type_or_field.convert(old_value)
        except:
            new_value = type_or_field.initial_value
        return new_value
    return str_to

# When converting a field value, failure to convert uses type initial value
# When converting a member value, failure to convert uses field initial value

def field_set_type(field_id, new_type, source="model"):
    field = _get_field(field_id)
    convert_field_value = {
        Integer: {
            Integer: int,
            String: str,
            Float: float,
            Bool: bool,
        },
        String: {
            Integer: make_str_to(Integer),
            String: str,
            Float: make_str_to(Float),
            Bool: bool,
        },
        Float: {
            Integer: int,
            String: str,
            Float: float,
            Bool: bool,
        },
        Bool: {
            Integer: int,
            String: str,
            Float: float,
            Bool: bool,
        }
    }
    convert_member_value = {
        Integer: {
            Integer: int,
            String: str,
            Float: float,
            Bool: bool,
        },
        String: {
            Integer: make_str_to(field),
            String: str,
            Float: make_str_to(field),
            Bool: bool,
        },
        Float: {
            Integer: int,
            String: str,
            Float: float,
            Bool: bool,
        },
        Bool: {
            Integer: int,
            String: str,
            Float: float,
            Bool: bool,
        }
    }
    old_type = field.type
    old_initial_value = field.initial_value
    new_initial_value = convert_field_value[old_type][new_type](old_initial_value)
    field.type = new_type
    field.initial_value = new_initial_value

    klass = _get_class(field.klass)
    _emit.class_changed(klass.id, source)
    position = klass.fields.index(field_id)
    for object_id in klass.objects:
        # Convert type of corresponding member in object
        object = _get_object(object_id)
        member_id = object.members[position]
        old_member_value = member_get_value(member_id)
        new_member_value = convert_member_value[old_type][new_type](old_member_value)
        member_set_value(member_id, new_member_value)
        _emit.object_changed(object_id, source)

def field_delete(field_id, source="model"):
    field = _get_field(field_id)
    klass = _get_class(field.klass)
    # Remove the field from its class, saving its position
    position = klass.fields.index(field_id)
    klass.fields.pop(position)
    # Remove the associated member from each of the objects of the class
    for object_id in klass.objects:
        object = _get_object(object_id)
        member_id = object.members[position]
        __type_id_map[Member].remove(member_id)
        del __id_entity_map[member_id]
        object.members.pop(position)
    # Signal the change to the class and object event handlers
    _emit.class_changed(klass.id, source)
    for object_id in klass.objects:
        _emit.object_changed(object_id, source)
    # Remove the field from the top-level data structures
    __type_id_map[Field].remove(field_id)
    del __id_entity_map[field_id]

# Members

class Member(object, metaclass=TypeRepr):
    def __init__(self, id, field_id, value=None):
        self.id = id
        self.field = field_id
        self.value = value if not value is None else field_get_initial_value(field_id)

    def to_dict(self):
        return {
            "type": Member,
            "id": self.id,
            "field": self.field,
            "value": self.value,
        }
    
    @staticmethod
    def from_dict(d):
        member = Member(d["id"], d["field"], d["value"])
        return member

_get_member = _make_type_getter(Member)

def member_get_value(member_id):
    member = _get_member(member_id)
    return member.value

class InvalidTypeException(Exception):
    def __init__(self, message):
        super().__init__(message)

def member_set_value(member_id, value):
    member = _get_member(member_id)
    if not member.field.type.is_valid(value):
        raise InvalidTypeException("blam")
    member.value = value

def member_get_field(member_id):
    member = _get_member(member_id)
    return member.field

# Relations

class RelationException(Exception):
    def __init__(self, source_id, dest_id, relation_name, message):
        source_title = object_get_name(source_id)
        dest_title = object_get_name(dest_id)
        message = "Can't connect {0} to {1} by {2}: {3}".format(
            repr(source_title), repr(dest_title), repr(relation_name), message
        )
        super().__init__(message)

class Relation(event.Emitter, VisibilitySuppressor, metaclass=TypeRepr):
    def __init__(self, id, name):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self)
        self.id = id
        self.name = name
        self.color = Color.random()
        self.directed = True
        self.acyclic = True
        self.max_innodes = -1
        self.max_outnodes = -1
        self.on_add = "do-nothing"
        self.on_delete = "do-nothing"
        self.reverse = False
        self.innodes = {}
        self.outnodes = {}
        self.forest = []
    
    def suppressable_entities(self):
        for edge_id in get_relation_edges(self.id):
            yield __id_entity_map[edge_id]

    def to_dict(self):
        return {
            "type": Relation,
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "directed": self.directed,
            "acyclic": self.acyclic,
            "max_innodes": self.max_innodes,
            "max_outnodes": self.max_outnodes,
            "on_add": self.on_add,
            "on_delete": self.on_delete,
            "reverse": self.reverse,
            "innodes": dict(self.innodes),
            "outnodes": dict(self.outnodes),
            "forest": list(self.forest),
        }
    
    @staticmethod
    def from_dict(d):
        relation = Relation(d["id"], d["name"])
        relation.color = d["color"]
        relation.directed = d["directed"]
        relation.acyclic = d["acyclic"]
        relation.max_innodes = d["max_innodes"]
        relation.max_outnodes = d["max_outnodes"]
        relation.on_add = d["on_add"]
        relation.on_delete = d["on_delete"]
        relation.reverse = d["reverse"]
        relation.innodes = d["innodes"]
        relation.outnodes = d["outnodes"]
        relation.forest = d["forest"]
        return relation

def relation_new(name, *args, source="model", **kwargs):
    relation_id = make_id()
    relation = Relation(relation_id, name, *args, **kwargs)
    __id_entity_map[relation_id] = relation
    __type_id_map[Relation].append(relation_id)
    _emit.relation_created(relation_id, source)
    return relation_id

_get_relation = _make_type_getter(Relation)

def get_relations():
    return list(__type_id_map[Relation])

def relation_delete(relation_id, source="model"):
    _emit.relation_deleted(relation_id, source)
    relation_delete_edges(relation_id)
    __type_id_map[Relation].remove(relation_id)
    del __id_entity_map[relation_id]

def relation_get_edges(relation_id):
    relation = _get_relation(relation_id)
    innodes = dict(relation.innodes)
    outnodes = dict(relation.outnodes)
    visited = set()
    edge_ids = set()
    for dest_id, in_edges in innodes.items():
        in_edges = list(in_edges.values())
        for edge_id in in_edges:
            if not edge_id in visited:
                edge_ids.add(edge_id)
                visited.add(edge_id)
    for dest_id, out_edges in outnodes.items():
        out_edges = list(out_edges.values())
        for edge_id in out_edges:
            if not edge_id in visited:
                edge_ids.add(edge_id)
                visited.add(edge_id)
    return edge_ids

def relation_get_color(relation_id):
    relation = _get_relation(relation_id)
    return Color.from_color(relation.color)

def relation_set_color(relation_id, color, source="model"):
    relation = _get_relation(relation_id)
    new_color = Color.from_color(color)
    relation.color = new_color
    _emit.relation_changed(relation_id, source)
    for edge_id in relation_get_edges(relation_id):
        _emit.edge_changed(edge_id, source)

def relation_get_name(relation_id):
    relation = _get_relation(relation_id)
    return relation.name

def relation_set_name(relation_id, name, source="model"):
    relation = _get_relation(relation_id)
    relation.name = name
    _emit.relation_changed(relation_id, source)

def relation_is_visible(relation_id):
    relation = _get_relation(relation_id)
    return relation.is_visible()

def relation_is_directed(relation_id):
    relation = _get_relation(relation_id)
    return relation.directed

def relation_set_directed(relation_id, is_directed, source="model"):
    relation = _get_relation(relation_id)
    relation.directed = is_directed
    _emit.relation_changed(relation_id, source)

def relation_is_acyclic(relation_id):
    relation = _get_relation(relation_id)
    return relation.acyclic

def relation_set_acyclic(relation_id, is_acyclic, source="model"):
    relation = _get_relation(relation_id)
    relation.acyclic = is_acyclic
    _emit.relation_changed(relation_id, source)

def relation_is_reverse(relation_id):
    relation = _get_relation(relation_id)
    return relation.reverse

def relation_set_reverse(relation_id, is_reverse, source="model"):
    relation = _get_relation(relation_id)
    relation.reverse = is_reverse
    _emit.relation_changed(relation_id, source)

def relation_get_max_innodes(relation_id):
    relation = _get_relation(relation_id)
    return relation.max_innodes

def relation_set_max_innodes(relation_id, max_innodes, source="model"):
    relation = _get_relation(relation_id)
    relation.max_innodes = max_innodes
    _emit.relation_changed(relation_id, source)

def relation_get_max_outnodes(relation_id):
    relation = _get_relation(relation_id)
    return relation.max_outnodes

def relation_set_max_outnodes(relation_id, max_outnodes, source="model"):
    relation = _get_relation(relation_id)
    relation.max_outnodes = max_outnodes
    _emit.relation_changed(relation_id, source)

def relation_get_on_add_handler(relation_id):
    relation = _get_relation(relation_id)
    return relation.on_add

def relation_set_on_add_handler(relation_id, on_add, source="model"):
    relation = _get_relation(relation_id)
    relation.on_add = on_add
    _emit.relation_changed(relation_id, source)

def relation_get_on_delete_handler(relation_id):
    relation = _get_relation(relation_id)
    return relation.on_delete

def relation_set_on_delete_handler(relation_id, on_delete, source="model"):
    relation = _get_relation(relation_id)
    relation.on_delete = on_delete
    _emit.relation_changed(relation_id, source)

def relation_delete_edges(relation_id):
    for edge_id in relation_get_edges(relation_id):
        edge_delete(edge_id)

def relation_roots(relation_id):
    relation = _get_relation(relation_id)
    return list(relation.forest)

def relation_is_tree(relation_id):
    relation = _get_relation(relation_id)
    return relation.directed and relation.max_innodes > 1 and relation.max_outnodes == 1

# Edges

class Edge(event.Emitter, VisibilitySuppressor, metaclass=TypeRepr):
    def __init__(self, id, relation_id, src_id, dst_id, suppressors=set()):
        event.Emitter.__init__(self)
        VisibilitySuppressor.__init__(self, suppressors)
        self.id = id
        self.relation_id = relation_id
        self.src_id = src_id
        self.dst_id = dst_id
    
    def suppressable_entities(self):
        return []
    
    def visibility_changed(self):
        _emit.edge_changed(self.id, "model")

    def to_dict(self):
        return {
            "type": Edge,
            "id": self.id,
            "relation_id": self.relation_id,
            "src_id": self.src_id,
            "dst_id": self.dst_id,
            "suppressors": self._suppressors,
        }
    
    @staticmethod
    def from_dict(d):
        edge = Edge(d["id"], d["relation_id"], d["src_id"], d["dst_id"], d["suppressors"])
        return edge

def edge_new(relation_id, srcid, dstid, source="model"):
    relation = _get_relation(relation_id)
    edge_id = make_id()
    edge = Edge(edge_id, relation_id, srcid, dstid, relation.suppressors())
    _edge_connect(relation_id, srcid, dstid, edge_id)
    if not relation.directed:
        try:
            _edge_connect(relation_id, dstid, srcid, edge_id)
        except RelationException as exception:
            _edge_disconnect(relation_id, srcid, dstid, source)
            raise exception
    
    _edge_update_forest(relation_id, srcid)
    _edge_update_forest(relation_id, dstid)
    
    __type_id_map[Edge].add(edge_id)
    __id_entity_map[edge_id] = edge
    _emit.edge_created(edge_id, source)
    try:
        lang.eval(lang.read(relation.on_add))(edge_id)
    except Exception as e:
        log.error(e.message)
    return edge_id

def _edge_update_forest(relation_id, object_id):
    relation = _get_relation(relation_id)
    nodes = object_get_innodes if relation.reverse else object_get_outnodes
    if len(nodes(object_id, relation_id)) == 0:
        relation.forest.append(object_id)
    elif object_id in relation.forest:
        relation.forest.remove(object_id)

def _edge_connect(relation_id, srcid, dstid, edge_id, source="model"):
    relation = _get_relation(relation_id)
    outnodes = relation.outnodes.get(srcid, {})
    innodes = relation.innodes.get(dstid, {})
    if len(outnodes) == relation.max_outnodes:
        raise RelationException(srcid, dstid, relation.name, "Can't add more outnodes.")
    
    if len(innodes) == relation.max_innodes:
        raise RelationException(srcid, dstid, relation.name, "Can't add more innodes.")
    
    if relation.acyclic and has_path(dstid, srcid, relation_id):
        raise RelationException(srcid, dstid, relation.name, "Relation is acyclic.")

    # TODO: Restrict the relation to certain types of objects.
    
    source_object = _get_object(srcid)
    outnodes[dstid] = edge_id
    relation.outnodes[srcid] = outnodes
    _emit.object_changed(srcid, source)
    
    dest_object = _get_object(dstid)
    innodes[srcid] = edge_id
    relation.innodes[dstid] = innodes
    _emit.object_changed(dstid, source)

def edge_delete(edge_id, source="model"):
    edge = _get_edge(edge_id)
    relation_id = edge.relation_id
    relation = _get_relation(relation_id)
    srcid = edge.src_id
    dstid = edge.dst_id

    _edge_disconnect(relation, srcid, dstid, source)
    if not relation.directed:
        _edge_disconnect(relation, dstid, srcid, source)
    _edge_update_forest(relation_id, srcid)
    _edge_update_forest(relation_id, dstid)

    _emit.edge_deleted(edge_id, source)
    try:
        lang.eval(lang.read(relation.on_delete))(edge_id)
    except Exception as e:
        log.error(e.message)
    __type_id_map[Edge].remove(edge_id)
    del __id_entity_map[edge_id]

def _edge_disconnect(relation, srcid, dstid, source):
    del relation.outnodes[srcid][dstid]
    if not relation.outnodes[srcid]:
        del relation.outnodes[srcid]
    _emit.object_changed(srcid, source)

    del relation.innodes[dstid][srcid]
    if not relation.innodes[dstid]:
        del relation.innodes[dstid]
    _emit.object_changed(dstid, source)

_get_edge = _make_type_getter(Edge)

def get_edges():
    return list(__type_id_map[Edge])

def edge_get_relation(edge_id):
    edge = _get_edge(edge_id)
    return edge.relation_id

def edge_get_source_object(edge_id):
    edge = _get_edge(edge_id)
    return edge.src_id

def edge_get_destination_object(edge_id):
    edge = _get_edge(edge_id)
    return edge.dst_id

def edge_is_visible(edge_id):
    edge = _get_edge(edge_id)
    return edge.is_visible()

def edge_get_color(edge_id):
    edge = _get_edge(edge_id)
    return relation_get_color(edge.relation_id)

# Object Filters

class ObjectFilter(object, metaclass=TypeRepr):
    def __init__(self, id, name, code, predicate):
        self.id = id
        self.name = name
        self.code = code
        self.predicate = predicate

    def to_dict(self):
        return {
            "type": ObjectFilter,
            "id": self.id,
            "name": self.name,
            "code": self.code,
        }
    
    @staticmethod
    def from_dict(d):
        predicate = lang.eval(lang.read(d["code"]))
        edge = ObjectFilter(d["id"], d["name"], d["code"], predicate)
        return edge

def object_filter_new(title, code, source="model"):
    filter_id = make_id()
    predicate = lang.eval(lang.read(code))
    filter = ObjectFilter(filter_id, title, code, predicate)
    __id_entity_map[filter_id] = filter
    __type_id_map[ObjectFilter].add(filter_id)
    _emit.object_filter_created(filter_id, source)
    return filter_id

_get_object_filter = _make_type_getter(ObjectFilter)

def object_filter_delete(object_filter_id, source="model"):
    _emit.object_filter_deleted(object_filter_id, source)
    __type_id_map[ObjectFilter].remove(object_filter_id)
    del __id_entity_map[object_filter_id]

def object_filter_get_name(object_filter_id):
    filter = _get_object_filter(object_filter_id)
    return filter.name

def object_filter_get_predicate(object_filter_id):
    filter = _get_object_filter(object_filter_id)
    return filter.predicate

def get_object_filters():
    return list(__type_id_map[ObjectFilter])

# Event Handling
#
# Make a Delegate class with object_created, object_changed, object_deleted,
# etc. methods. Then make a SuperDelegate class with the same methods which
# forwards the calls to each of a set of Delegates.

def _event_handler(self, id, source):
    pass
def _reload_handler(self, source):
    pass
_object_types = ["object", "class", "relation", "edge", "object_filter"]
_event_types = ["created", "changed", "deleted"]
_event_handler_names = ["{0}_{1}".format(e[0], e[1]) for e in itertools.product(_object_types, _event_types)]
_event_handler_map = {name : _event_handler for name in _event_handler_names}
_event_handler_map["reload"] = _reload_handler
Delegate = type("Delegate", (), _event_handler_map)

def _super_delegate_init(self, delegates):
    Delegate.__init__(self)
    self.delegates = delegates

def _make_super_delegate_handler(method_name):
    def handler(self, id, source):
        for delegate in list(self.delegates):
            getattr(delegate, method_name)(id, source)
    return handler
def _reload_super_delegate_handler(self, source):
    for delegate in list(self.delegates):
        delegate.reload(source)
_event_handler_map = {e : _make_super_delegate_handler(e) for e in _event_handler_names}
_event_handler_map["reload"] = _reload_super_delegate_handler
_event_handler_map["__init__"] = _super_delegate_init
__SuperDelegate = type("__SuperDelegate", (Delegate,), _event_handler_map)

__delegates = set()
_emit = __SuperDelegate(__delegates)

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
    ObjectFilter: set(),
    Field: set(),
    Member: set(),
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
        Field: field_delete,
        ObjectFilter: object_filter_delete,
    }
    assert entity_type in type_delete_map
    type_delete_map[entity_type](entity_id)

def reset():
    for type, v in __type_id_map.items():
        if type == Member:
            continue
        for entity_id in list(v):
            delete(entity_id)
    for type, v in __type_id_map.items():
        assert len(v) == 0
    assert len(__id_entity_map) == 0

# Types

class Integer(object, metaclass=TypeRepr):
    initial_value = 0
    is_valid = lambda value: type(value) == int
    convert = lambda value: int(value)

class Float(object, metaclass=TypeRepr):
    initial_value = 0.0
    is_valid = lambda value: type(value) == float
    convert = lambda value: float(value)

class String(object, metaclass=TypeRepr):
    initial_value = ""
    is_valid = lambda value: type(value) == str
    convert = lambda value: str(value)

class Bool(object, metaclass=TypeRepr):
    initial_value = False
    is_valid = lambda value: type(value) == bool
    convert = lambda value: bool(value)

# Saving and Loading

def _model():
    return {
        "version": "0.1.0",
        "id_entity_map": {id: object.to_dict() for id, object in __id_entity_map.items()},
        "type_id_map": dict(__type_id_map),
    }

def write(file):
    file.write(repr(_model()))

def read(file):
    data = eval(file.read())
    # TODO: Switch on data version
    reset()
    global __id_entity_map
    __id_entity_map = {id: o['type'].from_dict(o) for id, o in data["id_entity_map"].items()}
    global __type_id_map
    __type_id_map = data["type_id_map"]
    _emit.reload("model")