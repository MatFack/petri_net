#!/usr/bin/python
# -*- coding: utf-8 -*-

import wx
import traceback
import time
import petri
import vector_2d as vec2d
import itertools

def draw_text(dc, text, center_x, center_y):
    """ Draws text, given text center """
    tw, th = dc.GetTextExtent(text)
    dc.DrawText(text, (center_x-tw/2),  (center_y-th/2))
    
def draw_unique_id(dc, unique_id, left_x, top_y):
    """ Draws element label, given topleft coordinates. """
    tw, th = dc.GetTextExtent(unique_id)
    dc.DrawText(unique_id, left_x-tw, top_y-th)

class GUIPlace(petri.Place):
    pos_x_to_serialize = True
    pos_y_to_serialize = True
    def __init__(self, unique_id=None, tokens=0, position=None):
        """
        unique_id - unique identifier (hash if None)
        tokens - number of tokens in initial marking
        position - (x,y)
        """
        super(GUIPlace, self).__init__(unique_id=unique_id, tokens=tokens)
        self.pos_x, self.pos_y = position or (0,0)
        self.radius = 10
        
    def set_position(self, x, y):
        self.pos_x = x
        self.pos_y = y
        
    def get_position(self):
        return self.pos_x, self.pos_y
        
    def draw(self, dc):
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawCircle(self.pos_x, self.pos_y, self.radius)
        draw_text(dc, str(self.tokens), self.pos_x, self.pos_y)
        draw_unique_id(dc, self.unique_id, self.pos_x-self.radius, self.pos_y-self.radius)
        
    def contains_point(self, x, y):
        x_diff = self.pos_x - x
        y_diff = self.pos_y - y
        return x_diff**2 + y_diff**2 <= self.radius**2
    
    def get_begin(self, vec, arc):
        pos = vec2d.Vec2d(self.get_position())
        pos -= vec.normalized()*self.radius
        return pos
    
    def get_end(self, vec, arc):
        pos = vec2d.Vec2d(self.get_position())
        pos += vec.normalized()*self.radius
        return pos
        
class GUIArc(petri.Arc):
    def __init__(self, place=None, transition=None, weight=0):
        super(GUIArc, self).__init__(place=place, transition=transition, weight=weight)
        self.tail_length = 10
        self.tail_angle = 15
        self.line_pen = wx.Pen(wx.BLACK, 2)
        
    def draw(self, dc):
        dc.SetPen(self.line_pen)
        fr = self.place
        to = self.transition
        if self.weight<0:
            fr, to = to, fr
        fr_center = vec2d.Vec2d(fr.get_position())
        to_center = vec2d.Vec2d(to.get_position())
        direction = fr_center - to_center
        fr_begin = fr.get_begin(direction, self)
        to_end = to.get_end(direction, self)
        self.draw_arrow(dc, fr_begin, to_end)
        label_x = (fr_begin[0]+to_end[0]) / 2
        label_y = (fr_begin[1]+to_end[1]) / 2
        label = str(self.weight)
        tw,th = dc.GetTextExtent(label)
        label_vec = to_end - fr_begin
        label_vec_perp = label_vec.perpendicular_normal()*max(th,tw)*0.5
        draw_text(dc, label, label_x+label_vec_perp[0], label_y+label_vec_perp[1])
        
    def draw_arrow(self, dc, fr, to):
        x,y = fr[0], fr[1]
        end_x, end_y = to[0], to[1]
        vec = -(to - fr)
        vec = vec.normalized()
        tail_1 = vec.rotated(self.tail_angle) * self.tail_length
        tail_2 = vec.rotated(-self.tail_angle) * self.tail_length
        dc.DrawLine(end_x, end_y, end_x+tail_1[0], end_y+tail_1[1])
        dc.DrawLine(end_x, end_y, end_x+tail_2[0], end_y+tail_2[1])
        #print x,y,end_x,end_y
        dc.DrawLine(x, y, end_x, end_y)
        
    def get_point_next_to(self, obj):
        if obj==self.place:
            return self.transition.get_position()
        elif obj==self.transition:
            return self.place.get_position()
        
        
        
class GUITransition(petri.Transition):
    ARC_CLS = GUIArc
    
    pos_x_to_serialize = True
    pos_y_to_serialize = True
    horizontal_to_serialize = True
    
    def __init__(self, unique_id=None, position=None, input_arcs=None, output_arcs=None, net=None):
        super(GUITransition,self).__init__(unique_id=unique_id, input_arcs=input_arcs, output_arcs=output_arcs, net=net)
        self.pos_x, self.pos_y = position or (0,0)
        self.width_coef = 0.9
        self.height_coef = 0.5
        self._width = self._height = 0
        self.width = 50
        self.height = 10
        
        self.side_slots = []
        self.main_angle = 90
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1), ]
        
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
        
    def get_width(self):
        return self._width
    
    def get_height(self):
        return self._height
    
    width = property(get_width, __set_width)
    height = property(get_height, __set_height)
        
    def set_position(self, x, y):
        self.pos_x = x
        self.pos_y = y
        
    def get_position(self):
        return self.pos_x, self.pos_y
        
    def rotate(self):
        self.width, self.height = self.height, self.width
        
    def draw(self, dc):
        rect = self.get_rectangle()
        x,y,w,h = rect
        if self.is_enabled:
            dc.SetBrush(wx.RED_BRUSH)
            dc.SetPen(wx.RED_PEN)
        else:
            dc.SetBrush(wx.BLACK_BRUSH)
            dc.SetPen(wx.BLACK_PEN)
        #dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(x,y,w,h)
        
    def get_rectangle(self):
        x,y = self.pos_x, self.pos_y
        w,h = self.width,self.height
        return x-w/2,y-h/2,w,h
    
    def contains_point(self, x, y):
        r_x,r_y,r_w,r_h = self.get_rectangle()
        return (r_x <= x <= r_x+r_w) and (r_y <= y <= r_y+r_h)
    
    def get_begin(self, vec, arc):
        return self.get_touch_point(vec, arc)
    
    def get_end(self, vec, arc):
        return self.get_touch_point(vec, arc)
    
    def get_touch_point(self, vec, arc):
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
        
    
    def precalculate_arcs(self):
        """Precalculates the position of arcs' ends so that they are places as free as possible"""
        side_slots = [[] for i in xrange(4)]
        for arc in itertools.chain(self.input_arcs, self.output_arcs):
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
        
                
            
        
            
            
        #print "HERE!"
        
        
        

