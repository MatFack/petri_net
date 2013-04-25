#!/usr/bin/python
# -*- coding: utf-8 -*-


# DONE: Commands history
# DONE: Move command
# DONE: Create command
# DONE: Delete command
# DONE: Copy - puts selected into Buffer - this gonna be tough
# DONE: Make coordinates in buffer relative,
# DONE: Cut - creates Delete command, puts selected into Buffer
# DONE: Paste - creates Create command, puts there objects from Buffer

# DONE: Tabs
# TODO: Put properties somewhere, (menu - analysis - tabbed window)
# DONE: Create menu (save, open, exit, export)

import wx
import wx.aui
import traceback
import time
import petri
import vector_2d as vec2d
import itertools
import json
import collections
import wx.lib.buttons as buttons
from petrigui.dialog_fields import DialogFields, place_ranged 
import serializable
from collections import OrderedDict, deque
import os
import os.path as osp


if __name__ == '__main__':
    app = wx.App(False)

VSCROLL_X = wx.SystemSettings_GetMetric(wx.SYS_VSCROLL_X)
HSCROLL_Y = wx.SystemSettings_GetMetric(wx.SYS_HSCROLL_Y)

RIGHT_OFFSET = BOTTOM_OFFSET = VSCROLL_X*2

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
    separate = r1 < l2 or l1 > r2 or t1>b2 or b1<t2
    return not separate 



class ElementPropertiesDialog(wx.Dialog):
    def __init__(self, parent, window_id, title, obj, fields):
        self.parent = parent
        self.fields = collections.OrderedDict()
        for field, value in fields:
            self.fields[field] = value
        self.obj = obj
        super(ElementPropertiesDialog, self).__init__(parent, window_id, title)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.result = {} #
        
        sb = wx.StaticBox(self, label=title)
        sbs = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)
        self.InitUI(sbs)

        sizer.Add(sbs, border=5, proportion=1, flag=wx.ALL|wx.EXPAND)
        
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, wx.ID_OK, label='Ok')
        closeButton = wx.Button(self, wx.ID_CANCEL, label='Cancel')
        hbox2.Add(okButton)
        hbox2.Add(closeButton, flag=wx.LEFT, border=5)
        sizer.Add(hbox2, 
            flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        closeButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        
        
        self.SetSizer(sizer)
        self.Fit()
    
        
    def OnOk(self, event):
        if self.check_values():
            self.UpdateObjectValues()
            self.Destroy()
            self.SetReturnCode(wx.ID_CANCEL)
            
    OnTextEnter = OnOk
        
    def check_values(self):
        for field_name, (label, getter, setter) in self.fields.iteritems():
            control = self.field_controls[field_name]
            value = setter(control)
            self.result[field_name] = value
            if getattr(self.obj, field_name, None) == value:
                continue
            checker = getattr(self.obj, 'check_update_'+field_name, None)
            if checker:
                try:
                    checker(value)
                except Exception, e:
                    error = getattr(e,'message','')
                    error = '\n'+error if error else error
                    wx.MessageBox("Incorrect value for field %s.%s"%(field_name, error))
                    return False
        return True
        
    def UpdateObjectValues(self):
        command = ChangePropertiesCommand(self.parent, self.obj)
        for field, value in self.result.iteritems():
            command.update_field_value(field, getattr(self.obj, field, None), value)
        if not command.does_nothing:
            command.execute()
            self.parent.append_command(command)
        
    def OnCancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)
        
    def InitUI(self, sizer):
        self.field_controls = {}
        for field_name, (label, getter, setter) in self.fields.iteritems():
            value = getattr(self.obj, field_name, '')
            self.result[field_name] = value
            hbox1 = wx.BoxSizer(wx.HORIZONTAL)
            hbox1.Add(wx.StaticText(self, label=label))
            control = getter(self, value)
            self.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter)
            hbox1.Add(control, flag=wx.LEFT, border=5, )
            self.field_controls[field_name] = control
            sizer.Add(hbox1)
            

    
class PositionMixin(object):
    def __init__(self, *args, **kwargs):
        self.pos_x, self.pos_y = kwargs.get('pos_x', 0), kwargs.get('pos_y', 0)
        super(PositionMixin, self).__init__(*args, **kwargs)
        
    def set_position(self, x, y):
        x, y = self.correct_to_grid(x, y)
        self.pos_x = x # - (x%7)
        self.pos_y = y # - (y%7) # lol grid
        
    def get_size(self):
        return (0, 0)

    def correct_to_grid(self, x, y):
        w,h = self.get_size()
        x -= x % 7
        y -= y % 7
        r_x, r_y = max(x, w), max(y, h)
        return r_x, r_y
        
    def get_position(self):
        return self.pos_x, self.pos_y
    
    def shift(self, dx, dy):
        x, y = self.get_position()
        self.set_position(x+dx, y+dy)
    
    def prepare_to_move(self):
        self.memo_x, self.memo_y = self.pos_x, self.pos_y
        
    def move_diff(self, diff_x, diff_y):
        new_x = self.memo_x + diff_x
        new_y = self.memo_y + diff_y
        self.set_position(new_x, new_y)
        
class SelectionMixin(object):
    def __init__(self, *args, **kwargs):
        self.selected = False
        self.temporary_selected = False
        self.temporary_discarded = False
        super(SelectionMixin, self).__init__(*args, **kwargs)
        
    @property
    def is_selected(self):
        return False if self.temporary_discarded else self.selected or self.temporary_selected
        
    def unselect_temporary(self):
        self.temporary_discarded = self.temporary_selected = False
        
    def set_selected(self, selected):
        if not selected:
            self.unselect_temporary()
        self.selected = selected
        

