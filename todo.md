# Todo App Todos

## Todo
* Add tags tree
  - have a normal class called "Tag"
  - allow classes to have Controls in addition to Fields
    - Controls might include checkboxes, buttons, listboxes, etc.
    - Controls can have code event handlers attached to them to do stuff
  - add widget to display relations in list or tree form depending on limitations of relation
    - widget displays controls of objects the relation relates
  - add checkbox control to Tag class whose code hides all objects tagged with that tag
    - code finds all objects with a path between them and the tag
    - calls (push-visibility target-object-id tag-id) to hide the object (object may already be hidden)
    - calls (pop-visibility target-object-id tag-id) to unhide the object (won't necessarily make it visible)
* Export graph to graphviz
* Add Image field to objects to customize image
* Add a tree view that shows goal structure and the actionable items under them

## Features

* As a user, I want to know which of my tasks are actionable.

  A plain todo list shows actionable tasks.

* As a user, I want to indicate that one task must precede another.

  Arrows between nodes indicate ordering.

* As a user, I want to capture all the things I could do to achieve a goal.

  Users can currently do this by just creating items.

* As a user, I want to toggle the visibility of tasks and goals that are actionable.

  Add checkboxes next to classes to toggle visibility like relations

* As a user, I want to toggle the visibility of tasks or goals that I'm unwilling to tackle right now.

  This can be achieved by allowing users to tag items as Someday/Maybe (or whatever tag name they choose). The user can then toggle the visibility of tagged items. By default the last tags can be used when creating an item.

* As a user, I want to see which goals I'm working toward by completing a given task.

  Add a tree view which shows goals and the next actionable item to achieve it. Allow the user to invert the tree, so goals can be parents or children depending on what's useful to the user.

* As a user, I want to see a plain todo list of actionable items sorted by priority.
* As a user, I want to search for all goals and tasks by name, priority, and/or tag.
* As a user, I want to toggle the visibility of goals and tasks with a given tag.
* As a user, I want to organize tags hierarchically, with child tags considered as subsets of their parents.
* As a user, I want to find friends or coworkers who are sharing todo lists online.
* As a user, I want to share my todo list online (i.e. make it visible to others).
* As a user, I want to restrict the tasks and goals which are visibible in my shared todo list.
* As a user, I want to package up common routines into a single node that I can drag from a node palette and drop onto my todo list.

* As a user, I want a palette of nodes to drag and drop (or double-click) onto my graph.

  This has now been added.

* As a user, I want my node palette to offer nodes for automating tasks.
* As a user, I want to specify a dependency between my task and the task of a person whose todo list I'm following.

## A

* Users can pan the graph canvas
* Users can create goal nodes in the graph
* Users can toggle "trace view" in their todo list to see which goals they're working to achieve
* Replace the node editor with a table-based view that allows for bulk updates
* Users can add custom text to a task in markdown
* Users can add a header image to a task or goal
* Users can assign an owner for a task
* Users can create self-contained routines for themselves. Add tab bar to view routines, and routine browser to display routines from which user can drag/drop onto their graph

### Requires Server Communication

* Users can set a profile picture and description
* Users can log in using a username and password
* Users see the graph as they left it when they return
* Users can change their passwords
* Users can recover their passwords
* Users can import other people's routines into their graphs
* Users can publish their routines to friends or the world
* Users can search for and browse published routines
* Users can see the graphs of people who have given them read access
* Users can cooperatively build the graph
* Advertisers can advertise according to the content of tasks

## Todo

* Users can select zero or more nodes for editing with shift and click
* Users can click and drag a rectangle to select zero or more nodes
* Users cannot draw more than one arrow from the same source to the same destination
* Users can press space to see all nodes at once
* Users cannot create cycles in their graphs
* Users can press Ctrl-A to select all nodes
* Users can undo node add/remove/move
* Users can undo edge add/remove
* Users can create task nodes in the graph
* Users can edit tasks individually or in bulk

## Done

* Users can select and delete edges between nodes
* Users can zoom the graph in and out
* Users can right-click to draw an arrow between two nodes
* Users can delete nodes by selecting and pressing <delete>

* Someday/Maybe

** B
*** Advertisers can promote routines in user browse and search results
*** Users can 'follow' routines so the routines they import are updated automatically
*** Users can add functionality-specific task nodes like "Skype Call" or "Email"
*** Users can comment on routines like in a reddit thread
*** Users can disable advertising for a recurring fee
*** Users can double-click nodes to toggle visibility of innodes
*** Users can integrate smart devices like Nest thermostats which are given responsibility for completing tasks
*** Users can integrate with the automation tool Zapier
*** Users can modify the graphs of people who have given them write access
*** Users can publish tasks or goals that they've completed to their profile
*** Users can list actionable goals by priority rather than tasks
*** Allow users to cmd-click window handles to automatically grow

** C
*** The algorithm which computes the edge of a node accounts for the rounded corners of the node
*** Users are given an indication that a node is draggable by a slight highlight around the node
*** Users can add text and images to a task in WYSIWYG mode
*** Users can automatically reposition nodes in the graph in a sensible way
*** Users can customize the method of prioritization for their tasks
*** Users can indicate that one of several paths can be taken to complete a goal by using an =or= node
*** Users can right-click nodes and edges to see a context-sensitive menu
*** Users can see drag/drop tasks and routines to a calendar display