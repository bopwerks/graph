import event
import random

_id = 0
def make_id():
    global _id
    _id += 1
    return _id

class Relation(event.Emitter):
    def __init__(self, name, color=None, symmetric=False, transitive=True):
        super().__init__()
        self.id = make_id()
        self.name = name
        self.color = color
        self.symmetric = symmetric
        self.transitive = transitive
        self._max_innodes = -1
        self._max_outnodes = -1
        self.visible = True
        self._innodes = {}
        self._outnodes = {}

    def path(self, srcid, dstid):
        # TODO: Find a path from srcid to dstid
        pass

    def connect(self, srcid, dstid):
        if srcid not in self._outnodes:
            self._outnodes[srcid] = set()
        source_object = get_object(srcid)
        source_object.set_field("Outnodes", source_object.get_field("Outnodes") + 1)
        self._outnodes[srcid].add(dstid)
        
        if dstid not in self._innodes:
            self._innodes[dstid] = set()
        dest_object = get_object(dstid)
        dest_object.set_field("Innodes", dest_object.get_field("Innodes") + 1)
        self._innodes[dstid].add(srcid)

        # TODO: Restrict the relation to certain types of objects.
        return True

    def disconnect(self, srcid, dstid):
        self._outnodes[srcid].remove(dstid)
        if not self._outnodes[srcid]:
            del self._outnodes[srcid]
        source_object = get_object(srcid)
        source_object.set_field("Outnodes", source_object.get_field("Outnodes") - 1)
        self._innodes[dstid].remove(srcid)
        if not self._innodes[dstid]:
            del self._innodes[dstid]
        dest_object = get_object(dstid)
        dest_object.set_field("Innodes", dest_object.get_field("Innodes") - 1)

    def clear(self):
        # Decrement innodes and outnodes of all related objects
        for outnodes in self._outnodes.values():
            for outnode in outnodes:
                outnode.set_field("Innodes", outnode.get_field("Innodes") - 1)
        for innodes in self._innodes.values():
            for innode in innodes:
                innode.set_field("Outnodes", innode.get_field("Outnodes") - 1)
        self._innodes = {}
        self._outnodes = {}

class Field(object):
    def __init__(self, name, type, initial_value):
        self.name = name
        self.type = type
        self.initial_value = initial_value

    def __repr__(self):
        return "Field({0}, {1}, {2})".format(repr(self.name), repr(self.type), repr(self.initial_value))

class Class(event.Emitter):
    def __init__(self, name, *fields):
        super().__init__()
        self.id = make_id()
        self.name = name
        self.fields = fields
        self.visible = True
    
    def set_visible(self, is_visible):
        self.visible = is_visible
        self.emit("class_changed", self.id)
    
    def __repr__(self):
        return "Class({0})".format(repr(self.name))
        # return "Class({0}, {1})".format(repr(self.name), ', '.join(map(repr, self.fields))) 

class Object(event.Emitter):
    def __init__(self, klass, *values):
        super().__init__()
        self.id = make_id()
        self.klass = klass
        self.fields = []
        self.tags = set()
        for i, field in enumerate(klass.fields):
            if i >= len(values):
                self.fields.append(field.initial_value)
            else:
                value = values[i]
                assert type(value) == field.type, "Expected {0}, got {1}".format(field.type, type(value))
                self.fields.append(value)

    def __repr__(self):
        return "Object({0})".format(repr(self.get_field("Title")))
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
                self.emit("object_changed", self.id)
    
    def _class_changed(self, class_id):
        # TODO: Update fields
        klass = get_class(class_id)
        self.set_field("Visible", klass.visible)

class collection(list, event.Emitter):
    def __init__(self):
        list.__init__(self)
        event.Emitter.__init__(self)
    
    def append(self, object):
        super().append(object)
        self.emit("object_created", object.id)
        object.add_listener("object_changed", self._object_changed)
    
    def remove(self, object):
        object.remove_listener("object_changed", self._object_changed)
        super().remove(object)
        self.emit("object_deleted", object.id)
    
    def _object_changed(self, object_id):
        self.emit("object_changed", object_id)

def _iter_objects(object_sets):
    for object_set in object_sets:
        for object in object_set:
            yield object

class collection_map(event.Emitter):
    def __init__(self):
        super().__init__()
        self._objects = {}
    
    def append(self, object):
        class_id = object.klass.id
        if class_id not in self._objects:
            self._objects[class_id] = set()
        self._objects[class_id].add(object)
        self.emit("object_created", object.id)
        object.add_listener("object_changed", self._object_changed)
    
    def remove(self, object):
        class_id = object.klass.id
        assert class_id in self._objects
        self._objects[class_id].remove(object)
        object.remove_listener("object_changed", self._object_changed)
        self.emit("object_deleted", object.id)
    
    def _object_changed(self, object_id):
        self.emit("object_changed", object_id)
    
    def by_class(self, class_id):
        return iter(self._objects.get(class_id, []))

    def __iter__(self):
        return _iter_objects(self._objects.values())

