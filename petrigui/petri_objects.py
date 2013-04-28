

import itertools

from objects_canvas.object_mixins import MenuMixin, SelectionMixin, PositionMixin
from object_label import ObjectLabel
import util.constants
from petri import petri
import wx
import collections
import util.vector_2d as vec2d
import util.drawing
from properties_dialog import ElementPropertiesDialog, DialogFields, place_ranged
from util import constants, serializable
from commands.create_delete_command import CreateDeleteObjectCommand


class GUIPlace(PositionMixin, SelectionMixin, petri.Place):
    pos_x_to_serialize = True
    pos_y_to_serialize = True
    radius_to_serialize = True
    
    def __init__(self, net, unique_id=None, tokens=0, position=None):
        """
        unique_id - unique identifier (hash if None)
        tokens - number of tokens in initial marking
        """
        super(GUIPlace, self).__init__(net=net, unique_id=unique_id, tokens=tokens)
        self.radius = 14
        self._tokens = tokens
        self.label = ObjectLabel(self, -self.radius, -self.radius)
        self.temporary_tokens = None
        if position:
            self.set_position(*position)
            
    def set_temporary_tokens(self, tokens):
        self.temporary_tokens = tokens
           
    def label_to_json_struct(self, **kwargs):
        return self.label.to_json_struct(**kwargs)
    
    def label_from_json_struct(self, label_obj, **kwargs):
        return ObjectLabel.from_json_struct(label_obj, constructor_args=dict(obj=self), **kwargs)
           
    def __get_tokens(self):
        if self.temporary_tokens is not None:
            return self.temporary_tokens
        return self._tokens
    
    def __set_tokens(self, value):
        self._tokens = value
        
    tokens = property(fget=__get_tokens, fset=__set_tokens)
           
    def draw(self, dc, zoom):
        if self.is_selected:
            dc.SetPen(constants.BLUE_PEN)
        else:
            dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawCircle(self.pos_x, self.pos_y, self.radius)
        tokens = self.tokens

        if isinstance(tokens, basestring) or tokens>4:
            if self.temporary_tokens is not None:
                dc.SetPen(constants.BLUE_PEN)
            else:
                dc.SetPen(wx.BLACK_PEN)
            util.drawing.draw_text(dc, str(tokens), self.pos_x, self.pos_y)
        elif tokens>0:
            self.draw_tokens(dc, tokens)    
            
    def get_topleft_position(self):
        x, y = self.get_position()
        return x-self.radius, y-self.radius
                
    def draw_tokens(self, dc, tokens):
        #This sucks, but who cares
        if self.temporary_tokens is not None:
            dc.SetBrush(wx.BLUE_BRUSH)
        else:
            dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        tokens_r = self.radius/3
        tokens_offset = self.radius/2.8
        if tokens==1:
            dc.DrawCircle(self.pos_x, self.pos_y, tokens_r)
        elif tokens==2:
            dc.DrawCircle(self.pos_x-tokens_offset, self.pos_y, tokens_r)
            dc.DrawCircle(self.pos_x + tokens_offset, self.pos_y, tokens_r)
        elif tokens==3:
            dc.DrawCircle(self.pos_x-tokens_offset, self.pos_y+tokens_r, tokens_r)
            dc.DrawCircle(self.pos_x + tokens_offset, self.pos_y+tokens_r, tokens_r)
            dc.DrawCircle(self.pos_x, self.pos_y-tokens_r, tokens_r)
        elif tokens==4:
            for x_diff in xrange(0,2):
                x_diff = (x_diff*2-1)*tokens_offset
                for y_diff in xrange(0,2):
                    y_diff = (y_diff*2-1)*tokens_offset
                    dc.DrawCircle(self.pos_x+x_diff, self.pos_y+y_diff, tokens_r)

        
    def contains_point(self, x, y):
        x_diff = self.pos_x - x
        y_diff = self.pos_y - y
        return x_diff**2 + y_diff**2 <= self.radius**2
    
    def in_rect(self, lx, ly, tx, ty):
        r = self.radius
        bounding_rect = (self.pos_x-r, self.pos_y-r, self.pos_x+r, self.pos_y+r)
        return vec2d.rectangles_intersect(bounding_rect, (lx, ly, tx, ty))
    
    def get_size(self):
        return self.radius, self.radius
    
    def get_begin(self, arc):
        pos = vec2d.Vec2d(self.get_position())
        vec = vec2d.Vec2d(arc.get_point_next_to(self)) - pos
        pos += vec.normalized()*self.radius
        return pos
    
    def get_end(self, arc):
        pos = vec2d.Vec2d(self.get_position())
        vec = vec2d.Vec2d(arc.get_point_next_to(self)) - pos
        pos += vec.normalized()*self.radius
        return pos
    
    
    
    def open_properties_dialog(self, parent):
        fields = [ ('unique_id', DialogFields.unique_id),
                   ('tokens', place_ranged('Tokens', minimum=0)),
                   ('radius', place_ranged('Radius', minimum=5))
                   ]
        dia = ElementPropertiesDialog(parent, -1, 'Place properties', obj=self, fields=fields)
        dia.ShowModal()
        dia.Destroy()      
        
    def check_update_unique_id(self, value):
        if not value:
            raise ValueError, "Place name can't be blank"
        if value in self.net.places:
            raise ValueError, "A place with such name already exists"
        
    def update_unique_id(self, value):
        self.net.rename_place(from_name=self.unique_id, to_name=value)
        
    def get_depending_objects(self):
        for arc in self.get_arcs():
            yield arc
        