class GUIPetriNet(petri.PetriNet):
    PLACE_CLS = GUIPlace
    TRANSITION_CLS = GUITransition
    

        

class PetriPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super(PetriPanel, self).__init__(*args, **kwargs)
        self.SetDoubleBuffered(True)
        self.Bind(wx.EVT_PAINT, self.on_paint_event)
        self.Bind(wx.EVT_SIZE,  self.on_size_event)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_button_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_button_up)
        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        
        self.size = None
        self.mouse_x = self.mouse_y = 0
        self.left_down = False
        
        self.petri = GUIPetriNet.from_string("""
            # p1::1 p2::2
            p2 -> t1 -> p1 p3
            p1 -> t2 -> p3::100
            p1 -> t3 -> p4
            p3 p4 -> t4 -> p2
        """)
        
        self.petri.places['p1'].set_position(50,20)
        self.petri['p2'].set_position (100,20)
        self.petri['p3'].set_position (80,80)
        self.petri['p4'].set_position (100,100)
        
        self.petri.transitions['t1'].set_position(300,80)
        self.petri.transitions['t2'].set_position(200,100)
        self.petri.transitions['t3'].set_position(60,100)
        self.petri.transitions['t4'].set_position(150,150)
        self.petri.transitions['t4'].rotate()
        #self.petri.transitions['t1'].set_horizontal(True)
        
        self.cur_obj = None #TODO: teplace with strategies (now just for debug)
        
        
    def on_size_event(self, event):
        self.size = event.GetSize()
        self.Refresh()
        
    def on_paint_event(self, event):
        dc = wx.BufferedPaintDC(self)
        w,h = self.size
        dc.SetPen(wx.WHITE_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(0,0,w,h)
        self.draw(dc, w, h)
        
    def on_left_button_down(self, event):
        self.mouse_x, self.mouse_y = event.m_x,event.m_y
        self.left_down = True
        
        obj = self.get_object_at(self.mouse_x, self.mouse_y)
        if not obj:
            return
        self.cur_obj = obj
        self.drag_mouse_x, self.drag_mouse_y = self.mouse_x, self.mouse_y
        self.drag_obj_x, self.drag_obj_y = self.cur_obj.get_position()
        self.Refresh()
        
    def get_object_at(self, x, y):
        # Check in reverse order so the topmost object will be selected
        places = list(self.petri.get_places())
        transitions = list(self.petri.get_transitions())
        objects = transitions[::-1] + places[::-1] 
        for obj in objects:
            if obj.contains_point(x, y):
                return obj
        
    def on_mouse_motion(self, event):
        self.mouse_x, self.mouse_y = event.m_x,event.m_y
        if self.cur_obj is not None:
            diff_x, diff_y = self.mouse_x - self.drag_mouse_x, self.mouse_y - self.drag_mouse_y
            self.cur_obj.set_position(self.drag_obj_x+diff_x, self.drag_obj_y+diff_y)
            self.Refresh()
        
    def on_left_button_up(self, event):
        self.mouse_x, self.mouse_y = event.m_x,event.m_y
        self.left_down = False
        self.cur_obj = None
        self.Refresh()
        
    def draw(self, dc, w, h):
        if not self.petri:
            return
        for place in self.petri.get_places():
            place.draw(dc)
        for transition in self.petri.get_transitions():
            transition.draw(dc)
            transition.precalculate_arcs()
            for arc in transition.input_arcs:
                arc.draw(dc)
            for arc in transition.output_arcs:
                arc.draw(dc)
        
        """
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawLine(0,0,w,h)
        if self.mouse_pos:
            dc.DrawLine(0, 0, self.mouse_pos[0], self.mouse_pos[1])"""
        
        

class Example(wx.Frame):
    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(500, 500))

        self.petri_panel = PetriPanel(self)

        self.Centre() 
        self.Show()


if __name__ == '__main__':
    app = wx.App(False)
    Example(None, 'Line')
    app.MainLoop()
    
    p  = GUIPlace('p1', 1, (100,100))
    x = p.to_json_struct()
    p2 = GUIPlace.from_json_struct(x, unique_id='p1')
    
    net1 = GUIPetriNet.from_string("""
    # 
    p2 -> t1 -> p1 p3
    p1 -> t2 -> p3
    p1 -> t3 -> p4
    p3 p4 -> t4 -> p2
    """,)
    
    print net1.to_json_struct()
    