class ObjectLabel(SelectionMixin, PositionMixin, serializable.Serializable):
    diff_x_to_serialize = True
    diff_y_to_serialize = True
    
    def __init__(self, obj, x=0, y=0):
        self.obj = obj
        self.diff_x = x
        self.diff_y = y
        self.rectangle = (0, 0, 0, 0)
        self.rectangle_set = False
        self.tw = self.th = 0
        
        
    def draw(self, dc):
        text = str(self.obj.unique_id)
        self.draw_text(dc, text)
        
    def draw_text(self, dc, text):
        tw, th = dc.GetTextExtent(text)
        if tw%2==1: tw+=1
        if th%2==1: th+=1
        self.tw, self.th = tw, th
        self.recalculate_position()
        x1,y1, _, _ = self.rectangle
        dc.DrawText(text,  x1, y1)
        
    def set_position(self, x, y):
        obj_x, obj_y = self.obj.get_position()
        self.diff_x, self.diff_y = x - obj_x + self.tw/2, y - obj_y + self.th/2
        
    def get_size(self):
        x1, y1, x2, y2 = self.rectangle
        return (x2-x1)/2, (y2-y1)/2
    
    def correct_to_grid(self, x, y):
        return max(x, 0), max(y, 0)
    
    def recalculate_position(self):
        obj_x, obj_y = self.obj.get_position()
        right_x = obj_x + self.diff_x
        bottom_y = obj_y + self.diff_y
        x1, y1 = right_x-self.tw, bottom_y-self.th
        x1, y1 = self.correct_to_grid(x1, y1)
        x2, y2 = x1 + self.tw, y1 + self.th
        self.rectangle = (x1, y1, x2, y2)
        if not self.rectangle_set:
            self.rectangle_set = True
            x1, y1 = self.correct_to_grid(x1, y1)
            x2, y2 = x1 + self.tw, y1 + self.th
            self.rectangle = (x1, y1, x2, y2)
        
    def get_position(self):
        x1, y1, x2, y2 = self.rectangle
        return (x1+x2)/2, (y1+y2)/2
        
    def contains_point(self, x, y):
        x1, y1, x2, y2 = self.rectangle
        return x1 <= x <= x2 and y1 <= y <= y2
    
    def prepare_to_move(self):
        self.memo_diff_x = self.diff_x
        self.memo_diff_y = self.diff_y
    
    def in_rect(self, lx, ly, tx, ty):
        pass
    
    def move_diff(self, diff_x, diff_y):
        self.diff_x = self.memo_diff_x + diff_x
        self.diff_y = self.memo_diff_y + diff_y
        
    def open_properties_dialog(self, panel):
        self.obj.open_properties_dialog(panel)
        
class MenuMixin(object):
    def spawn_context_menu(self, parent, event):
        self.menu_parent = parent
        self.menu_event = event
        menu = wx.Menu()
        for event_id, (name, handler) in self.menu_fields.iteritems():
            menu.Append(event_id, name)
            parent.Bind(wx.EVT_MENU, handler, id=event_id)
        parent.PopupMenu(menu, event.GetPositionTuple())
        menu.Destroy()
        for event_id, (name, handler) in self.menu_fields.iteritems():
            parent.Unbind(wx.EVT_MENU, id=event_id)
        parent.Refresh()

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
        self.label = ObjectLabel(self, -self.radius, -self.radius)
        if position:
            self.set_position(*position)
           
    def label_to_json_struct(self, **kwargs):
        return self.label.to_json_struct(**kwargs)
    
    def label_from_json_struct(self, label_obj, **kwargs):
        return ObjectLabel.from_json_struct(label_obj, constructor_args=dict(obj=self), **kwargs)
           
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
            
    def get_topleft_position(self):
        x, y = self.get_position()
        return x-self.radius, y-self.radius
                
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
        self.menu_fields = OrderedDict()
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
            self.points_selected -= 1
        self.points.remove(point)
        
    def select_line_pen(self, dc):
        if self.is_selected:
            dc.SetPen(self.line_selected_pen)
        else:
            dc.SetPen(self.line_pen)        
            
    def draw(self, dc):
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
        self.draw_arrow(dc, fr_begin, to_end)
        if abs(self.weight)>1:
            self.draw_label(dc)
            
    def draw_label(self, dc):
        point, direction = self.get_center()
        label = str(abs(self.weight))
        label_x = point[0]
        label_y = point[1]
        tw,th = dc.GetTextExtent(label)
        label_vec_perp = direction.perpendicular_normal()*max(th,tw)*0.8
        draw_text(dc, label, label_x+label_vec_perp[0], label_y+label_vec_perp[1])
        
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
        
    def draw_arrow(self, dc, fr, to):
        end_x, end_y = to[0], to[1]
        vec = -(to - fr)
        vec = vec.normalized()
        tail_1 = vec.rotated(self.tail_angle) * self.tail_length
        tail_2 = vec.rotated(-self.tail_angle) * self.tail_length
        dc.DrawLine(end_x, end_y, end_x+tail_1[0], end_y+tail_1[1])
        dc.DrawLine(end_x, end_y, end_x+tail_2[0], end_y+tail_2[1])
        
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
        x,y = self.menu_event.GetPositionTuple()
        ind, (a,b) = self.get_segment_nearest_to_point(x, y, self.line_pen.GetWidth())
        arc_point = ArcPoint(self)
        arc_point.set_position(x, y)
        self.points.insert(ind, arc_point)
        strategy = self.menu_parent.strategy
        if isinstance(strategy, MoveAndSelectStrategy):
            strategy.discard_selection()
            strategy.add_to_selection(arc_point) # nu eto uje pizdec obser
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
        
    def get_rectangle(self):
        x,y = self.pos_x, self.pos_y
        w,h = self.width,self.height
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
        return rectangles_intersect((x, y, x+w, y+h), (lx, ly, tx, ty))
    
    def draw(self, dc):
        if not self.arc.points_selected and not self.arc.is_selected:
            return 
        x, y, w, h = self.get_rectangle()
        if self.selected:
            dc.SetPen(BLUE_PEN)
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
        self.menu_fields = OrderedDict()
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
        
    def draw(self, dc):
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

    

class Strategy(object):
    def __init__(self, panel):
        self._panel = panel
        self.left_down = False
        self.right_down = False
        self.mouse_x, self.mouse_y = 0, 0
        self.need_capture_mouse = False
        self.is_moving_objects = False
        self.allow_undo_redo = True
        
        
    @property
    def panel(self):
        return self._panel()
        
    def set_mouse_coords(self, event):
        #x, y = max(event.m_x, 0), max(event.m_y, 0)
        x, y = event.m_x, event.m_y
        self.mouse_x, self.mouse_y = self.panel.screen_to_canvas_coordinates((x, y))
        
    def on_left_down(self, event):
        self.left_down = True
        self.set_mouse_coords(event)
        
    def on_left_dclick(self, event):
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
    
    def on_key_down(self, event):
        pass
        
    def draw(self, dc):
        pass
    
    def on_switched_strategy(self):
        pass
        
        