class GUIArc(SelectionMixin, PositionMixin, MenuMixin, petri.Arc): #PositionMixin is just a stub
    
    INSERT_POINT = wx.NewId()
    REMOVE_POINT = wx.NewId()
    
    def __init__(self, net, place=None, transition=None, weight=1):
        super(GUIArc, self).__init__(net=net, place=place, transition=transition, weight=weight)
        self.tail_length = 10
        self.tail_angle = 15
        line_width = 2
        self.line_pen = wx.Pen(wx.BLACK, line_width)
        self.line_selected_pen = wx.Pen("Blue", line_width)
        self.begin = self.end = None
        self.points = []
        self.__points_to_be_added = []
        self.__points_selected = 0
        #
        self.menu_fields = collections.OrderedDict()
        self.menu_fields[GUIArc.INSERT_POINT] = ('Insert point', self.menu_insert_point)
        
    def __get_points_selected(self):
        return self.__points_selected
    
    def __set_points_selected(self, value):
        self.__points_selected = max(value, 0)
        
    points_selected = property(fget=__get_points_selected, fset=__set_points_selected)
        
    def points_to_json_struct(self, **kwargs):
        return [point.to_json_struct(**kwargs) for point in self.points]
    
    def points_from_json_struct(self, points_obj, **kwargs):
        points = []
        for point_obj in points_obj:
            arc_point = ArcPoint.from_json_struct(point_obj, constructor_args=dict(arc=self))
            points.append(arc_point)
        return points
    
    def get_position(self): #just a stub
        return self.place.get_position()
    
    def get_topleft_position(self):
        min_x, min_y = self.get_position()
        for point in self.points:
            x,y = point.get_position()
            if x < min_x: min_x = x
            if y < min_y: min_y = y
        return min_x, min_y
    
    def shift(self, dx, dy):
        for point in self.points:
            point.shift(dx, dy)
            
    def add_point(self, point_coords):
        point = ArcPoint(self)
        point.set_position(*point_coords)
        self.points.append(point)
        
    def remove_point(self, point):
        if point.is_selected:
            self.__points_selected -= 1
        self.points.remove(point)
        
    def remove_arc_points(self):
        self.points = []
        self.points_selected = 0
        
    def select_line_pen(self, dc):
        if self.is_selected:
            dc.SetPen(self.line_selected_pen)
        else:
            dc.SetPen(self.line_pen)        
            
    def draw(self, dc, zoom):
        self.select_line_pen(dc)
        fr = self.place
        to = self.transition
        if self.weight<0:
            fr, to = to, fr
        fr_begin = fr.get_begin(self)
        to_end = to.get_end(self)
        self.begin = fr_begin
        self.end = to_end
        for fr, to in self._iter_segments():
            self.draw_segment(dc, fr, to)
            fr_begin = fr
        fr_begin = vec2d.Vec2d(fr_begin)
        util.drawing.draw_arrow(dc, fr_begin, to_end, self.tail_angle, self.tail_length)
        if abs(self.weight)>1:
            self.draw_label(dc)
            
    def draw_label(self, dc):
        point, direction = self.get_center()
        label = str(abs(self.weight))
        label_x = point[0]
        label_y = point[1]
        tw,th = dc.GetTextExtent(label)
        label_vec_perp = direction.perpendicular_normal()*max(th,tw)*0.8
        util.drawing.draw_text(dc, label, label_x+label_vec_perp[0], label_y+label_vec_perp[1])
        
    def get_center(self):
        length = 0.
        for a,b in self._iter_segments():
            a, b = vec2d.Vec2d(a), vec2d.Vec2d(b)
            length += a.get_distance(b)
        new_length = 0
        half_length = length / 2.
        for a,b in self._iter_segments():
            a, b = vec2d.Vec2d(a), vec2d.Vec2d(b)
            dist = a.get_distance(b)
            new_length += dist
            if new_length > half_length:
                redundancy = new_length - half_length
                dist_proportion = (dist - redundancy) / dist
                resulting_vec = b - a
                return a + resulting_vec*dist_proportion, resulting_vec
                
    def draw_segment(self, dc, fr, to):
        x1, y1 = fr[0], fr[1]
        x2, y2 = to[0], to[1]
        self.select_line_pen(dc)
        dc.DrawLine(x1, y1, x2, y2)
                
    def get_point_next_to(self, obj):
        index = 0 if self.weight>0 else -1
        if obj==self.place:
            next_obj = self.points[index] if self.points else self.transition
        elif obj==self.transition:
            next_obj = self.points[-1-index] if self.points else self.place
        
        return next_obj.get_position()
    
    def set_point_at(self, point, index):
        if self.__points_to_be_added is None:
            self.__points_to_be_added = []
        self.__points_to_be_added.append((point, index))
        
    def contains_point(self, x, y):
        segment = self.get_segment_nearest_to_point(x, y, self.line_pen.GetWidth())
        return segment is not None
    
    def get_segment_nearest_to_point(self, x, y, maximum_distnace):
        """ Returns  (a,b) tuple, where a and b are points """
        if self.begin is None or self.end is None:
            return None
        for i, (fr, to) in enumerate(self._iter_segments()):
            x1, y1 = fr[0], fr[1]
            x2, y2 = to[0], to[1]
            distance = vec2d.dist(x1, y1, x2, y2, x, y)
            if distance <= maximum_distnace:
                return i, (fr, to)
        return None
    
    def restore_points(self):
        if self.__points_to_be_added is None:
            return
        for point, index in sorted(self.__points_to_be_added, key=lambda x:x[1]):
            self.points.insert(index, point)
        self.__points_to_be_added = None
    
    def _iter_points(self, include_first=True):
        """ Returns object that provide a[0] a[1], this generator returns vectors and tuples."""
        if include_first:
            yield self.begin
        for point in self.points:
            yield point.get_position()
        yield self.end
         
    def _iter_segments(self):
        for a,b in itertools.izip(self._iter_points(), self._iter_points(include_first=False)):
            yield a,b   
    
    def in_rect(self, lx, ly, tx, ty):
        for a,b in self._iter_segments():

            x1,y1 = a[0],a[1]
            x2,y2 = b[0],b[1]
            if vec2d.rectangle_intersects_line((x1,y1), (x2, y2), (lx, ly, tx, ty)):
                return True
        return False
    
    def __get_weight(self):
        return abs(self.weight)
    
    def __set_weight(self, value):
        if self.weight < 0:
            value = -value
        self.weight = value
        
    abs_weight = property(__get_weight, __set_weight)
    
    def open_properties_dialog(self, parent):
        fields = [ 
                   ('abs_weight', place_ranged('Weight', minimum=1))
                   ]
        self.menu_parent = parent 
        dia = ElementPropertiesDialog(parent, -1, 'Arc properties', obj=self, fields=fields)
        dia.ShowModal()
        dia.Destroy()      
         
    def menu_insert_point(self, event):
        x,y = self.menu_canvas_pos
        seg = self.get_segment_nearest_to_point(x, y, self.line_pen.GetWidth())
        if seg is None:
            return
        ind, (a,b) = seg
        arc_point = ArcPoint(self)
        arc_point.set_position(x, y)
        self.points.insert(ind, arc_point)
        strategy = self.menu_parent.strategy
        if strategy.can_select:
            strategy.discard_selection()
            strategy.add_to_selection(arc_point)
        command = CreateDeleteObjectCommand(self.menu_parent, arc_point)
        self.menu_parent.append_command(command)
        
    def get_depending_objects(self):
        return []
    

            
        
