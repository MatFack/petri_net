
import wx
import igraph
import util.vector_2d as vec2d
import util.constants as constants
from objects_canvas.objects_canvas import ObjectsCanvas
from objects_canvas.object_mixins import PositionMixin, SelectionMixin

class Edge(PositionMixin, SelectionMixin):
    def __init__(self, v1, v2, label=None):
        super(Edge, self).__init__()
        self.v1 = v1
        self.v2 = v2
        self.labels = []
        if label is not None:
            self.add_label(label)
        
    def add_label(self, label):
        self.labels.append(label)
        
    def is_selectable(self):
        return False
    
    def get_position(self):
        return self.v1.get_position()
        
    def draw(self, dc, zoom):
        fx, fy = self.v1.get_position()
        tx, ty = self.v2.get_position()
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawLine(fx, fy, tx, ty)
        
    def contains_point(self, x, y):
        return False
    
    def in_rect(self, lx, ly, tx, ty):
        return False
        
class Vertex(PositionMixin, SelectionMixin):
    def __init__(self, unique_id):
        super(Vertex, self).__init__()
        self.unique_id = unique_id
        self.radius = 20
        self.edges_from = {}
        self.edges_to = {}
        
    def draw(self, dc, zoom):
        x, y = self.get_position()
        dc.SetBrush(wx.WHITE_BRUSH)
        if self.is_selected:
            dc.SetPen(constants.BLUE_PEN)
        else:
            dc.SetPen(wx.BLACK_PEN)
        dc.DrawCircle(x, y, self.radius)
        
    def in_rect(self, lx, ly, tx, ty):
        r = self.radius
        bounding_rect = (self.pos_x-r, self.pos_y-r, self.pos_x+r, self.pos_y+r)
        return vec2d.rectangles_intersect(bounding_rect, (lx, ly, tx, ty))

        
    def contains_point(self, x, y):
        pos_x, pos_y = self.get_position()
        return (x - pos_x)**2 + (y - pos_y)**2 <= self.radius**2
    

class Graph(object):
    def __init__(self):
        self.vertices = {}
        self.__vertices_cache = None
    
    def vertices_changed(self):
        self.__vertices_cache = None
    
    def add_vertex(self, vertex):
        assert vertex.unique_id not in self.vertices
        self.vertices[vertex.unique_id] = vertex
        self.vertices_changed()
        
    def add_edge(self, fr, to, label):
        fr = self.vertices[fr]
        to = self.vertices[to]
        edge = to.edges_from.get(fr, None)
        if edge is None:
            edge = Edge(fr, to)
            to.edges_from[fr] = edge
            fr.edges_to[to] = edge
        edge.add_label(label)
                
    def get_vertices(self):
        if self.__vertices_cache is None:
            self.__vertices_cache = self.vertices.values()
        return self.__vertices_cache
    
    
    
    def automatic_layout(self):
        objects = {}
        for vertex in self.get_vertices():
            objects[vertex] = len(objects)
        graph = igraph.Graph(directed=True)
        graph.add_vertices(len(objects))
        for vertex in self.get_vertices():
            v1_n = objects[vertex]
            for edge in vertex.edges_from.itervalues():
                v2_n = objects[edge.v1]
                graph.add_edge(v1_n, v2_n)
        objects_lst = [None]*len(objects)
        if not objects_lst:
            return
        for obj, i in objects.iteritems():
            objects_lst[i] = obj
        layout = graph.layout_auto()
        v1_n = v2_n = None
        max_dist = 0
        for vertex in self.get_vertices():
            v1_n = objects[vertex]
            for edge in vertex.edges_from.itervalues():
                v2_n = objects[edge.v1]
                x1, y1 = layout[v1_n]
                x2, y2 = layout[v2_n]
                dist = ( (x1-x2)**2 + (y1-y2)**2 )**0.5
                if max_dist<dist:
                    max_dist = dist
            
        bbox = layout.bounding_box()
        layout.translate((-bbox.left, -bbox.top))
        if dist!=0:
            layout.scale(150/dist)
        for obj, pos in zip(objects_lst, layout):
            x,y = pos
            obj.set_position(x+constants.RIGHT_OFFSET*3,y+constants.BOTTOM_OFFSET*3)

    

class GraphPanel(ObjectsCanvas):
    def __init__(self, parent , frame, **kwargs):
        self.graph = Graph()
        super(GraphPanel, self).__init__(parent, frame=frame, **kwargs)
        self.SetName("Reachability graph")
        
    def __graph_get(self):
        return self.objects_container
    
    def __graph_set(self, value):
        self.objects_container = value
        
    def set_graph(self, states, names):
        self.graph = Graph()
        print names
        for state in states:
            print "Adding", state, names[state]
            vertex = Vertex(names[state])
            self.graph.add_vertex(vertex)
        for state, neighbours in states.iteritems():
            state_name = names[state]
            for edge_label, state_to in neighbours.iteritems():
                state_to_name = names[state_to]
                self.graph.add_edge(state_name, state_to_name, edge_label)
        self.graph.automatic_layout()
        self.Refresh()
        
    petri = property(fget=__graph_get, fset=__graph_set)
    
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