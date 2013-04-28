
from objects_canvas.strategy import Strategy, MenuStrategyMixin, PropertiesMixin
from commands.create_delete_command import CreateDeleteObjectCommand
from petri import petri
from petri_objects import GUIArc


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
        
class AddArcStrategy(MenuStrategyMixin, Strategy):
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

    def draw(self, dc, zoom):
        if self.arc is not None:
            self.arc.draw(dc, zoom=zoom)
            
    def on_switched_strategy(self):
        super(AddArcStrategy, self).on_switched_strategy()
        self.reset()
        self.panel.Refresh()