import event
import random

class Node(event.Emitter):
    def __init__(self, title="", urgent=True, important=True, id=0, innodes=0, outnodes=0):
        self.id = id
        self._title = title
        self._urgentp = urgent
        self._importantp = important
        self._innodes = innodes
        self._outnodes = outnodes
        self._listeners = set()

    def __repr__(self):
        return str(self)

    def __str__(self):
        return ("Node(" +
                "title={0}, " +
                "urgent={1}, " +
                "important={2}, " +
                "id={3}, " +
                "innodes={4}, " +
                "outnodes={5})").format(repr(self._title),
                                        repr(self._urgentp),
                                        repr(self._importantp),
                                        repr(self.id),
                                        repr(self._innodes),
                                        repr(self._outnodes))

    def setUrgent(self, urgentp):
        self._urgentp = urgentp
        self.emit()

    def urgent(self):
        return self._urgentp

    def setImportant(self, importantp):
        self._importantp = importantp
        self.emit()

    def important(self):
        return self._importantp

    def id(self):
        return self._id

    def title(self):
        return self._title

    def setTitle(self, title):
        self._title = title
        self.emit()

    def addInnode(self):
        self._innodes += 1
        self.emit()

    def removeInnode(self):
        self._innodes -= 1
        assert self._innodes >= 0
        self.emit()
        
    def innodes(self):
        return self._innodes

    def addOutnode(self):
        self._outnodes += 1
        self.emit()

    def removeOutnode(self):
        self._outnodes -= 1
        assert self._outnodes >= 0
        self.emit()
        
    def outnodes(self):
        return self._outnodes

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
    
    def __repr__(self):
        return "Class({0}, {1})".format(repr(self.name), ', '.join(map(repr, self.fields))) 

class Object(event.Emitter):
    def __init__(self, klass, *values):
        super().__init__()
        self.id = make_id()
        self.klass = klass
        self.fields = []
        for i, field in enumerate(klass.fields):
            if i >= len(values):
                self.fields.append(field.initial_value)
            else:
                value = values[i]
                assert type(value) == field.type, "Expected {0}, got {1}".format(field.type, type(value))
                self.fields.append(value)

    def __repr__(self):
        return "Object({0}, {1})".format(repr(self.klass), ', '.join(map(repr, self.fields)))

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

class collection(list, event.Emitter):
    def __init__(self):
        list.__init__(self)
        event.Emitter.__init__(self)
    
    def append(self, object):
        super().append(object)
        self.emit("object_created", object.id)
        object.add_listener("object_changed", self._object_changed)
    
    def remove(self, object):
        super().remove(object)
        self.emit("object_deleted", object.id)
    
    def _object_changed(self, object_id):
        self.emit("object_changed", object_id)

classes = collection()
objects = collection()
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
        Field("Color", color, color.random())
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
    return object.id

def get_object(object_id):
    return find_by_id("object", objects, object_id)

def delete_object(object_id):
    # TODO: Remove all relations involving this object
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
