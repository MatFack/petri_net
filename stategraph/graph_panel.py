
import wx
from objects_canvas.objects_canvas import ObjectsCanvas
from graph import Graph, Vertex

    

class GraphPanel(ObjectsCanvas):
    def __init__(self, parent , frame, **kwargs):
        self.graph = Graph()
        super(GraphPanel, self).__init__(parent, frame=frame, **kwargs)
        self.SetName("Reachability graph")
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        
    def OnKeyDown(self, event):
        if not self.process_key(event):
            event.Skip()
        
    def process_key(self, event):
        print event.ShiftDown()
        print event.KeyCode,ord('A'),ord('a')
        if not event.ShiftDown():
            return False
        if event.KeyCode == ord('Z'):
            self.undo()
        elif event.KeyCode == ord('Y'):
            self.redo()
        elif event.KeyCode == ord('A'):
            self.select_all()
        elif event.KeyCode == ord('+'):
            self.zoom_in()
        elif event.KeyCode == ord('-'):
            self.zoom_out()
        elif event.KeyCode == ord('R'):
            self.zoom_restore()
        else:
            return False
        return True

    def __graph_get(self):
        return self.objects_container
    
    def __graph_set(self, value):
        self.objects_container = value
        
    def set_graph(self, states, names):
        self.graph = Graph()
        print names
        for state in states:
            vertex = Vertex(names[state], state)
            self.graph.add_vertex(vertex)
        for state, neighbours in states.iteritems():
            state_name = names[state]
            for edge_label, state_to in neighbours.iteritems():
                state_to_name = names[state_to]
                self.graph.add_edge(state_name, state_to_name, edge_label)
        self.graph.automatic_layout()
        self.update_bounds()
        self.Refresh()
        
    petri = property(fget=__graph_get, fset=__graph_set)
    
    def set_temporary_state(self, marking):
        self.frame.set_temporary_state(marking)
    
    def get_selection(self):
        return self.strategy.selection
    
    def select_states(self, states):
        self.strategy.discard_selection()
        self.strategy.add_to_selection(*[self.graph.vertices[state] for state in states])
        self.Refresh()
        
    
    def get_objects_iter(self):
        for vertex in self.graph.get_vertices():
            for edge in vertex.edges_from.itervalues():
                yield edge
        for vertex in self.graph.get_vertices():
            yield vertex
        
    def get_objects_reversed_iter(self):
        for vertex in reversed(self.graph.get_vertices()):
            for edge in vertex.edges_from.itervalues():
                yield edge # we don't care, edges won't be clickable
            yield vertex