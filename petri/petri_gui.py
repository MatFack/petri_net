#!/usr/bin/python
# -*- coding: utf-8 -*-

import wx
import traceback
import time
import petri



class PositionedPlace(petri.Place):
    pos_to_serialize = True
    def __init__(self, unique_id=None, tokens=0, position=None):
        """
        unique_id - unique identifier (hash if None)
        tokens - number of tokens in initial marking
        position - (x,y)
        """
        super(PositionedPlace, self).__init__(unique_id=unique_id, tokens=tokens)
        self.pos = position
        
class PositionedTransition(petri.Transition):
    pos_to_serialize = True
    def __init__(self, unique_id=None, position=None, input_arcs=None, output_arcs=None, net=None):
        super(PositionedTransition,self).__init__(unique_id=unique_id, input_arcs=input_arcs, output_arcs=output_arcs, net=net)
        self.pos = position

class GUIPetriNet(petri.PetriNet):
    PLACE_CLS = PositionedPlace
    TRANSITION_CLS = PositionedTransition
        

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
        self.mouse_pos = None
        self.left_down = False
        
        self.petri = petri.PetriNet()
        
        
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
        self.mouse_pos = event.m_x,event.m_y
        self.left_down = True
        self.Refresh()
        
    def on_mouse_motion(self, event):
        self.mouse_pos = event.m_x,event.m_y
        if self.left_down:
            self.Refresh()
        
    def on_left_button_up(self, event):
        self.mouse_pos = event.m_x,event.m_y
        self.left_down = False
        self.Refresh()
        
    def draw(self, dc, w, h):
        """
        dc.SetPen(wx.BLACK_PEN)
        dc.DrawLine(0,0,w,h)
        if self.mouse_pos:
            dc.DrawLine(0, 0, self.mouse_pos[0], self.mouse_pos[1])"""
        
        

class Example(wx.Frame):
    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(250, 150))

        self.petri_panel = PetriPanel(self)

        self.Centre() 
        self.Show()


if __name__ == '__main__':
    """
    app = wx.App()
    Example(None, 'Line')
    app.MainLoop()
    """
    p  =PositionedPlace('p1', 1, (100,100))
    x = p.to_json_struct()
    p2 = PositionedPlace.from_json_struct(x, unique_id='p1')
    
    net1 = GUIPetriNet.from_string("""
    # 
    p2 -> t1 -> p1 p3
    p1 -> t2 -> p3
    p1 -> t3 -> p4
    p3 p4 -> t4 -> p2
    """,)
    
    print net1.to_json_struct()
    