class ArcPoint(SelectionMixin, PositionMixin, serializable.Serializable):
    pos_x_to_serialize = True
    pos_y_to_serialize = True
    
    def __init__(self, arc):
        super(ArcPoint, self).__init__()
        self.arc = arc
        self.width = 7
        self.height = 7
        self.zoom = 1
        
    def get_rectangle(self):
        x,y = self.pos_x, self.pos_y
        w,h = self.width,self.height
        if self.zoom<1:
            w /= self.zoom
            h /= self.zoom
        return x-w/2,y-h/2,w,h
    
    def set_selected(self, selected):
        previous = self.is_selected
        super(ArcPoint, self).set_selected(selected)
        new = self.is_selected
        if new and not previous:
            self.arc.points_selected+=1
        elif previous and not new:
            self.arc.points_selected -=1
        
    def contains_point(self, x, y):
        r_x,r_y,r_w,r_h = self.get_rectangle()
        return (r_x <= x <= r_x+r_w) and (r_y <= y <= r_y+r_h)
    
    def in_rect(self, lx, ly, tx, ty):
        x, y, w, h = self.get_rectangle()
        return vec2d.rectangles_intersect((x, y, x+w, y+h), (lx, ly, tx, ty))
    
    def draw(self, dc, zoom):
        self.zoom = zoom
        if not self.arc.points_selected and not self.arc.is_selected:
            return 
        x, y, w, h = self.get_rectangle()
        if self.selected:
            dc.SetPen(constants.BLUE_PEN)
        else:
            dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(x, y, w, h)
        
    def shift(self, dx, dy):
        x, y = self.get_position()
        self.set_position(x+dx, y+dy)
        
    def get_size(self):
        return self.width/2, self.height/2
    
    def prepare_to_delete(self):
        self.index_in_arc = self.arc.points.index(self)
        
    def delete(self):
        self.arc.remove_point(self)
        
    def restore(self):
        self.arc.set_point_at(self, self.index_in_arc)
        
    def post_restore(self):
        self.arc.restore_points()
    
    
            
    def get_depending_objects(self):
        return []
        
        