class Tag(object):
    def __init__(self, name, parent=None):
        self.id = make_id()
        self.name = name
        self.visible = True
        if parent:
            parent.add_child(self)
        self.children = set()

    def add_child(self, tag):
        tag.parent = self
        self.children.add(tag)

    def remove_child(self, tag):
        tag.parent = None
        self.children.remove(tag)
    
    def objects(self):
        pass


classes = collection()
objects = collection_map()
relations = collection()

def find_by_id(type, list, id):
    matches = [o for o in list if o.id == id]
    assert len(matches) == 1, "Can't find {0} with id {1}".format(type, id)
    return matches[0]

def make_class(name, *custom_fields):
    default_fields = [
        Field("Title", str, ""),
        Field("Innodes", int, 0),
        Field("Outnodes", int, 0),
        Field("Color", color, color.random()),
        Field("Visible", bool, True)
    ]
    klass = Class(name, *default_fields, *custom_fields)
    classes.append(klass)
    return klass.id

def get_class(class_id):
    return find_by_id("class", classes, class_id)

def delete_class(class_id):
    klass = get_class(class_id)
    objects = [o for o in objects if o.klass == klass]
    for object in objects:
        delete_object(object)
    classes.remove(klass)

def make_object(class_id, *values):
    klass = get_class(class_id)
    object = Object(klass, *values)
    objects.append(object)
    klass.add_listener("class_changed", object._class_changed)
    return object.id

def object_has_tag(object_id, tag_id):
    object = get_object(object_id)
    return tag_id in object.tags

def object_add_tag(object_id, tag_id):
    object = get_object(object_id)
    object.tags.add(tag_id)

def get_objects_by_class(class_id):
    return objects.by_class(class_id)

def get_object(object_id):
    return find_by_id("object", objects, object_id)

def delete_object(object_id):
    # TODO: Remove all relations involving this object
    object = get_object(object_id)
    klass = object.klass
    klass.remove_listener("class_changed", object._class_changed)
    objects.remove(get_object(object_id))

def make_relation(name):
    relation = Relation(name)
    relations.append(relation)
    return relation.id

def get_relation(relation_id):
    return find_by_id("relation", relations, relation_id)

def delete_relation(relation_id):
    relation = get_relation(relation_id)
    relation.clear()
    relations.remove(get_relation(relation_id))

def connect(relation_id, *object_ids):
    relation = get_relation(relation_id)
    relation.connect(*object_ids)

def disconnect(relation_id, *object_ids):
    relation = get_relation(relation_id)
    relation.disconnect(*object_ids)

class color(object):
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b
    
    @staticmethod
    def random():
        rand = lambda: random.randint(0, 255)
        return color(rand(), rand(), rand())

goal_class = make_class("Goal")
# goal1 = make_object(goal_class, "Be healthy")

task_class = make_class(
    "Task",
    Field("Urgent", bool, False),
    Field("Important", bool, False)
)
# task1 = make_object(task_class, "Exercise")
precedes = make_relation("precedes")
# task2 = make_object(task_class, "Eat Right")
# connect(precedes, task1, task2)
# connect(precedes, task2, goal1)

# tag_class = make_class("Tag")
# tag1 = make_object(tag_class, "health")
# tag2 = make_object(tag_class, "exercise")
# is_child_of = make_relation("is a child of")
# connect(is_child_of, tag2, tag1)

# is_tagged_by = make_relation("tags")
# connect(is_tagged_by, goal1, tag1)

# connect(is_tagged_by, task1, tag2)
# connect(is_tagged_by, task2, tag1)

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

def tagged_with(tag_name):
    # Find tag with name
    matches = [o for o in objects if o.klass.id == tag_class and o.get_field("Title") == tag_name]
    assert len(matches) == 1
    tag_object = matches[0]
    return has_path_to(tag_object.id, is_child_of, is_tagged_by)

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

# filter1 = eq(field("Innodes"), const(0))
# for object in filter(filter1, objects):
#     print(object)

# filter2 = land(has_type(task_class), tagged_with("health"))
# for object in filter(filter2, objects):
#    print(object)

def get_object_tags(object_id):
    tag_relation = get_relation(is_tagged_by)
    return list(tag_relation._outnodes.get(object_id, []))

# for tag_id in get_object_tags(goal1):
#     print(get_object(tag_id))
