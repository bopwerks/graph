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

@with_setup(teardown=model.reset)
def test_object_get_innodes():
    class_id = model.class_new("Test Class")
    object_id1 = model.object_new(class_id)
    object_id2 = model.object_new(class_id)
    relation_id = model.relation_new("Test Relation")
    edge_id = model.edge_new(relation_id, object_id1, object_id2)
    innode_ids = model.object_get_innodes(object_id2, relation_id)
    assert [object_id1] == innode_ids

@with_setup(teardown=model.reset)
def test_object_get_outnodes():
    class_id = model.class_new("Test Class")
    object_id1 = model.object_new(class_id)
    object_id2 = model.object_new(class_id)
    relation_id = model.relation_new("Test Relation")
    edge_id = model.edge_new(relation_id, object_id1, object_id2)
    innode_ids = model.object_get_outnodes(object_id1, relation_id)
    assert [object_id2] == innode_ids

@with_setup(teardown=model.reset)
def test_object_get_edges():
    class_id = model.class_new("Test Class")
    object_id1 = model.object_new(class_id)
    object_id2 = model.object_new(class_id)
    relation_id = model.relation_new("Test Relation")
    edge_id = model.edge_new(relation_id, object_id1, object_id2)
    edge_ids = model.object_get_edges(object_id1, relation_id)
    assert set([edge_id]) == edge_ids

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

@with_setup(teardown=model.reset)
def test_relation_get_edges():
    class_id = model.class_new("Test Class")
    object_id1 = model.object_new(class_id)
    object_id2 = model.object_new(class_id)
    relation_id = model.relation_new("Test Relation")
    edge_id = model.edge_new(relation_id, object_id1, object_id2)
    edge_ids = model.relation_get_edges(relation_id)
    assert set([edge_id]) == edge_ids

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

# Fields

@with_setup(teardown=model.reset)
def test_new_class_has_no_fields():
    class_id = model.class_new("Test Class")
    field_ids = model.class_get_fields(class_id)
    assert [] == field_ids

@with_setup(teardown=model.reset)
def test_no_field_class_has_instances_with_no_members():
    class_id = model.class_new("Test Class")
    object_id = model.object_new(class_id)
    member_ids = model.object_get_members(object_id)
    assert [] == member_ids

@with_setup(teardown=model.reset)
def test_class_add_int_field_adds_one_field_id():
    class_id = model.class_new("Test Class")
    field_id = model.class_add_field(class_id, "Test Field", model.Integer)
    field_ids = model.class_get_fields(class_id)
    assert [field_id] == field_ids

@with_setup(teardown=model.reset)
def test_class_delete_field():
    class_id = model.class_new("Test Class")
    field_id = model.class_add_field(class_id, "Test Field", model.Integer)
    model.field_delete(field_id)
    field_ids = model.class_get_fields(class_id)
    assert [] == field_ids

@with_setup(teardown=model.reset)
def test_added_field_present_in_object_instance():
    class_id = model.class_new("Test Class")
    expected_field_id = model.class_add_field(class_id, "Test Field", model.Integer)
    object_id = model.object_new(class_id)
    member_ids = model.object_get_members(object_id)
    assert len(member_ids) == 1
    member_id = member_ids[0]
    actual_field_id = model.member_get_field(member_id)
    assert actual_field_id == expected_field_id

@with_setup(teardown=model.reset)
def test_field_added_after_object_created_is_present_in_object():
    class_id = model.class_new("Test Class")
    object_id = model.object_new(class_id)
    expected_field_id = model.class_add_field(class_id, "Test Field", model.Integer)
    member_ids = model.object_get_members(object_id)
    assert len(member_ids) == 1
    member_id = member_ids[0]
    actual_field_id = model.member_get_field(member_id)
    assert actual_field_id == expected_field_id

@with_setup(teardown=model.reset)
def test_field_removed_after_object_created_is_removed_from_object():
    class_id = model.class_new("Test Class")
    field_id = model.class_add_field(class_id, "Test Field", model.Integer)
    object_id = model.object_new(class_id)
    model.field_delete(field_id)
    assert [] == model.object_get_members(object_id)
