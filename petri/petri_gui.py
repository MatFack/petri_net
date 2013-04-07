#!/usr/bin/python
# -*- coding: utf-8 -*-

import wx
import traceback
import time
import petri
import vector_2d as vec2d
import itertools
import json

if __name__ == '__main__':
    app = wx.App(False)

BLUE_PEN = wx.Pen('BLUE', 1)

def draw_text(dc, text, center_x, center_y):
    """ Draws text, given text center """
    tw, th = dc.GetTextExtent(text)
    dc.DrawText(text, (center_x-tw/2),  (center_y-th/2))
    
def draw_unique_id(dc, unique_id, left_x, top_y):
    """ Draws element label, given topleft coordinates. """
    tw, th = dc.GetTextExtent(unique_id)
    dc.DrawText(unique_id, left_x-tw, top_y-th)
    
def rectangles_intersect(rect1, rect2):
    """ Detects, whtether one rectangles intersects with another (including their square) """
    l1, t1, r1, b1 = rect1
    l2, t2, r2, b2 = rect2
    #print rect1,rect2
    separate = r1 < l2 or l1 > r2 or t1>b2 or b1<t2
    #print separate
    return not separate 
    
class PositionMixin(object):
    def __init__(self, *args, **kwargs):
        self.pos_x, self.pos_y = kwargs.get('pos_x', 0), kwargs.get('pos_y', 0)
        self.selected = False
        self.temporary_selected = False
        super(PositionMixin, self).__init__(*args, **kwargs)
    
    @property
    def is_selected(self):
        return self.selected or self.temporary_selected
        
        
    def set_position(self, x, y):
        self.pos_x = x
        self.pos_y = y
        
    def get_position(self):
        return self.pos_x, self.pos_y
    
    def prepare_to_move(self):
        self.memo_x, self.memo_y = self.pos_x, self.pos_y
        
    def move_diff(self, diff_x, diff_y):
        self.pos_x = self.memo_x + diff_x
        self.pos_y = self.memo_y + diff_y
        

