
import wx
import igraph
import util.vector_2d as vec2d
import util.drawing
import util.constants as constants
from objects_canvas.object_mixins import PositionMixin, SelectionMixin


class Edge(PositionMixin, SelectionMixin):
    def __init__(self, v1, v2, label=None):
        super(Edge, self).__init__()
        self.v1 = v1
        self.v2 = v2
        self.labels = []
        self.label_text = ''
        if label is not None:
            self.add_label(label)
        
    def add_label(self, label):
        self.labels.append(label)
        self.label_text = ','.join(self.labels)
        
    def is_selectable(self):
        return False
    
    def get_position(self):
        return self.v1.get_position()
        
    def draw(self, dc, zoom):
        fx, fy = self.v1.get_position()
        tx, ty = self.v2.get_position()
        dc.SetPen(wx.BLACK_PEN)
        # True if there is also and edge from v2 to v1
        double_directed = self.v1.edges_from.get(self.v2, None) is not None
        cx, cy = (fx+tx)/2, (fy+ty)/2
        angle = abs(vec2d.Vec2d(tx-fx, ty-fy).angle)
        if not double_directed:
            dc.DrawLine(fx, fy, tx, ty)
        else:
            perp_x, perp_y = -(ty-fy), tx-fx
            normal = (perp_x**2 + perp_y**2)**0.5
            if normal:
                perp_x /= normal
                perp_y /= normal
                cx+=perp_x*20
                cy+=perp_y*20
            else:
                cx+=30
                cy+=30  
            dc.DrawLine(fx, fy, cx, cy)          
            dc.DrawLine(cx, cy, tx, ty)
        fr, to = vec2d.Vec2d(cx, cy), vec2d.Vec2d(tx, ty)
        direction = to-fr
        to -= direction.normalized()*self.v2.radius
        util.drawing.draw_arrow(dc, fr, to, 15, 10)
        dc.DrawText(self.label_text, cx, cy)
        
        
    def contains_point(self, x, y):
        return False
    
    def in_rect(self, lx, ly, tx, ty):
        return False
        
class Vertex(PositionMixin, SelectionMixin):
    def __init__(self, unique_id, marking):
        super(Vertex, self).__init__()
        self.unique_id = unique_id
        self.marking = marking
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
        util.drawing.draw_text(dc, self.unique_id, x, y)
        
    def in_rect(self, lx, ly, tx, ty):
        r = self.radius
        bounding_rect = (self.pos_x-r, self.pos_y-r, self.pos_x+r, self.pos_y+r)
        return vec2d.rectangles_intersect(bounding_rect, (lx, ly, tx, ty))

        
    def contains_point(self, x, y):
        pos_x, pos_y = self.get_position()
        return (x - pos_x)**2 + (y - pos_y)**2 <= self.radius**2
    
    def open_properties_dialog(self, panel):
        panel.set_temporary_state(self.marking)


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
        if max_dist!=0:
            layout.scale(200/max_dist)
        for obj, pos in zip(objects_lst, layout):
            x,y = pos
            obj.set_position(x+constants.RIGHT_OFFSET*3,y+constants.BOTTOM_OFFSET*3)

if __name__ == '__main__':
    graph = Graph()
    
    graph.add_vertex(Vertex('a', (1,2)))
    graph.add_vertex(Vertex('b', (2,1)))
    
    graph.add_edge('a','b', 't1')
    
    