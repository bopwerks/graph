# todo

This is a to-do program that models to-do lists as directed graphs.

![A screenshot of the program](https://raw.githubusercontent.com/bopwerks/todo/master/screenshot.png)

Tasks are created by clicking the "new" button, filling in the task's title and priority, and positioning it in the network. Tasks are "completed" by selecting them and pressing the delete key. A task's title, and "urgent" and "important" checkboxes for prioritization, are edited by left-clicking the task. Arrows in the graph denote a "comes before" relationship between tasks, and are created by right-clicking and dragging an arrow from one task to another.

A panel summarizes the graph in the traditional list view, in priority order. Only "actionable" tasks -- tasks without arrows pointing to them -- are displayed. When a task is removed from the graph, the actionable tasks that follow from the completed task are added to the to-do list. This creates a sort of "self-generating" to-do list.