class GUIPlace(PositionMixin, petri.Place):
    pos_x_to_serialize = True
    pos_y_to_serialize = True
    def __init__(self, unique_id=None, tokens=0, position=None):
        """
        unique_id - unique identifier (hash if None)
        tokens - number of tokens in initial marking
        """
        super(GUIPlace, self).__init__(unique_id=unique_id, tokens=tokens)
        self.radius = 14
           
    def draw(self, dc):
        if self.is_selected:
            dc.SetPen(BLUE_PEN)
        else:
            dc.SetPen(wx.BLACK_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawCircle(self.pos_x, self.pos_y, self.radius)
        if self.tokens>4:
            draw_text(dc, str(self.tokens), self.pos_x, self.pos_y)
        elif self.tokens>0:
            self.draw_tokens(dc)
        draw_unique_id(dc, self.unique_id, self.pos_x-self.radius, self.pos_y-self.radius)
        
    def draw_tokens(self, dc):
        #This sucks, but who cares
        dc.SetBrush(wx.BLACK_BRUSH)
        dc.SetPen(wx.BLACK_PEN)
        tokens_r = self.radius/3
        tokens_offset = self.radius/2.8
        if self.tokens==1:
            dc.DrawCircle(self.pos_x, self.pos_y, tokens_r)
        elif self.tokens==2:
            dc.DrawCircle(self.pos_x-tokens_offset, self.pos_y, tokens_r)
            dc.DrawCircle(self.pos_x + tokens_offset, self.pos_y, tokens_r)
        elif self.tokens==3:
            dc.DrawCircle(self.pos_x-tokens_offset, self.pos_y+tokens_r, tokens_r)
            dc.DrawCircle(self.pos_x + tokens_offset, self.pos_y+tokens_r, tokens_r)
            dc.DrawCircle(self.pos_x, self.pos_y-tokens_r, tokens_r)
        elif self.tokens==4:
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
        return rectangles_intersect(bounding_rect, (lx, ly, tx, ty))
    
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
        abs_weight = abs(self.weight)
        if abs_weight>1:
            label_x = (fr_begin[0]+to_end[0]) / 2
            label_y = (fr_begin[1]+to_end[1]) / 2
            label = str(abs_weight)
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
        dc.DrawLine(x, y, end_x, end_y)
        
    def get_point_next_to(self, obj):
        if obj==self.place:
            return self.transition.get_position()
        elif obj==self.transition:
            return self.place.get_position()
        
        
        
class GUITransition(PositionMixin, petri.Transition):
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
        self.width = 50
        self.height = 20
        
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
        
    def __get_width(self):
        return self._width
    
    def __get_height(self):
        return self._height
    
    width = property(__get_width, __set_width)
    height = property(__get_height, __set_height)
        
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
        if self.is_selected:
            dc.SetPen(BLUE_PEN)
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
        return rectangles_intersect((x, y, x+w, y+h), (lx, ly, tx, ty))

    
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
    

class Strategy(object):
    def __init__(self, panel):
        self.panel = panel
        self.left_down = False
        self.right_down = False
        self.mouse_x, self.mouse_y = 0, 0
        
    def set_mouse_coords(self, event):
        self.mouse_x, self.mouse_y = event.m_x, event.m_y
        
    def on_left_down(self, event):
        self.left_down = True
        self.set_mouse_coords(event)
    
    def on_left_up(self, event):
        self.left_down = False
        self.set_mouse_coords(event)
    
    def on_right_down(self, event):
        self.right_down = True
        self.set_mouse_coords(event)
    
    def on_right_up(self, event):
        self.right_down = False
        self.set_mouse_coords(event)
    
    def on_motion(self, event):
        self.set_mouse_coords(event)
        
    
class MoveAndSelectStrategy(Strategy):
    def __init__(self, panel):
        super(MoveAndSelectStrategy, self).__init__(panel=panel)
        self.selection = set()
        self.choosing_rect_left = None
        self.to_select = None
        self.object_moved = False
        self.dragging = False
        self.obj_under_mouse = None
        
    def on_left_down(self, event):
        super(MoveAndSelectStrategy, self).on_left_down(event)
        print dir(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if not (event.ControlDown() or event.AltDown()):
            #obj not in self.selection:
            print "Discarding"
            self.discard_selection()
        self.obj_under_mouse = obj
        if obj is None:
            self.choosing_rect_left = self.mouse_x, self.mouse_y
            self.update_selected(event.AltDown())
            self.panel.Refresh()
            return
        if event.AltDown():
            self.remove_from_selection(obj)
        else:
            self.add_to_selection(obj)  
            self.start_dragging()
        self.panel.Refresh()
        
    def discard_selection(self):
        if not self.selection:
            return
        for obj in self.selection:
            obj.set_selected(False)
        self.selection.clear()
        
    def add_to_selection(self, *objects):
        for obj in objects:
            obj.set_selected(True)
        self.selection.update(objects)
        
    def remove_from_selection(self, *objects):
        for obj in objects:
            obj.set_selected(False)
        self.selection.difference_update(objects)
        
    def move_selection(self):
        diff_x, diff_y = self.mouse_x - self.drag_mouse_x, self.mouse_y - self.drag_mouse_y
        for obj in self.selection:
            obj.move_diff(diff_x, diff_y)
        
    def on_motion(self, event):
        if not event.LeftIsDown():
            return
        super(MoveAndSelectStrategy, self).on_motion(event)
        self.object_moved = True
        if self.choosing_rect_left is not None:
            self.update_selected(event.AltDown())
            self.panel.Refresh()
        elif self.left_down and self.selection is not None:
            self.move_selection()
            self.panel.Refresh()

            
    def update_selected(self, alt_down, return_selection=False):
        self.choosing_rect_right = self.mouse_x, self.mouse_y
        gen = self.panel.GetObjectsInRect(*self.points_to_rect(self.choosing_rect_left, self.choosing_rect_right))
        if return_selection:
            result = list(gen)
        else:
            result = gen
        for obj in result:
            obj.set_selected(not alt_down)
        return result if return_selection else None
        
    def points_to_rect(self, left, right):
            lx,ly = left
            tx,ty = right
            if lx>tx:
                tx, lx = lx, tx
            if ly>ty:
                ty, ly = ly, ty
            return lx, ly, tx, ty
        
    def draw(self, dc):
        if self.choosing_rect_left:
            lx, ly, tx, ty = self.points_to_rect(self.choosing_rect_left, self.choosing_rect_right)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(wx.BLACK_PEN)
            dc.DrawRectangle(lx,ly, tx-lx, ty-ly)
        
            
    def on_left_up(self, event):
        super(MoveAndSelectStrategy, self).on_left_up(event)
        if self.choosing_rect_left is not None:
            selected = self.update_selected(event.AltDown(), return_selection=True)
            if event.AltDown():
                self.remove_from_selection(*selected)
            else:
                self.add_to_selection(*selected)
            self.choosing_rect_left = None
            self.panel.Refresh()
        if not self.object_moved and self.obj_under_mouse in self.selection:
            if not event.ControlDown():
                self.discard_selection()
            self.add_to_selection(self.obj_under_mouse)
            self.panel.Refresh()
        if self.dragging:
            self.stop_dragging()
              
    def start_dragging(self):
        self.drag_mouse_x, self.drag_mouse_y = self.mouse_x, self.mouse_y
        for obj in self.selection:
            obj.prepare_to_move()
        self.dragging = True
        self.object_moved = False
        
    def stop_dragging(self):
        self.dragging = False

class SimulateStrategy(Strategy):
    def __init__(self, panel):
        super(SimulateStrategy, self).__init__(panel=panel)
        
    def on_left_down(self, event):
        super(SimulateStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if isinstance(obj, petri.Transition):
            if obj.is_enabled:
                obj.fire()
                self.panel.Refresh()
    
    

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
        
        try:
            self.petri = self.load_from_file('net.json')
        except:
            self.petri = GUIPetriNet.from_string("""
                # p1::1 p2::2 p3::3 p4::4 p5::5
                p2 -> t1 -> p1 p3
                p1 -> t2 -> p3::100
                p1 -> t3 -> p4
                p3 p4 -> t4 -> p2
            """)
            
            
        self.strategy = MoveAndSelectStrategy(self)
        #self.strategy = SimulateStrategy(self)
        #self.petri.transitions['t1'].set_horizontal(True)
        
        self.cur_obj = None #TODO: replace with strategies (now just for debug)
        
    def GetObjectsInRect(self, lx, ly, tx, ty):
        if not self.petri:
            return
        for obj in itertools.chain(self.petri.get_places(), self.petri.get_transitions()):
            obj.set_temp_selected(False)
            if obj.in_rect(lx, ly, tx, ty):
                yield obj
        
            
        
    def load_from_file(self, filepath):
        net = None
        with open(filepath, 'rb') as f:
            json_struct = json.load(f)
        net = GUIPetriNet.from_json_struct(json_struct)
        return net
        
    def save_to_filepath(self, filepath, net):
        json_struct = net.to_json_struct()
        with open(filepath, 'wb') as f:
            json.dump(json_struct, f)
        
        
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
        self.mouse_in = True
        self.on_lbutton_timer()
        self.strategy.on_left_down(event)
        
    def on_lbutton_timer(self, *args, **kwargs):
        x, y, w, h = self.GetScreenRect()
        mx, my = wx.GetMousePosition()
        state = wx.GetMouseState()
        if not state.LeftDown():
            if self.HasCapture():
                self.ReleaseMouse()
            return
        mouse_in = x <= mx <= x+w and y <= my <= y+h
        if mouse_in and not self.mouse_in:
            if self.HasCapture():
                self.ReleaseMouse()
        elif not mouse_in and self.mouse_in:
            self.CaptureMouse()
        self.mouse_in = mouse_in
        wx.CallLater(20, self.on_lbutton_timer)
        
    def get_object_at(self, x, y):
        # Check in reverse order so the topmost object will be selected
        places = list(self.petri.get_places())
        transitions = list(self.petri.get_transitions())
        objects = transitions[::-1] + places[::-1] 
        for obj in objects:
            if obj.contains_point(x, y):
                return obj
        
    def on_mouse_motion(self, event):
        self.strategy.on_motion(event)
        
    def on_left_button_up(self, event):
        self.strategy.on_left_up(event)
        
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
        self.strategy.draw(dc)
        
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
    