class GUITransition(PositionMixin, SelectionMixin, MenuMixin, petri.Transition):
    ARC_CLS = GUIArc
    
    pos_x_to_serialize = True
    pos_y_to_serialize = True
    width_to_serialize = True
    height_to_serialize = True
    
    def __init__(self, unique_id=None, position=None, input_arcs=None, output_arcs=None, net=None):
        super(GUITransition,self).__init__(unique_id=unique_id, input_arcs=input_arcs, output_arcs=output_arcs, net=net)
        self.pos_x, self.pos_y = position or (0,0)
        self.width_coef = 0.9
        self.height_coef = 0.5
        self._width = self._height = 0
        self.width = 15
        self.height = 40
        
        self.side_slots = []
        self.main_angle = 90
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1), ]
        self.label = ObjectLabel(self, -self.width/2, -self.height/2)
        self.temporary_arc = None
        # Menu
        self.menu_fields = collections.OrderedDict()
        self.menu_fields[GUIArc.INSERT_POINT] = ('Rotate', self.menu_rotate)
        
        
    def label_to_json_struct(self, **kwargs):
        return self.label.to_json_struct(**kwargs)
    
    def label_from_json_struct(self, label_obj, **kwargs):
        return ObjectLabel.from_json_struct(label_obj, constructor_args=dict(obj=self), **kwargs)

        
    def __set_width(self, width):
        self._width = width
        self.width_start = self._width * (1-self.width_coef) / 2.
        self.width_range = self._width * self.width_coef
        self.update_main_angle()
        
    def update_main_angle(self):
        self.main_angle = 180*self._height/(self._width + self._height)
        
    def __set_height(self, height):
        self._height = height
        self.height_start = self._height * (1-self.height_coef) /2.
        self.height_range = self._height * self.height_coef
        self.update_main_angle()
        
    def get_topleft_position(self):
        min_x, min_y = self.get_position()
        for arc in itertools.chain(self.input_arcs, self.output_arcs):
            x, y = arc.get_topleft_position()
            if x<min_x: min_x = x
            if y<min_y: min_y = y
        return min_x, min_y
    
    def shift(self, dx, dy):
        super(GUITransition, self).shift(dx, dy)
        for arc in itertools.chain(self.input_arcs, self.output_arcs):
            arc.shift(dx, dy)
        
    def __get_width(self):
        return self._width
    
    def __get_height(self):
        return self._height
    
    def get_size(self):
        return self.width/2, self.height/2
    
    width = property(__get_width, __set_width)
    height = property(__get_height, __set_height)
        
    def rotate(self):
        self.width, self.height = self.height, self.width
        
    def set_temporary_arc(self, arc):
        self.temporary_arc = arc
        
    def draw(self, dc, zoom):
        self.precalculate_arcs()
        rect = self.get_rectangle()
        x,y,w,h = rect
        if self.is_enabled:
            dc.SetBrush(wx.RED_BRUSH)
            dc.SetPen(wx.RED_PEN)
        else:
            dc.SetBrush(wx.BLACK_BRUSH)
            dc.SetPen(wx.BLACK_PEN)
        if self.is_selected:
            dc.SetPen(constants.BLUE_PEN)
        #dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(x,y,w,h)
        
    def get_rectangle(self):
        x,y = self.pos_x, self.pos_y
        w,h = self.width,self.height
        return x-w/2,y-h/2,w,h
    
    def contains_point(self, x, y):
        r_x,r_y,r_w,r_h = self.get_rectangle()
        return (r_x <= x <= r_x+r_w) and (r_y <= y <= r_y+r_h)
    
    def in_rect(self, lx, ly, tx, ty):
        x, y, w, h = self.get_rectangle()
        return vec2d.rectangles_intersect((x, y, x+w, y+h), (lx, ly, tx, ty))
    
    def get_begin(self, arc):
        return self.get_touch_point(arc)
    
    def get_end(self, arc):
        return self.get_touch_point(arc)
    
    def get_touch_point(self, arc):
        result = vec2d.Vec2d(self.get_position())
        order, total_order, direction = self.side_slots[arc]
        order = (order + 1) / float(total_order+1)
        mx, my = self.directions[direction]
        if my == 0:
            my = self.height_start + order*self.height_range - self.height/2
            mx *= self.width/2.
        else:
            mx = self.width_start + order*self.width_range - self.width/2
            my *= self.height/2.
        result += vec2d.Vec2d(mx, my)
        return result
    
    def get_side(self, angle):
        if angle>180:
            a = 1
            angle-=180
        else:
            a = 0
        b = angle > self.main_angle
        return a*2+b
        
    def get_temporary_arc_iter(self):
        if self.temporary_arc is not None:
            yield self.temporary_arc
    
    def precalculate_arcs(self):
        """Precalculates the position of arcs' ends so that they are placed as free as possible"""
        side_slots = [[] for i in xrange(4)]
        for arc in itertools.chain(self.input_arcs, self.output_arcs, self.get_temporary_arc_iter()):
            point = arc.get_point_next_to(self)
            p_trans = vec2d.Vec2d(self.get_position())
            p_place = vec2d.Vec2d(point) - p_trans
            angle = p_place.angle
            angle += self.main_angle/2
            if angle<0:
                angle+=360
            elif angle>360:
                angle-=360
            direction = self.get_side(angle)
            side_slots[direction].append((arc, angle))
        self.side_slots = {}
        for n, slot in enumerate(side_slots):
            signum = 1 if (n==0 or n==3) else -1
            self.side_slots.update(dict((elem[0], (i, len(slot), n)) for i, elem in enumerate(sorted(slot, key=lambda x:x[1])[::signum])))
        
    def open_properties_dialog(self, parent):
        fields = [ ('unique_id', DialogFields.unique_id),
                   ('width', place_ranged('Width', minimum=5)),
                   ('height', place_ranged('Height', minimum=5)),
                   ] 
        dia = ElementPropertiesDialog(parent, -1, 'Transition properties', obj=self, fields=fields)
        dia.ShowModal()
        dia.Destroy()      
        
    def check_update_unique_id(self, value):
        if not value:
            raise ValueError, "Transition name can't be blank"
        if value in self.net.transitions:
            raise ValueError, "A transition with such name already exists"
        
    def update_unique_id(self, value):
        self.net.rename_transition(from_name=self.unique_id, to_name=value)
        
    def menu_rotate(self, event):
        self.rotate()
        
        
    def get_depending_objects(self):
        return []
        
        

