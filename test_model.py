from nose.tools import *
import model

class EventChain(object):
    def __init__(self, events):
        self.events = events
        self.i = 0
    
    def object_created(self, id):
        assert self.events[self.i] == ("object_created", id)
        self.i += 1
        return self

    def object_changed(self, id):
        assert self.events[self.i] == ("object_changed", id)
        self.i += 1
        return self

    def object_deleted(self, id):
        assert self.events[self.i] == ("object_deleted", id)
        self.i += 1
        return self

    def class_created(self, id):
        assert self.events[self.i] == ("class_created", id)
        self.i += 1
        return self

    def class_changed(self, id):
        assert self.events[self.i] == ("class_changed", id)
        self.i += 1
        return self

    def class_deleted(self, id):
        assert self.events[self.i] == ("class_deleted", id)
        self.i += 1
        return self

    def relation_created(self, id):
        assert self.events[self.i] == ("relation_created", id)
        self.i += 1
        return self

    def relation_changed(self, id):
        assert self.events[self.i] == ("relation_changed", id)
        self.i += 1
        return self

    def relation_deleted(self, id):
        assert self.events[self.i] == ("relation_deleted", id)
        self.i += 1
        return self

    def edge_created(self, id):
        assert self.events[self.i] == ("edge_created", id)
        self.i += 1
        return self

    def edge_changed(self, id):
        assert self.events[self.i] == ("edge_changed", id)
        self.i += 1
        return self

    def edge_deleted(self, id):
        assert self.events[self.i] == ("edge_deleted", id)
        self.i += 1
        return self
    
    def end(self):
        assert self.i == len(self.events)
        return self

class TestDelegate(model.Delegate):
    def __init__(self):
        self._events = []
    
    def events(self):
        return EventChain(self._events)
    
    def object_created(self, id):
        self._events.append(("object_created", id))

    def object_changed(self, id):
        self._events.append(("object_changed", id))

    def object_deleted(self, id):
        self._events.append(("object_deleted", id))

    def class_created(self, id):
        self._events.append(("class_created", id))

    def class_changed(self, id):
        self._events.append(("class_changed", id))

    def class_deleted(self, id):
        self._events.append(("class_deleted", id))

    def relation_created(self, id):
        self._events.append(("relation_created", id))

    def relation_changed(self, id):
        self._events.append(("relation_changed", id))

    def relation_deleted(self, id):
        self._events.append(("relation_deleted", id))

    def edge_created(self, id):
        self._events.append(("edge_created", id))

    def edge_changed(self, id):
        self._events.append(("edge_changed", id))

    def edge_deleted(self, id):
        self.events.append(("edge_deleted", id))

# Initialization

@with_setup(teardown=model.reset)
def test_model_initially_has_no_classes():
    classes = model.get_classes()
    assert [] == classes

@with_setup(teardown=model.reset)
def test_model_initially_has_no_edges():
    edges = model.get_edges()
    assert [] == edges

@with_setup(teardown=model.reset)
def test_model_initially_has_no_objects():
    objects = model.get_objects()
    assert [] == objects

@with_setup(teardown=model.reset)
def test_model_initially_has_no_relations():
    relations = model.get_relations()
    assert [] == relations

# Classes

@with_setup(teardown=model.reset)
def test_class_new_updates_class_list():
    class_id = model.class_new("Test")
    classes = model.get_classes()
    assert [class_id] == classes

@with_setup(teardown=model.reset)
def test_class_delete_updates_class_list():
    class_id = model.class_new("Test")
    model.class_delete(class_id)
    classes = model.get_classes()
    assert [] == classes

@with_setup(teardown=model.reset)
def test_class_delete_deletes_instances():
    class_id = model.class_new("Test")
    object_id = model.object_new(class_id)
    model.class_delete(class_id)
    objects = model.get_objects()
    assert [] == objects

# Objects

@with_setup(teardown=model.reset)
def test_object_new_updates_object_list():
    class_id = model.class_new("Test Class")
    object_id = model.object_new(class_id)
    objects = model.get_objects()
    assert [object_id] == objects

@with_setup(teardown=model.reset)
def test_object_delete_updates_object_list():
    class_id = model.class_new("Test Class")
    object_id = model.object_new(class_id)
    model.object_delete(object_id)
    objects = model.get_objects()
    assert [] == objects

# Relations

@with_setup(teardown=model.reset)
def test_relation_new_updates_relation_list():
    relation_id = model.relation_new("Test Relation")
    relations = model.get_relations()
    assert [relation_id] == relations

@with_setup(teardown=model.reset)
def test_relation_delete_updates_relation_list():
    relation_id = model.relation_new("Test Relation")
    model.relation_delete(relation_id)
    relations = model.get_relations()
    assert [] == relations

# Edges

@with_setup(teardown=model.reset)
def test_edge_new_updates_edge_list():
    class_id = model.class_new("Test Class")
    relation_id = model.relation_new("Test Relation")
    object_id1 = model.object_new(class_id)
    object_id2 = model.object_new(class_id)
    edge_id = model.edge_new(relation_id, object_id1, object_id2)
    edges = model.get_edges()
    assert [edge_id] == edges

@with_setup(teardown=model.reset)
def test_edge_delete_updates_edge_list():
    class_id = model.class_new("Test Class")
    relation_id = model.relation_new("Test Relation")
    object_id1 = model.object_new(class_id)
    object_id2 = model.object_new(class_id)
    edge_id = model.edge_new(relation_id, object_id1, object_id2)
    model.edge_delete(edge_id)
    edges = model.get_edges()
    assert [] == edges
