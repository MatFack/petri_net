# -*- coding: utf-8 -*-

import json
from util.serializable import Serializable, RequiredException
from timeit import itertools

    
class Arc(Serializable):
    """
    An arc from transition to place.
    If weight<0, the arc is considered to be output, else input
    """
    weight_to_serialize = True

    def __init__(self, net, place=None, transition=None, weight=0):
        self.net=net
        self.place = place
        self.transition = transition
        self.weight = weight
        
    
    def is_sufficient(self):
        return self.place.tokens >= self.weight
    
    def place_to_json_struct(self, **kwargs):
        return self.place.unique_id
    
    def move_tokens(self):
        abs_weight = abs(self.weight)
        if self.weight>0:
            self.place.remove_tokens(abs_weight)
        elif self.weight<0:
            self.place.add_tokens(abs_weight)
    
    def place_from_json_struct(self, place_obj, places_dct, **kwargs):
        return places_dct[place_obj]
    
    def prepare_to_delete(self):
        pass
    
    def delete(self):
        self.transition.delete_arc(self)
        
    def restore(self):
        self.transition.add_arc(self)
        
    def post_restore(self):
        pass

    @property
    def is_input_arc(self):
        return self.weight>0
    
    def can_append(self, place=None, transition=None):
        place = place or self.place
        transition = transition or self.transition
        if self.is_input_arc:
            arcs_set = transition.input_arcs
        else:
            arcs_set = transition.output_arcs
        for arc in arcs_set:
            if arc.place == place:
                return False
        return True
    
    def inject(self):
        self.transition.add_arc(self)
    


class Transition(Serializable):
    ARC_CLS = Arc
    
    unique_id_to_serialize = True
    def __init__(self, net, unique_id=None, input_arcs=None, output_arcs=None):
        """
            unique_id - unique identifier (hash if None)
            input_arcs, output_arcs - dictionary
                { place : weight }
            net - petri net (only if arcs are represented as strings)
        """
        self.net = net
        self.input_arcs = self._convert_arcs(input_arcs, is_input=True)
        self.arcs_cache = None
        self.output_arcs = self._convert_arcs(output_arcs, is_input=False)
        self.unique_id = hash(self) if unique_id is None else unique_id
        
    def _convert_arcs(self, arcs, is_input):
        if isinstance(arcs, basestring):
            return set(self._str_to_arc(arc, is_input) for arc in arcs.split())
        else:
            return set(arcs or [])
    
    def _str_to_arc(self, arc_str, is_input):
        if '::' in arc_str:
            place_name, _, weight = arc_str.rpartition('::')
            weight = int(weight)
        else:
            place_name = arc_str
            weight = 1
        if not is_input:
            weight = -weight
        place = self.net.get_or_create_place(place_name)
        return self.__class__.ARC_CLS(net=self.net, place=place, transition=self, weight=weight)
            
    def get_arcs(self):
        if self.arcs_cache is None:
            self.arcs_cache = list(self.input_arcs) + list(self.output_arcs)            
        return self.arcs_cache
        
    @property
    def is_enabled(self):
        return all(arc.is_sufficient() for arc in self.input_arcs)
    
    def add_arc(self, arc):
        if arc.is_input_arc:
            arc_set = self.input_arcs
        else:
            arc_set = self.output_arcs
        arc_set.add(arc)
        self.arcs_cache = None
    
    def delete_arc(self, arc):
        if arc.is_input_arc:
            arc_set = self.input_arcs
        else:
            arc_set = self.output_arcs
        arc_set.remove(arc)
        self.arcs_cache = None
        
    def prepare_to_delete(self):
        pass
        
    def delete(self):
        self.net.remove_transition(self.unique_id)
        
    def restore(self):
        self.net.add_transition(self)
        
    def post_restore(self):
        pass
    
    def fire(self):
        """
            Fire the transition. It's assumed that it can fire.
        """
        assert(self.is_enabled)
        for arc in self.input_arcs:
            arc.move_tokens()
        for arc in self.output_arcs:
            arc.move_tokens()
            
    # Serialization routines
            
    def input_arcs_to_json_struct(self, only_arcs_with_places=None, **kwargs):
        return [arc.to_json_struct() for arc in self.input_arcs if only_arcs_with_places is None or arc.place in only_arcs_with_places]
    
    def output_arcs_to_json_struct(self, only_arcs_with_places=None, **kwargs):
        return [arc.to_json_struct(**kwargs) for arc in self.output_arcs if only_arcs_with_places is None or arc.place in only_arcs_with_places]
    
    def input_arcs_from_json_struct(self, input_arcs_obj, places_dct, **kwargs):
        input_arcs = []
        for obj in input_arcs_obj:
            constructor_args = dict(net=self.net, transition=self)
            arc = self.ARC_CLS.from_json_struct(obj, constructor_args, places_dct=places_dct, **kwargs)
            input_arcs.append(arc)
        return set(input_arcs)
    
    def output_arcs_from_json_struct(self, output_arcs_obj, places_dct, **kwargs):
        output_arcs = []
        for obj in output_arcs_obj:
            constructor_args = dict(net=self.net, transition=self)
            arc = self.ARC_CLS.from_json_struct(obj, constructor_args, places_dct=places_dct, **kwargs)
            output_arcs.append(arc)
        return set(output_arcs)
        
        