class GUIPetriNet(petri.PetriNet):
    PLACE_CLS = GUIPlace
    TRANSITION_CLS = GUITransition
    
    def rename_place(self, from_name, to_name):
        place = self.remove_place(from_name)
        place.unique_id = to_name
        self.add_place(place)
        
    def rename_transition(self, from_name, to_name):
        transition = self.remove_transition(from_name)
        transition.unique_id = to_name
        self.add_transition(transition)
        
    def get_unique_place_name(self):
        return self.get_unique_name('p%d', self.places)
    
    def get_unique_transition_name(self):
        return self.get_unique_name('t%d', self.transitions)
    
    def get_unique_name(self, pattern, dct):
        i = 0
        while True:
            i += 1
            if pattern%i not in dct:
                return pattern%i
            
    def remove_arc_points(self):
        for transition in self.transitions.values():
            for arc in itertools.chain(transition.input_arcs, transition.output_arcs):
                arc.remove_arc_points()
                
    def automatic_layout(self):
        objects = {}
        for place in self.get_sorted_places():
            objects[place] = len(objects)
        for transition in self.get_sorted_transitions():
            objects[transition] = len(objects)
        import igraph
        graph = igraph.Graph(directed=True)
        graph.add_vertices(len(objects))
        for transition in self.get_sorted_transitions():
            trans_n = objects[transition]
            for arc in transition.input_arcs:
                graph.add_edge(objects[arc.place], trans_n)
            for arc in transition.output_arcs:
                graph.add_edge(trans_n, objects[arc.place])
        objects_lst = [None]*len(objects)
        if not objects_lst:
            return
        for obj, i in objects.iteritems():
            objects_lst[i] = obj
        layout = graph.layout_auto()
        bbox = layout.bounding_box()
        layout.translate((-bbox.left, -bbox.top))
        layout.scale(200)
        for obj, pos in zip(objects_lst, layout):
            x,y = pos
            obj.set_position(x+constants.RIGHT_OFFSET*3,y+constants.BOTTOM_OFFSET*3)

