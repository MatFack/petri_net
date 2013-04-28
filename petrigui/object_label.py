
from object_mixins import SelectionMixin, PositionMixin


from util import serializable

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
        
    def is_selectable(self):
        return False
        
    def draw(self, dc, zoom):
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
