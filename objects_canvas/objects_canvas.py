
import wx
import os.path as osp
from smart_dc import SmartDC
from commands.command import Command
from util import constants

class ObjectsCanvas(wx.ScrolledWindow):
    def __init__(self, parent, frame, **kwargs):
        """ Constructor must be called after objects_container is set!!! """
        super(ObjectsCanvas, self).__init__(parent, **kwargs)
        self.frame = frame
        self.SetDoubleBuffered(True)
        self.size = 0, 0
        self.SetName("ObjectCanvas")
        self.commands = Command()
        self.saved_command = self.commands
        self.canvas_size = [1, 1] # w, h
        self.view_point = [0, 0]  # x, y
        self.filepath = None
        self.zoom = 1
        self.update_bounds()
        self.do_bindings()
        
    def zoom_out(self):
        if self.zoom >=0.25:
            self.zoom -= 0.1
            self.update_bounds()
            self.Refresh()
            
    def zoom_in(self):
        self.zoom += 0.1
        self.update_bounds()
        self.Refresh()
        
    def zoom_restore(self):
        self.zoom = 1
        self.update_bounds()
        self.Refresh()
        
    @property
    def strategy(self):
        return self.frame.strategy
        
    def do_bindings(self):
        self.Bind(wx.EVT_PAINT, self.on_paint_event)
        self.Bind(wx.EVT_SIZE,  self.on_size_event)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_button_down)
        self.Bind(wx.EVT_LEFT_UP, self.on_left_button_up)
        self.Bind(wx.EVT_MOTION, self.on_mouse_motion)
        self.Bind(wx.EVT_LEFT_DCLICK, self.on_left_button_dclick)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_button_down)
        self.Bind(wx.EVT_RIGHT_UP, self.on_right_button_up)
        self.Bind(wx.EVT_SCROLLWIN, self.on_scroll)
    
    @property
    def is_changed(self):
        return self.commands is not self.saved_command
    
    @property
    def has_unsaved_changes(self):
        if self.is_changed:
            return True
        if self.filepath is None:
            if self.petri.places or self.petri.transitions:
                return True
        return False
        
    def GetObjectsInRect(self, lx, ly, tx, ty):
        for obj in self.get_objects_iter():
            if not obj.is_selectable():
                continue
            obj.unselect_temporary()
            if obj.in_rect(lx, ly, tx, ty):
                yield obj
        
    def get_name(self):
        result = self.GetName()
        if self.has_unsaved_changes:
            result = '*'+result
        return result
        
    def load_from_file(self, filepath, format):
        net = None
        with open(filepath, 'rb') as f:
            data = f.read()
        net = format.import_net(data)
        self.update_title(filepath)
        self.filepath = filepath
        self.petri = net
    
    def update_title(self, filepath):
        basename = osp.basename(filepath)
        title = osp.splitext(basename)[0]
        self.SetName(title)
        
    def save_to_file(self, filepath, net, format):
        if format.persistent:
            self.update_title(filepath)
        data = format.export_net(net)
        with open(filepath, 'wb') as f:
            f.write(data)
        if format.persistent:
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
            if rng==0:
                self.Refresh()
                return
            ind = 1 if orientation == wx.VERTICAL else 0
            new_vp = (float(pos) / rng) * (self.canvas_size[ind] - self.size[ind])
            self.view_point[ind] = int(new_vp)
            self.Refresh()
            
    def append_command(self, command):
        if command.does_nothing:
            return
        self.commands = self.commands.add_command(command)
        self.frame.update_menu()
        
    def update_frame_menu(self):
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
        return self.strategy.can_select
    
    can_cut = can_delete = can_paste = can_copy = can_select
    
    def copy(self):
        if self.can_copy():
            self.on_copy()
        
    def on_copy(self):
        raise NotImplementedError
            
    def paste(self):
        if self.can_paste():
            self.on_paste()
            
    def on_paste(self):
        raise NotImplementedError
            
    def cut(self):
        if self.can_cut():
            self.on_cut()
            
    def on_cut(self):
        raise NotImplementedError
            
    def delete(self):
        if self.can_delete():
            self.on_delete()
            
    def on_delete(self):
        raise NotImplementedError
            
    def select_all(self):
        if self.can_select():
            self.strategy.on_select_all()
    
    def save(self, format):
        return self.save_as(filepath=self.filepath, format=format)
    
            
    def save_as(self, format, filepath=None):
        if filepath is None:
            while True:
                print format
                dlg = wx.FileDialog(
                    self, message="Save file as ...", 
                    defaultFile="", wildcard=format.get_wildcard(), style=wx.SAVE
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
        self.save_to_file(filepath, self.petri, format=format)
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
        dc.DrawRectangleOnScreen(0,0,w,h)
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
        """ Dirty hack to catch the moment when mouse leaves window and capture it. wx.EVT_LEAVE_WINDOW is not always sent. """
        x, y, w, h = self.GetScreenRect()
        w -= constants.VSCROLL_X
        h -= constants.HSCROLL_Y
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
        """ Gets object under given virtual position """
        # Check in reverse order so the topmost object will be selected
        for obj in self.get_objects_reversed_iter():
            if obj.contains_point(x, y):
                return obj
        
    def on_mouse_motion(self, event):
        self.strategy.on_motion(event)
        
    def on_left_button_up(self, event):
        self.strategy.on_left_up(event)
        
    def get_objects_iter(self):
        raise NotImplementedError
        
    def get_objects_reversed_iter(self):
        raise NotImplementedError
            
    def update_bounds(self):
        """ Update canvas size and adjust scrollbars to it """
        if self.strategy.is_moving_objects:
            # Do not update when user is moving something, because it will cause mess.
            return
        max_x, max_y = 0, 0
        for obj in self.get_objects_iter():
            x,y = obj.get_position()
            w,h = obj.get_size()
            max_x = max(max_x, x+w)
            max_y = max(max_y, y+h)
        max_x = max_x * self.zoom
        max_y = max_y * self.zoom
        max_x = max(max_x+constants.RIGHT_OFFSET, self.size[0]-constants.VSCROLL_X)
        max_y = max(max_y+constants.BOTTOM_OFFSET, self.size[1]-constants.HSCROLL_Y)
        self.canvas_size[0], self.canvas_size[1] = max_x, max_y
        prev_x, prev_y = self.GetScrollPos(wx.HORIZONTAL), self.GetScrollPos(wx.VERTICAL)
        self.SetScrollbars(1, 1, max_x, max_y)
        self.Scroll(prev_x, prev_y)
        self.process_scroll_event(wx.VERTICAL)
        self.process_scroll_event(wx.HORIZONTAL)
        
    def screen_to_canvas_coordinates(self, point):
        x, y = point
        x = x / self.zoom
        y = y / self.zoom
        return (x+self.view_point[0], y+self.view_point[1])
    
    def canvas_to_screen_coordinates(self, point):
        x, y = point
        x = x * self.zoom
        y = y * self.zoom
        return (x-self.view_point[0], y-self.view_point[1])
            
    def draw(self, dc, w, h):
        for obj in self.get_objects_iter():
            obj.draw(dc, self.zoom)
        self.strategy.draw(dc, self.zoom)