class PropertiesMixin(object):
    def on_left_dclick(self, event):
        super(PropertiesMixin, self).on_left_dclick(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if not obj:
            return
        obj.open_properties_dialog(self.panel)
        self.panel.Refresh()
        
    
class MoveAndSelectStrategy(PropertiesMixin, Strategy):
    def __init__(self, panel):
        super(MoveAndSelectStrategy, self).__init__(panel=panel)
        self.selection = set()
        self.choosing_rect_left = None
        self.choosing_rect_right = None
        self.to_select = None
        self.object_moved = False
        self.dragging = False
        self.obj_under_mouse = None
        self.label_moved = None
        self.need_capture_mouse = True
        self.move_command = None
        
    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_DELETE:
            self.on_delete()
        elif keycode == wx.WXK_RETURN:
            if len(self.selection) == 1:
                for obj in self.selection:
                    obj.open_properties_dialog(self.panel)
                
    def on_cut(self):
        self.on_copy()
        self.on_delete()
        
    def on_select_all(self):
        for obj in self.panel.get_objects_iter():
            if not isinstance(obj, ObjectLabel):
                self.add_to_selection(obj)
        self.panel.Refresh()
                
    def on_copy(self):
        places_set = set()
        places = deque()
        transitions_objects = deque()
        transitions = deque()
        for obj in self.selection:
            if isinstance(obj, petri.Place):
                places.append((obj.__class__,obj.to_json_struct()))
                places_set.add(obj)
            elif isinstance(obj, petri.Transition):
                transitions_objects.append(obj)
        if not places_set and not transitions_objects:
            return
        for transition in transitions_objects:
            transitions.append((transition.__class__, transition.to_json_struct(only_arcs_with_places=places_set)))
        self.panel.clip_buffer.set_content(places=places, transitions=transitions)
        
    def on_paste(self):
        places, transitions = self.panel.clip_buffer.get_content()
        if not places and not transitions:
            return
        self.discard_selection()
        command = CreateDeleteObjectCommand(self.panel, move_strategy=self)
        objects = deque()
        places_dct = {}
        
        net = self.panel.petri
        for cls, place_obj in places:
            place = cls.from_json_struct(place_obj, constructor_args=dict(net=net))
            place_name = place.unique_id
            k = 1
            while place.unique_id in net.places:
                place.unique_id = '%s (%d)'%(place_name, k)
                k += 1
            places_dct[place_name] = place
            net.add_place(place)
            self.add_to_selection(place)
            command.add_object(place)
            objects.append(place)
            
        for cls, transition_obj in transitions:
            transition = cls.from_json_struct(transition_obj, constructor_args=dict(net=net), places_dct=places_dct)

            transition_name = transition.unique_id
            k = 1
            while transition.unique_id in net.transitions:
                transition.unique_id = '%s (%d)'%(transition_name, k)
                k += 1
            net.add_transition(transition)
            self.add_to_selection(transition)
            for arc in itertools.chain(transition.input_arcs, transition.output_arcs):
                for point in arc.points:
                    self.add_to_selection(point)
            command.add_object(transition)
            objects.append(transition)
        min_x = min_y = None, None
        for obj in objects:
            x, y = obj.get_topleft_position()
            if min_x is None or x < min_x: min_x = x
            if min_x is None or y < min_y: min_y = y
        vx, vy = self.panel.view_point
        for obj in objects:
            obj.shift(-min_x+40+vx, -min_y+40+vy)
        self.panel.append_command(command)
        self.panel.update_bounds()
        self.panel.Refresh()
        
    def on_delete(self):
        if not self.selection:
            return
        net = self.panel.petri
        to_delete = set()
        for obj in self.selection:
            to_delete.add(obj)
            to_delete.update(obj.get_depending_objects())
        command = CreateDeleteObjectCommand(self.panel, move_strategy=self,to_delete=True)
        for obj in to_delete:
            command.add_object(obj)
        command.execute()
        self.panel.append_command(command)
        self.panel.update_bounds()
        self.discard_selection()
        self.panel.Refresh()
        
    def on_left_down(self, event):
        super(MoveAndSelectStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if isinstance(obj, ObjectLabel):
            if event.ControlDown():
                self.label_moved = obj
            else:
                self.label_moved = obj.obj
            self.start_dragging()
            self.panel.Refresh()
            return
        #if obj is not None and obj.is_selected:
        #    self.add_to_selection(obj)
        if not (event.ControlDown() or event.AltDown()):
            if obj not in self.selection:
                self.discard_selection()
        self.obj_under_mouse = obj
        if obj is None:
            self.choosing_rect_left = self.mouse_x, self.mouse_y
            self.choosing_rect_right = None
            #self.update_selected(event.AltDown())
            self.panel.Refresh()
            return
        if event.AltDown():
            self.remove_from_selection(obj)
        else:
            self.add_to_selection(obj)  
            self.start_dragging()
        self.panel.Refresh()
        
    def on_right_down(self, event):
        super(MoveAndSelectStrategy, self).on_right_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if obj is None:
            return
        self.add_to_selection(obj)
        obj.spawn_context_menu(self.panel, event)

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
        
    def get_selection_objects(self, object_to_move):
        if object_to_move is None:
            for obj in self.selection:
                yield obj
        else:
            yield object_to_move
        
    def move_selection(self, object_to_move=None):
        diff_x, diff_y = self.mouse_x - self.drag_mouse_x, self.mouse_y - self.drag_mouse_y
        for obj in self.get_selection_objects(object_to_move):
            obj.move_diff(diff_x, diff_y)
        self.panel.update_bounds()
            
    def on_switched_strategy(self):
        self.discard_selection()
        self.panel.Refresh()
        
    def on_motion(self, event):
        if not event.LeftIsDown():
            return
        super(MoveAndSelectStrategy, self).on_motion(event)
        self.object_moved = True
        if self.choosing_rect_left is not None:
            self.update_selected(event.AltDown())
            self.panel.Refresh()
        elif self.left_down and self.dragging:
            if self.label_moved is not None:
                self.move_selection(object_to_move=self.label_moved)
            elif self.selection is not None:
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
            if return_selection:
                obj.unselect_temporary()
                continue
                # This is left button up event, no need to calculate temporary values
            obj.temporary_selected = not alt_down
            if alt_down:
                obj.temporary_discarded = True
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
        if self.choosing_rect_left and self.choosing_rect_right:
            lx, ly, tx, ty = self.points_to_rect(self.choosing_rect_left, self.choosing_rect_right)
            dc.SetBrush(wx.TRANSPARENT_BRUSH)
            dc.SetPen(wx.BLACK_PEN)
            dc.DrawRectangle(lx,ly, tx-lx, ty-ly)
        
            
    def on_left_up(self, event):
        super(MoveAndSelectStrategy, self).on_left_up(event)
        if self.label_moved is not None:
            self.label_moved = None
        elif self.choosing_rect_left is not None:
            if self.choosing_rect_right is None:
                self.choosing_rect_left = None
            else:
                selected = self.update_selected(event.AltDown(), return_selection=True)
                if event.AltDown():
                    self.remove_from_selection(*selected)
                else:
                    self.add_to_selection(*selected)
                self.choosing_rect_left = None
                self.choosing_rect_right = None
        elif not self.object_moved and self.obj_under_mouse in self.selection:
            if not event.ControlDown():
                self.discard_selection()
            self.add_to_selection(self.obj_under_mouse)
        if self.dragging:
            self.stop_dragging()
        self.panel.Refresh()
        self.panel.update_bounds()
        #self.panel.save_to_file('net.json', self.panel.petri)
              
    def start_dragging(self):
        self.drag_mouse_x, self.drag_mouse_y = self.mouse_x, self.mouse_y
        self.move_command = MoveCommand(self.panel)
        for obj in self.get_selection_objects(object_to_move=self.label_moved):
            obj.prepare_to_move()
            self.move_command.add_object(obj)
        self.dragging = True
        self.is_moving_objects = True
        self.object_moved = False
        
    def stop_dragging(self):
        self.dragging = False
        self.is_moving_objects = False
        self.move_command.record_move()
        self.panel.append_command(self.move_command)
        self.move_command = None

class SimulateStrategy(Strategy):
    def __init__(self, panel):
        super(SimulateStrategy, self).__init__(panel=panel)
        self.allow_undo_redo = False
        
    def on_left_down(self, event):
        super(SimulateStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if isinstance(obj, petri.Transition):
            if obj.is_enabled:
                obj.fire()
                self.panel.Refresh()
                print self.panel.petri.get_state()

class MenuStrategyMixin(object):
    def on_right_down(self, event):
        super(MenuStrategyMixin, self).on_right_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if obj is not None:
            obj.spawn_context_menu(self.panel, event)
                
class AddPlaceStrategy(MenuStrategyMixin, PropertiesMixin, Strategy):
    def __init__(self, panel):
        super(AddPlaceStrategy, self).__init__(panel=panel)
        
    def on_left_down(self, event):
        super(AddPlaceStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if obj is not None:
            return
        net = self.panel.petri
        unique_id = net.get_unique_place_name()
        position = (self.mouse_x, self.mouse_y)
        place = net.new_place(unique_id=unique_id, position=position)
        command = CreateDeleteObjectCommand(self.panel, place)
        self.panel.append_command(command)
        self.panel.Refresh()
        

        
class AddTransitionStrategy(MenuStrategyMixin, PropertiesMixin, Strategy):
    def __init__(self, panel):
        super(AddTransitionStrategy, self).__init__(panel=panel)
        
    def on_left_down(self, event):
        super(AddTransitionStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if obj is not None:
            return
        net = self.panel.petri
        unique_id = net.get_unique_transition_name()
        position = (self.mouse_x, self.mouse_y)
        trans = net.new_transition(unique_id=unique_id, position=position)
        command = CreateDeleteObjectCommand(self.panel, trans)
        self.panel.append_command(command)
        self.panel.Refresh()
        
class MouseObj(object):
    def __init__(self, panel, x, y):
        self.panel = panel
        self.x, self.y = x, y
        self.proxy_obj = None
        
    def set_position(self, x, y):
        self.x, self.y = x, y
    
    def get_position(self):
        if self.proxy_obj is not None:
            return self.proxy_obj.get_position()
        return self.x, self.y
    
    def get_begin(self, obj):
        if self.proxy_obj is not None:
            return self.proxy_obj.get_begin(obj)
        return self.get_position()
    
    def __eq__(self, other):
        return self.proxy_obj==other
    
    get_end = get_begin
        
class AddArcStrategy(MenuStrategyMixin, PropertiesMixin, Strategy):
    def __init__(self, panel):
        super(AddArcStrategy, self).__init__(panel=panel)
        self.arc = None
        self.mouse_obj = None
        self.needed_class = None
        
    def on_left_down(self, event):
        super(AddArcStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if self.arc is None:
            self.create_new_arc(obj)
        else:
            if obj is None:
                self.arc.add_point((self.mouse_x, self.mouse_y))
            elif isinstance(obj, self.needed_class):
                transition = self.arc.transition
                place = self.arc.place
                if self.needed_class == petri.Transition:
                    transition = obj
                elif self.needed_class == petri.Place:
                    place = obj
                if self.arc.can_append(place=place, transition=transition):
                    self.arc.transition = transition
                    self.arc.place = place
                    self.arc.inject()
                    command = CreateDeleteObjectCommand(self.panel, self.arc)
                    self.panel.append_command(command)
                    self.reset()
        self.panel.Refresh()
        
    def reset(self):
        if self.arc is not None:
            if isinstance(self.arc.transition, MouseObj):
                transition = self.arc.transition.proxy_obj
            else:
                transition = self.arc.transition
            if transition:
                transition.set_temporary_arc(None)
            self.arc = None
            self.mouse_obj = None
            self.needed_class = None
            
    def on_right_down(self, event):
        super(AddArcStrategy, self).on_right_down(event)
        self.reset()
        self.panel.Refresh()
        
    def create_new_arc(self, obj_clicked):
        self.mouse_obj = MouseObj(self.panel, self.mouse_x, self.mouse_y)
        if isinstance(obj_clicked, petri.Transition):
            self.arc = GUIArc(self.panel.petri, self.mouse_obj, obj_clicked, -1)
            obj_clicked.set_temporary_arc(self.arc)
            self.needed_class = petri.Place
        elif isinstance(obj_clicked, petri.Place):
            self.arc = GUIArc(self.panel.petri, obj_clicked, self.mouse_obj, 1)
            self.needed_class = petri.Transition
        else:
            self.needed_class = None
            
    def on_motion(self, event):
        super(AddArcStrategy, self).on_motion(event)
        if self.arc is not None and self.mouse_obj is not None:
            self.mouse_obj.set_position(self.mouse_x, self.mouse_y)
            obj_under_mouse = self.panel.get_object_at(self.mouse_x, self.mouse_y)
            prev_obj = self.mouse_obj.proxy_obj
            self.mouse_obj.proxy_obj = obj_under_mouse
            if prev_obj != obj_under_mouse and prev_obj and isinstance(prev_obj, petri.Transition):
                prev_obj.set_temporary_arc(None)
            if isinstance(obj_under_mouse, self.needed_class):
                if isinstance(obj_under_mouse, petri.Transition):
                    obj_under_mouse.set_temporary_arc(self.arc)
            else:
                self.mouse_obj.proxy_obj = None
            self.panel.Refresh()

    def draw(self, dc):
        if self.arc is not None:
            self.arc.draw(dc)
            
    def on_switched_strategy(self):
        super(AddArcStrategy, self).on_switched_strategy()
        self.reset()
        self.panel.Refresh()
        
    
class SmartDC(wx.BufferedPaintDC):
    def __init__(self, window, *args, **kwargs):
        self.panel = window
        super(SmartDC, self).__init__(window, *args, **kwargs)
    
    
    def DrawRectangle(self, x, y, width, height, convert=True):
        if convert:
            x,y = self.panel.canvas_to_screen_coordinates((x,y))
        return super(SmartDC, self).DrawRectangle(x, y, width, height)   
    
    def DrawLine(self, x1, y1, x2, y2):
        x1, y1 = self.panel.canvas_to_screen_coordinates((x1, y1))
        x2, y2 = self.panel.canvas_to_screen_coordinates((x2, y2))
        return super(SmartDC, self).DrawLine(x1, y1, x2, y2)
    
    def DrawCircle(self, x, y, radius):
        x, y = self.panel.canvas_to_screen_coordinates((x, y))
        return super(SmartDC, self).DrawCircle(x, y, radius)
    
    def DrawText(self, text, x, y):
        x, y = self.panel.canvas_to_screen_coordinates((x, y))
        return super(SmartDC, self).DrawText(text, x, y)

class Command(object): # not just a command, but a command history itself
    """
       Command instance is always the first one
       None <- Command() -> MoveCommand() -> DeleteCommand() -> None
    """
    def __init__(self):
        super(Command, self).__init__()
        self.__prev = None
        self.__next = None
        self.does_nothing = False # sometimes movecommand doens't do anything, so we just won't add commands that don't do anything
        
    def __get_next(self):
        return self.__next
        
    def __set_next(self, next):
        self.__next = next
        
    next = property(fget=__get_next, fset=__set_next)
 
    def __get_prev(self):
        return self.__prev
        
    def __set_prev(self, prev):
        self.__prev = prev     
        
    prev = property(fget=__get_prev, fset=__set_prev)  
        
    def add_command(self, command):
        self.next = command
        self.next.prev = self
        return command
    
    def has_prev(self):
        return self.prev is not None
    
    def has_next(self):
        return self.next is not None
    
    def __str__(self):
        return '<Unnamed command>'

    def go_prev(self):
        if not self.has_prev():
            return self
        self.unexecute()
        return self.prev
    
    def go_next(self):
        if not self.has_next():
            return self
        self.next.execute()
        return self.next

    def execute(self):
        raise NotImplementedError()
    
    def unexecute(self):
        raise NotImplementedError()
    
class MoveCommand(Command):
    def __init__(self, panel):
        super(MoveCommand, self).__init__()
        self.panel = panel
        self.objects = deque()
        
    def __str__(self):
        return 'Move %d object'%len(self.objects)
        
    def add_object(self, obj):
        self.objects.append([obj, obj.get_position(), None])
        
    def record_move(self):
        self.does_nothing = True
        for lst in self.objects:
            lst[-1] = lst[0].get_position()
            if lst[1] != lst[2]:
                self.does_nothing = False

    def execute(self):
        for obj, pos_before, pos_after in self.objects:
            obj.set_position(*pos_after)
        self.panel.update_bounds()
            
    def unexecute(self):
        for obj, pos_before, pos_after in self.objects:
            obj.set_position(*pos_before)
        self.panel.update_bounds()
        
class ChangePropertiesCommand(Command):
    def __init__(self, panel, obj):
        super(ChangePropertiesCommand, self).__init__()
        self.panel = panel
        self.obj = obj
        self.properties = deque()
    
    def update_field_value(self, field, fr, to):
        if fr == to:
            return
        self.does_nothing = False
        self.properties.append((field, fr, to))
        
    def execute(self):
        self._change_properties()
        
    def unexecute(self):
        self._change_properties(backward=True)
            
    def _change_properties(self, backward=False):
        for field, fr, to in self.properties:
            if backward:
                fr, to = to, fr
            updater = getattr(self.obj, 'update_'+field, None)
            if updater is not None:
                updater(to)
            else:
                setattr(self.obj, field, to)
        
class CreateDeleteObjectCommand(Command):
    """
    Create command does not create anything, it just removes and deletes dependencies, leaving objects in memory
    """
    def __init__(self, panel, obj=None, move_strategy=None, to_delete=False):
        super(CreateDeleteObjectCommand, self).__init__()
        self.to_delete = to_delete
        self.move_strategy = move_strategy
        self.panel = panel
        self.objects = deque()
        if obj is not None:
            self.add_object(obj)
        
    def add_object(self, obj):
        self.objects.append([obj, obj.is_selected])
        
    def execute(self):
        if self.to_delete:
            self._unexecute()
        else:
            self._execute()
        
    def unexecute(self):
        if self.to_delete:
            self._execute()
        else:
            self._unexecute()
        
    def _execute(self):
        arcs_set = set()
        for obj, is_selected in self.objects:
            if isinstance(obj, ArcPoint):
                arcs_set.add(obj.arc)
            obj.restore()
            if self.move_strategy is not None and is_selected:
                self.move_strategy.add_to_selection(obj)
        for arc in arcs_set:
            arc.restore_points()
        
    def _unexecute(self):
        for obj, _ in self.objects:
            obj.prepare_to_delete()
        for obj, _ in self.objects:
            obj.delete()
        

class PetriPanel(wx.ScrolledWindow):
    def __init__(self, parent, frame, strategy_getter, clip_buffer, **kwargs):
        super(PetriPanel, self).__init__(parent, **kwargs)
        self.clip_buffer = clip_buffer
        self.strategy_getter = strategy_getter
        self.frame = frame
        self.SetDoubleBuffered(True)
        self.size = 0, 0
        self.mouse_x = self.mouse_y = 0
        self.first_time = True
        self.commands = Command()
        self.saved_command = self.commands
        self.canvas_size = [1, 1] # w, h
        self.view_point = [0, 0]  # x, y
        self.petri = GUIPetriNet()
        self.filepath = None
        '''
        try:
            self.load_from_file('net.json')
        except:
            self.petri = GUIPetriNet.from_string("""
                # p1::1 p2::2 p3::3 p4::4 p5::5
                p2 -> t1 -> p1 p3
                p1 -> t2 -> p3
                p1 -> t3 -> p4
                p3 p4 -> t4 -> p2
            """)
        '''
        self.update_bounds()
        
        self.Bind(wx.EVT_PAINT, self.on_paint_event)
        self.Bind(wx.EVT_SIZE,  self.on_size_event)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_button_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_button_up)
        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_button_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_button_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_button_up)
        #self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll)
        #self.strategy = MoveAndSelectStrategy(self)
        #self.strategy = SimulateStrategy(self)
        #self.petri.transitions['t1'].set_horizontal(True)
        
        
    @property
    def strategy(self):
        return self.strategy_getter()
    
    @property
    def is_changed(self):
        return self.commands is not self.saved_command
        
    def GetObjectsInRect(self, lx, ly, tx, ty): #ignore labels
        if not self.petri:
            return
        for obj in self.get_objects_iter():
            if isinstance(obj, ObjectLabel):
                continue
            obj.unselect_temporary()
            if obj.in_rect(lx, ly, tx, ty):
                yield obj
        
    def get_name(self):
        result = self.GetName()
        if self.is_changed:
            result = '*'+result
        return result
        
    def load_from_file(self, filepath):
        net = None
        with open(filepath, 'rb') as f:
            json_struct = json.load(f)
        net = GUIPetriNet.from_json_struct(json_struct)
        self.update_title(filepath)
        self.filepath = filepath
        self.petri = net
    
    def update_title(self, filepath):
        basename = osp.basename(filepath)
        title = osp.splitext(basename)[0]
        self.SetName(title)
        
    def save_to_file(self, filepath, net):
        self.update_title(filepath)
        json_struct = net.to_json_struct()
        with open(filepath, 'wb') as f:
            json.dump(json_struct, f)
        self.filepath = filepath
        self.saved_command = self.commands
        
    def on_scroll(self, event):
        orientation = event.GetOrientation()
        event.Skip()
        wx.CallAfter(self.process_scroll_event, orientation)

    def process_scroll_event(self, orientation):
        if not self.strategy.is_moving_objects:
            pos = self.GetScrollPos(orientation)
            rng = self.GetScrollRange(orientation) - self.GetScrollThumb(orientation)
            ind = 1 if orientation == wx.VERTICAL else 0
            new_vp = (float(pos) / rng) * (self.canvas_size[ind] - self.size[ind])
            self.view_point[ind] = int(new_vp)
        
    def append_command(self, command):
        if command.does_nothing:
            return
        self.commands = self.commands.add_command(command)
        self.frame.update_menu()
        
    def undo(self):
        if self.can_undo():
            self.commands = self.commands.go_prev()
            self.Refresh()
            
    def can_undo(self):
        return self.strategy.allow_undo_redo and self.commands.has_prev()
        
    def redo(self):
        if self.can_redo():
            self.commands = self.commands.go_next()
            self.Refresh()
            
    def can_redo(self):
        return self.strategy.allow_undo_redo and self.commands.has_next()
    
    def can_select(self):
        return isinstance(self.strategy, MoveAndSelectStrategy)
    
    can_cut = can_delete = can_paste = can_copy = can_select
    
    def copy(self):
        if self.can_copy():
            self.strategy.on_copy()
            
    def paste(self):
        if self.can_paste():
            self.strategy.on_paste()
            
    def cut(self):
        if self.can_cut():
            self.strategy.on_cut()
            
    def delete(self):
        if self.can_delete():
            self.strategy.on_delete()
            
    def select_all(self):
        if self.can_select():
            self.strategy.on_select_all()
    
    def save(self):
        return self.save_as(filepath=self.filepath)
    
            
    def save_as(self, filepath=None):
        if filepath is None:
            while True:
                dlg = wx.FileDialog(
                    self, message="Save file as ...", 
                    defaultFile="", wildcard='JSON files (*.json)|*.json|All files|*', style=wx.SAVE
                    )
                if dlg.ShowModal() == wx.ID_OK:
                    filepath = dlg.GetPath()
                else:
                    return
                if not osp.exists(filepath):
                    break       
                if not osp.isfile(filepath):
                    continue
                dlg = wx.MessageDialog(self, message='File (%s) already exists. Overwrite it?'%filepath, style=wx.YES_NO|wx.CANCEL|wx.CENTER)
                result = dlg.ShowModal()
                dlg.Destroy()
                if result == wx.ID_YES:
                    break
                elif result == wx.ID_NO:
                    continue
                elif result == wx.ID_CANCEL:
                    return
        if not filepath:
            return
        self.save_to_file(filepath, self.petri)
        return True
        
    def on_size_event(self, event):
        self.size = event.GetSize()
        self.update_bounds()
        self.Refresh()
        
    def on_paint_event(self, event):
        dc = SmartDC(self)
        w, h = self.size
        dc.SetPen(wx.WHITE_PEN)
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.DrawRectangle(0,0,w,h, convert=False)
        self.draw(dc, w, h)
        if self.first_time:
            self.first_time = False
            dc.SetPen(wx.WHITE_PEN)
            dc.SetBrush(wx.WHITE_BRUSH)
            dc.DrawRectangle(0,0,w,h, convert=False)
            self.draw(dc, w, h)
        
    def on_left_button_down(self, event):
        if self.strategy.need_capture_mouse:
            self.mouse_in = True
            self.on_lbutton_timer()
        self.strategy.on_left_down(event)
        self.SetFocus()
        
    def on_right_button_down(self, event):
        self.strategy.on_right_down(event)
        
    def on_right_button_up(self, event):
        self.strategy.on_right_up(event)
        
    def on_left_button_dclick(self, event):
        self.strategy.on_left_dclick(event)
        self.SetFocus()
        
    def on_key_down(self, event):    
        self.strategy.on_key_down(event)

    def on_lbutton_timer(self, *args, **kwargs):
        x, y, w, h = self.GetScreenRect()
        w -= VSCROLL_X
        h -= HSCROLL_Y
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
        for obj in self.get_objects_reversed_iter():
            if obj.contains_point(x, y):
                return obj
        
    def on_mouse_motion(self, event):
        self.strategy.on_motion(event)
        
    def on_left_button_up(self, event):
        self.strategy.on_left_up(event)
        
    def get_objects_iter(self):
        for place in self.petri.get_places_iter():
            yield place
            yield place.label
        for transition in self.petri.get_transitions_iter():
            yield transition
            yield transition.label
        for transition in self.petri.get_transitions_iter():   
            for arc in transition.get_arcs():
                yield arc
                for point in arc.points:
                    yield point
        
    def get_objects_reversed_iter(self):
        for transition in reversed(self.petri.get_transitions()):
            for arc in reversed(transition.get_arcs()):
                for point in reversed(arc.points):
                    yield point
                yield arc
        for transition in reversed(self.petri.get_transitions()):
            yield transition.label
            yield transition
        for place in reversed(self.petri.get_places()):
            yield place.label
            yield place
            
    def update_bounds(self):
        if self.strategy.is_moving_objects:
            return
        max_x, max_y = 0, 0
        for obj in self.get_objects_iter():
            if isinstance(obj, ObjectLabel):
                obj.recalculate_position() #dirty hack
            x,y = obj.get_position()
            w,h = obj.get_size()
            max_x = max(max_x, x+w)
            max_y = max(max_y, y+h)
        max_x = max(max_x+RIGHT_OFFSET, self.size[0]-VSCROLL_X)
        max_y = max(max_y+BOTTOM_OFFSET, self.size[1]-HSCROLL_Y)
        self.canvas_size[0], self.canvas_size[1] = max_x, max_y
        prev_x, prev_y = self.GetScrollPos(wx.HORIZONTAL), self.GetScrollPos(wx.VERTICAL)
        self.SetScrollbars(1, 1, max_x, max_y)
        self.Scroll(prev_x, prev_y)
        self.process_scroll_event(wx.VERTICAL)
        self.process_scroll_event(wx.HORIZONTAL)
        
    def screen_to_canvas_coordinates(self, point):
        x, y = point
        return (x+self.view_point[0], y+self.view_point[1])
    
    def canvas_to_screen_coordinates(self, point):
        x, y = point

        return (x-self.view_point[0], y-self.view_point[1])
            
    def draw(self, dc, w, h):
        for obj in self.get_objects_iter():
            obj.draw(dc)
            
        self.strategy.draw(dc)
        
        """
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawLine(0,0,w,h)
        if self.mouse_pos:
            dc.DrawLine(0, 0, self.mouse_pos[0], self.mouse_pos[1])
        """
        

class Buffer(object):
    def __init__(self):
        self.places = None
        self.transitions = None
    
    def set_content(self, places, transitions):
        self.places = places
        self.transitions = transitions
        
    def reset_content(self):
        self.places = self.transitions = None
        
    def get_content(self):
        return self.places, self.transitions
    
    def is_empty(self):
        return self.places is None and self.transitions is None

class Example(wx.Frame):
    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(500, 500))
        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.clip_buffer = Buffer()
        
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        new_page_item = fileMenu.Append(wx.ID_NEW, '&New\tCtrl+N', 'New Petri net')
        open_item = fileMenu.Append(wx.ID_OPEN, '&Open\tCtrl+O', 'Open petri net')
        close_item = fileMenu.Append(wx.ID_CLOSE, '&Close\tCtrl+W', 'Close current net')
        fileMenu.AppendSeparator()
        save_item = fileMenu.Append(wx.ID_SAVE, '&Save\tCtrl+S', 'Save petri net')
        save_as_item = fileMenu.Append(wx.ID_SAVEAS, 'S&ave as\tCtrl+Shift+S', 'Save petri net as')
        fileMenu.AppendSeparator()
        quit_item = fileMenu.Append(wx.ID_EXIT, '&Quit\tCtrl+Q', 'Quit application')
        menubar.Append(fileMenu, '&File')
        editMenu = wx.Menu()
        self.undo_item = editMenu.Append(wx.ID_UNDO, '&Undo\tCtrl+Z', 'Undo last action')
        self.redo_item = editMenu.Append(wx.ID_REDO, '&Redo\tCtrl+Y', 'Redo last action')
        editMenu.AppendSeparator()
        self.cut_item = editMenu.Append(wx.ID_CUT, '&Cut\tCtrl+X', 'Cut elements')
        self.copy_item = editMenu.Append(wx.ID_COPY, 'C&opy\tCtrl+C', 'Copy elements')
        self.paste_item = editMenu.Append(wx.ID_PASTE, '&Paste\tCtrl+V', 'Paste elements')
        self.delete_item = editMenu.Append(wx.ID_DELETE, '&Delete\tDelete', 'Delete elements')
        editMenu.AppendSeparator()
        self.select_all_item = editMenu.Append(wx.ID_SELECTALL, '&Select all\tCtrl+A', 'Select all elements')
        menubar.Append(editMenu, '&Edit')
        #analysisMenu = wx.Menu()

        self.SetMenuBar(menubar)
        # Menu bindings
        # File
        self.Bind(wx.EVT_MENU, self.OnNew, new_page_item)
        self.Bind(wx.EVT_MENU, self.OnOpen, open_item)
        self.Bind(wx.EVT_MENU, self.OnClose, close_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnSave, save_item)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, save_as_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnQuit, quit_item)
        # Edit
        self.Bind(wx.EVT_MENU, self.OnUndo, self.undo_item)
        self.Bind(wx.EVT_MENU, self.OnRedo, self.redo_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnCut, self.cut_item)
        self.Bind(wx.EVT_MENU, self.OnCopy, self.copy_item)
        self.Bind(wx.EVT_MENU, self.OnPaste, self.paste_item)
        self.Bind(wx.EVT_MENU, self.OnDelete, self.delete_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnSelectAll, self.select_all_item)
        # Bind close
        self.Bind(wx.EVT_CLOSE, self.OnQuit)
        # Button bitmaps
        bmp_mouse = wx.Bitmap("icons/arrow.png", wx.BITMAP_TYPE_ANY)
        bmp_animate = wx.Bitmap("icons/animate.png", wx.BITMAP_TYPE_ANY)
        bmp_newplace = wx.Bitmap("icons/addplace.png", wx.BITMAP_TYPE_ANY)
        bmp_newtransition = wx.Bitmap("icons/addtransition.png", wx.BITMAP_TYPE_ANY)
        bmp_newarc = wx.Bitmap("icons/addarc.png", wx.BITMAP_TYPE_ANY)
        
        mouse_button = buttons.GenBitmapToggleButton(self, bitmap=bmp_mouse)
        
        self.buttons = [(mouse_button, MoveAndSelectStrategy(self.panel_getter)),
                         (buttons.GenBitmapToggleButton(self, bitmap=bmp_animate), SimulateStrategy(self.panel_getter)),
                         (buttons.GenBitmapToggleButton(self, bitmap=bmp_newplace), AddPlaceStrategy(self.panel_getter)),
                         (buttons.GenBitmapToggleButton(self, bitmap=bmp_newtransition), AddTransitionStrategy(self.panel_getter)),
                         (buttons.GenBitmapToggleButton(self, bitmap=bmp_newarc), AddArcStrategy(self.panel_getter)),
                         ]
        
        for button,_ in self.buttons:
            buttons_sizer.Add(button)
            self.Bind(wx.EVT_BUTTON, self.on_toggle_button)
            
        self.buttons = dict(self.buttons)
        
        self.strategy = self.buttons[mouse_button]
            
        self.toggle_button(mouse_button)
            
        vert_sizer.Add(buttons_sizer)
        self.tabs = wx.aui.AuiNotebook(self)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnPageChanged, self.tabs)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnPageClose, self.tabs)
        self._unnamed_count = 0
        self.add_new_page()
        vert_sizer.Add(self.tabs, proportion=1, flag=wx.EXPAND|wx.TOP, border=1)
        self.SetSizer(vert_sizer)
        self.Centre() 
        self.Show()
        
    def create_new_panel(self, title=None):
        return PetriPanel(self.tabs, name=title, frame=self, strategy_getter=self.strategy_getter, clip_buffer=self.clip_buffer)
        
    def add_new_page(self, title=None):
        if not title:
            self._unnamed_count += 1
            title = 'Petri net %s'%(str(self._unnamed_count) if self._unnamed_count else '')
        petri_panel = self.create_new_panel(title)
        self.tabs.AddPage(petri_panel, petri_panel.get_name(), select=True)
                
    def panel_getter(self):
        return self.tabs.GetPage(self.tabs.Selection)
    
    petri_panel = property(panel_getter)
    
    def strategy_getter(self):
        return self.strategy
        
    def toggle_button(self, button_on):
        button_on.SetValue(True)
        for button in self.buttons:
            if button!=button_on:
                button.SetValue(False)
                
    def on_toggle_button(self, event):
        button_on = event.GetEventObject()
        if not button_on.GetValue(): #can't untoggle 
            button_on.SetValue(True)
            return
        for button in self.buttons:
            if button != button_on:
                button.SetValue(False)
        self.strategy.on_switched_strategy()
        self.strategy = self.buttons[button_on]
        self.update_menu()
        self.petri_panel.SetFocus()
        
    def OnUndo(self, event):
        self.petri_panel.undo()
        self.update_menu()
        
    def OnCut(self, event):
        self.petri_panel.cut()
        self.update_menu()
    
    def OnCopy(self, event):
        self.petri_panel.copy()
        self.update_menu()
    
    def OnPaste(self, event):
        self.petri_panel.paste()
        self.update_menu()
    
    def OnDelete(self, event):
        self.petri_panel.delete()
    
    def OnNew(self, event):
        self.add_new_page()
        
    def OnSelectAll(self, event):
        self.petri_panel.select_all()
        
    def update_menu(self):
        self.refresh_undo_redo()
        tab_name = self.petri_panel.get_name()
        self.tabs.SetPageText(self.tabs.Selection, tab_name)
        
    def refresh_undo_redo(self):
        self.redo_item.Enable(self.petri_panel.can_redo())
        self.undo_item.Enable(self.petri_panel.can_undo())
        self.paste_item.Enable(not self.clip_buffer.is_empty() and self.petri_panel.can_paste())
        self.cut_item.Enable(self.petri_panel.can_cut())
        self.copy_item.Enable(self.petri_panel.can_copy())
        self.delete_item.Enable(self.petri_panel.can_delete())
        self.select_all_item.Enable(self.petri_panel.can_select())
        
    def OnPageClose(self, event):
        if not self.close_tab(event.Selection):
            event.Veto()
        
    def OnOpen(self, event):
        dlg = wx.FileDialog(
            self, message="Open file", 
            defaultFile="", wildcard='JSON files (*.json)|*.json|All files|*', style=wx.OPEN
            )
        if dlg.ShowModal() != wx.ID_OK:
            return
        filepath = dlg.GetPath()
        panel = self.create_new_panel('unnamed')
        try:
            panel.load_from_file(filepath)
        except Exception, e:
            self.DisplayError('Error while loading petri net:\n%s'%traceback.format_exc(), title='Error while opening file')
        else:
            self.tabs.AddPage(panel, panel.get_name(), select=True)
        
    def close_tab(self, pos):
        """ Returns false if user decided not to close the tab """
        tab = self.tabs.GetPage(pos)
        if not tab.is_changed:
            return True
        dlg = wx.MessageDialog(self, message='There are unsaved changes in "%s". Save?'%tab.get_name(), style=wx.YES_NO|wx.CANCEL|wx.CENTER)
        result = dlg.ShowModal()
        if result == wx.ID_YES:
            tab.save()
        elif result == wx.ID_CANCEL:
            return False
        return True
        
    def OnClose(self, event):
        if self.close_tab(self.tabs.Selection):
            self.tabs.DeletePage(self.tabs.Selection)
            
        
    def DisplayError(self, message, title='Error'):
        wx.MessageBox(message=message, caption=title, style=wx.ICON_ERROR)
        
        
    def OnSave(self, event):
        try:
            self.petri_panel.save()
        except Exception, e:
            self.DisplayError('Error while saving petri net:\n%s'%traceback.format_exc(), title='Error while saving file')
        self.update_menu()
        
    def OnSaveAs(self, event):
        try:
            self.petri_panel.save_as()
        except Exception, e:
            self.DisplayError('Error while saving petri net:\n%s'%traceback.format_exc(), title='Error while saving file')
        self.update_menu()
        
    def OnPageChanged(self, event):
        self.update_menu()
        self.petri_panel.SetFocus()
        
    def OnRedo(self, event):
        self.petri_panel.redo()
        self.update_menu()
        
    def quit(self):
        page_count = self.tabs.GetPageCount()
        for i in xrange(page_count):
            tab = self.tabs.GetPage(i)
            if not tab.is_changed:
                continue
            self.tabs.Selection = i
            if not self.close_tab(i):
                return False
        return True
        
    def OnQuit(self, event):
        if self.quit():
            self.Destroy()
        


if __name__ == '__main__':
    Example(None, 'Line')
    #import wx.lib.inspection
    #wx.lib.inspection.InspectionTool().Show()
    app.MainLoop()
    '''
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
    
    rint net1.to_json_struct()
    '''
    