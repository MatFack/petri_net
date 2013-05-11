
from objects_canvas.objects_canvas import ObjectsCanvas
from petri_objects import GUIPetriNet
from collections import deque
from petri import petri
import itertools
import wx

from commands.create_delete_command import CreateDeleteObjectCommand

class PetriPanel(ObjectsCanvas):
    def __init__(self, parent, frame, clip_buffer, **kwargs):
        self.petri = GUIPetriNet()
        super(PetriPanel, self).__init__(parent, frame=frame, **kwargs)
        self.SetName("Petri net")
        self.clip_buffer = clip_buffer
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        
    def OnSetFocus(self, event):
        self.set_temporary_state(None)
        self.discard_highlighted()
        
    def discard_highlighted(self):
        for obj in self.highlightable_objects_iter():
            obj.unhighlight()
    
    def __petri_get(self):
        return self.objects_container
    
    def __petri_set(self, value):
        self.objects_container = value
        
    petri = property(fget=__petri_get, fset=__petri_set)
    
    def highlight_objects(self, objects_dct):
        self.discard_highlighted()
        for obj, value in objects_dct.iteritems():
            obj.highlight(value)
        self.Refresh()
    
    def set_temporary_state(self, marking):
        if marking:
            for place, token in zip(self.petri.get_sorted_places(), marking):
                place.set_temporary_tokens(token)
        else:
            for place in self.petri.get_sorted_places():
                place.set_temporary_tokens(None)
        self.Refresh()
        
    def highlightable_objects_iter(self):
        for place in self.petri.get_places_iter():
            yield place
        for transition in self.petri.get_transitions_iter():
            yield transition
    
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
            
            
    def on_cut(self):
        self.on_copy()
        self.on_delete()
                
    def on_copy(self):
        places_set = set()
        places = deque()
        transitions_objects = deque()
        transitions = deque()
        for obj in self.strategy.selection:
            if isinstance(obj, petri.Place):
                places.append((obj.__class__,obj.to_json_struct()))
                places_set.add(obj)
            elif isinstance(obj, petri.Transition):
                transitions_objects.append(obj)
        if not places_set and not transitions_objects:
            return
        for transition in transitions_objects:
            transitions.append((transition.__class__, transition.to_json_struct(only_arcs_with_places=places_set)))
        self.clip_buffer.set_content(places=places, transitions=transitions)
        
    def on_paste(self):
        places, transitions = self.clip_buffer.get_content()
        if not places and not transitions:
            return
        self.strategy.discard_selection()
        command = CreateDeleteObjectCommand(self, move_strategy=self.strategy)
        objects = deque()
        places_dct = {}
        
        net = self.petri
        for cls, place_obj in places:
            place = cls.from_json_struct(place_obj, constructor_args=dict(net=net))
            place_name = place.unique_id
            k = 1
            while place.unique_id in net.places:
                place.unique_id = '%s (%d)'%(place_name, k)
                k += 1
            places_dct[place_name] = place
            net.add_place(place)
            self.strategy.add_to_selection(place)
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
            self.strategy.add_to_selection(transition)
            for arc in itertools.chain(transition.input_arcs, transition.output_arcs):
                for point in arc.points:
                    self.strategy.add_to_selection(point)
            command.add_object(transition)
            objects.append(transition)
        min_x = min_y = None, None
        for obj in objects:
            x, y = obj.get_topleft_position()
            if min_x is None or x < min_x: min_x = x
            if min_x is None or y < min_y: min_y = y
        vx, vy = self.view_point
        for obj in objects:
            obj.shift(-min_x+40+vx, -min_y+40+vy)
        self.append_command(command)
        self.update_bounds()
        self.Refresh()
        
    def on_petri_changed(self):
        self.frame.on_state_changed()
        
    def on_delete(self):
        if not self.strategy.selection:
            return
        net = self.petri
        to_delete = set()
        for obj in self.strategy.selection:
            to_delete.add(obj)
            to_delete.update(obj.get_depending_objects())
        command = CreateDeleteObjectCommand(self, move_strategy=self.strategy, to_delete=True)
        for obj in to_delete:
            command.add_object(obj)
        command.execute()
        self.append_command(command)
        self.update_bounds()
        self.strategy.discard_selection()
        self.Refresh()

