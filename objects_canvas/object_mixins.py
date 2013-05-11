

import wx

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
        #x -= x % 2
        #y -= y % 2
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
        
class HighlightingMixin(object):
    def __init__(self, *args, **kwargs):
        self.highlighted = None
        super(HighlightingMixin, self).__init__(*args, **kwargs)
        
    def highlight(self, value):
        self.highlighted = value
                
    def unhighlight(self):
        self.highlighted = None
        
        
class SelectionMixin(object):
    def __init__(self, *args, **kwargs):
        self.selected = False
        self.temporary_selected = False
        self.temporary_discarded = False
        super(SelectionMixin, self).__init__(*args, **kwargs)
        
    @property
    def is_selected(self):
        return False if self.temporary_discarded else self.selected or self.temporary_selected
    
    def is_selectable(self):
        return True
        
    def unselect_temporary(self):
        self.temporary_discarded = self.temporary_selected = False
        
    def set_selected(self, selected):
        if not selected:
            self.unselect_temporary()
        self.selected = selected
        

        
class MenuMixin(object):
    def spawn_context_menu(self, parent, event, canvas_pos):
        self.menu_parent = parent
        self.menu_event = event
        self.menu_canvas_pos = canvas_pos
        menu = wx.Menu()
        for event_id, (name, handler) in self.menu_fields.iteritems():
            menu.Append(event_id, name)
            parent.Bind(wx.EVT_MENU, handler, id=event_id)
        parent.PopupMenu(menu, event.GetPositionTuple())
        menu.Destroy()
        for event_id, (name, handler) in self.menu_fields.iteritems():
            parent.Unbind(wx.EVT_MENU, id=event_id)
        parent.Refresh()
        
        
