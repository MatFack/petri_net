

class Strategy(object):
    def __init__(self, panel):
        self._panel = panel
        self.left_down = False
        self.right_down = False
        self.mouse_x, self.mouse_y = 0, 0
        self.need_capture_mouse = False
        self.is_moving_objects = False
        self.allow_undo_redo = True
        self.can_select = False
        
        
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
        
    def draw(self, dc, zoom):
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
        
class MenuStrategyMixin(object):
    def on_right_down(self, event):
        super(MenuStrategyMixin, self).on_right_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if obj is not None:
            obj.spawn_context_menu(self.panel, event, (self.mouse_x, self.mouse_y))
            