class Place(Serializable):
    tokens_to_serialize = True
    unique_id_to_serialize = True
    
    def __init__(self, net, unique_id=None, tokens=0):
        """
        unique_id - unique identifier (hash if None)
        tokens - number of tokens in initial marking
        """
        self.net = net
        self.tokens = tokens
        tokens+1,tokens-1
        assert(tokens>=0)
        self.unique_id = hash(self) if unique_id is None else unique_id
        
    def remove_tokens(self, tokens):
        assert(tokens>0)
        assert(self.tokens >= tokens)
        self.tokens -= tokens
    
    def add_tokens(self, tokens):
        assert(tokens>0)
        self.tokens += tokens    
        
    def prepare_to_delete(self):
        pass
        
    def delete(self):
        self.net.remove_place(self.unique_id)
        
    def restore(self):
        self.net.add_place(self)
        
    def post_restore(self):
        pass
        
    def get_arcs(self):
        for transition in self.net.get_transitions():
            for arc in transition.get_arcs():
                if arc.place == self:
                    yield arc
        
    def __repr__(self):
        return "%s(%r,%r)" % (self.__class__.__name__, self.tokens,self.unique_id)
    
    __str__ = __repr__
    
    
class PetriNet(Serializable):
    PLACE_CLS = Place
    TRANSITION_CLS = Transition
    
    def __init__(self, places=None, transitions=None):
        self.places = dict(places or {})
        self.transitions = dict(transitions or {}) 
        self.cached_places = None
        self.cached_transitions = None
        self.cached_sorted_places = None
        self.cached_sorted_transitions = None
        
        
    def add_place(self, place):
        assert(place.unique_id not in self.places)
        self.places[place.unique_id] = place
        self.on_places_changed()
        
    def on_places_changed(self):
        self.cached_places = None
        self.cached_sorted_places = None
        
    def on_transitions_changed(self):
        self.cached_transitions = None
        self.cached_sorted_transitions = None
        
    def remove_place(self, place_name):
        result = self.places.pop(place_name)
        self.on_places_changed()
        return result
        
    def add_transition(self, transition):
        assert(transition.unique_id not in self.transitions)
        self.transitions[transition.unique_id] = transition
        self.on_transitions_changed()
        
    def remove_transition(self, transition_name):
        result = self.transitions.pop(transition_name)
        self.on_transitions_changed()
        return result
        
    def get_places_iter(self):
        for place in self.places.itervalues():
            yield place
            
    def get_transitions_iter(self):
        for transition in self.transitions.itervalues():
            yield transition
            
    def get_places(self):
        if self.cached_places is None:
            self.cached_places = self.places.values()
        return self.cached_places
    
    def get_transitions(self):
        if self.cached_transitions is None:
            self.cached_transitions = self.transitions.values()
        return self.cached_transitions
        
    def get_sorted_places(self):
        if self.cached_sorted_places is None:
            self.cached_sorted_places = [self.places[key] for key in sorted(self.places.keys())]
        return self.cached_sorted_places
    
    def get_sorted_transitions(self):
        if self.cached_sorted_transitions is None:
            self.cached_sorted_transitions = [self.transitions[key] for key in sorted(self.transitions.keys())]
        return self.cached_sorted_transitions
    
    def get_state(self):
        return tuple(place.tokens for place in self.get_sorted_places())
        
    def __getitem__(self, key):
        return self.places[key]
        
    def new_place(self, *args, **kwargs):
        """
            Creates a place and immediately adds it to this petri net
        """
        kwargs['net'] = self
        p = self.__class__.PLACE_CLS(*args, **kwargs)
        self.add_place(p)
        return p
    
    def new_transition(self, *args, **kwargs):
        """
            Creates a transition and immediately adds it to this petri net
        """
        kwargs['net'] = self
        t = self.__class__.TRANSITION_CLS(*args, **kwargs)
        self.add_transition(t)
        return t
        
    def transitions_to_json_struct(self, **kwargs):
        return [transition.to_json_struct(**kwargs) for transition in self.transitions.itervalues()]
        
    def places_to_json_struct(self, **kwargs):
        return [place.to_json_struct(**kwargs) for place in self.places.itervalues()]
    
    def places_from_json_struct(self, places_obj, **kwargs):
        places = {}
        for place_obj in places_obj:
            constructor_args = dict(net=self)
            place_obj = self.PLACE_CLS.from_json_struct(place_obj, constructor_args=constructor_args)
            places[place_obj.unique_id] = place_obj
        self.places_deserialized = True
        return places
    
    def transitions_from_json_struct(self, transitions_obj, **kwargs):
        if not getattr(self, 'places_deserialized', False):
            raise RequiredException('places')
        del self.places_deserialized
        transitions = {}
        for transition_obj in transitions_obj:
            constructor_args = dict(net=self)
            transition_obj = self.TRANSITION_CLS.from_json_struct(transition_obj, places_dct=self.places, constructor_args=constructor_args)
            transitions[transition_obj.unique_id] = transition_obj
        return transitions
    
    def get_or_create_place(self, place_name):
        if place_name in self.places:
            return self.places[place_name]
        place = self.new_place(net=self, unique_id=place_name)
        return place
    
    @classmethod
    def from_string(cls, s):
        lines = s.split('\n')
        net = cls()
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                line = line[1:]
                for place in line.split():
                    tokens = 0
                    if '::' in place:
                        name, _, tokens = place.partition('::')
                    else:
                        name = place
                    tokens = int(tokens)
                    if name not in net.places:
                        net.new_place(net=net, unique_id=name, tokens=tokens)
            c = line.count('->')
            if c not in (1,2):
                continue
            parts = [x.strip() for x in line.split('->')]
            name = None
            inp = parts[0]
            outp = parts[-1]
            if c==2:
                name = parts[1]
            inp_lst = inp.split()
            outp_lst = outp.split()
            """
            for place_name in inp_lst+outp_lst:
                if place_name not in net.places:
                    net.new_place(unique_id=place_name)
            """
            net.new_transition(net=net, unique_id=name, input_arcs=inp, output_arcs=outp)
        return net
    
    def _space_safe(self, s):
        return s.replace(' ', '_')
    
    def _format_arc(self, arc):
        result = arc.place.unique_id
        if abs(arc.weight)!=1:
            result+= '::'+str(abs(arc.weight))
        return result
            
    
    def _arcs_to_string(self, arcs):
        return ' '.join(self._format_arc(arc) for arc in arcs)
            
    def to_string(self):
        result = ''
        tokens_str = []
        for place in self.get_sorted_places():
            if place.tokens:
                tokens_str.append('%s::%d'%(place.unique_id, place.tokens))
        if tokens_str:
            result += '#'+' '.join(tokens_str)
        transitions_str = []
        for transition in self.get_sorted_transitions():
            transitions_str.append(self._arcs_to_string(transition.input_arcs) + ' -> ' + \
                                   transition.unique_id + ' -> ' + \
                                   self._arcs_to_string(transition.output_arcs))
        if result:
            result+='\n'
        result += '\n'.join(transitions_str)
        return result
        
    
    def __str__(self):
        places = sorted(self.places.items(),key=lambda x:x[0])
        return 'PetriNet({' + \
              ', '.join('%r: %r'%(uid, place) for uid, place in places) + \
              '})'
        
    
    
if __name__=='__main__':       

    def format(p):
        return json.dumps(p.to_json_struct(),indent=4, sort_keys=True)
    

    net1 = PetriNet.from_string("""
    #p1::1 p2::50
    p2 -> t1 -> p2 p1 p4
    p3 -> t2 -> p5
    """)
    
    print net1.to_string()
    
    p = net1.to_json_struct()
    
    print format(net1)
    
    net2 = PetriNet.from_json_struct(p)
    
    a = format(net1)
    b = format(net2)
    print [a]
    print '################################'
    print [b]
    print a==b
    
    
    
    print net1.transitions['t1'].input_arcs
    
    
    

