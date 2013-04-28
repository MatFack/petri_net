

from strategy import PropertiesMixin, Strategy
import wx
from commands.move_command import MoveCommand


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
        self.can_select = True
        
    def on_key_down(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_DELETE:
            self.on_delete()
        elif keycode == wx.WXK_RETURN:
            if len(self.selection) == 1:
                for obj in self.selection:
                    obj.open_properties_dialog(self.panel)
        
    def on_select_all(self):
        for obj in self.panel.get_objects_iter():
            if obj.is_selectable():
                self.add_to_selection(obj)
        self.panel.Refresh()
        
    def on_left_down(self, event):
        super(MoveAndSelectStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if obj and not obj.is_selectable():
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
        obj.spawn_context_menu(self.panel, event, (self.mouse_x, self.mouse_y))

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
        
    def draw(self, dc, zoom):
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
