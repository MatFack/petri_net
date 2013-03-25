# -*- coding: utf-8 -*-

import json
from serializable import Serializable, RequiredException

    
class Transition(Serializable):
    unique_id_to_serialize = True
    def __init__(self, unique_id=None, input_arcs=None, output_arcs=None, net=None):
        """
            unique_id - unique identifier (hash if None)
            input_arcs, output_arcs - dictionary
                { place : weight }
            net - petri net (only if arcs are represented as strings)
        """
        self.input_arcs = self._convert_arcs(input_arcs, net)
        self.output_arcs = self._convert_arcs(output_arcs, net)
        self.unique_id = hash(self) if unique_id is None else unique_id
        
    def _convert_arcs(self, arcs, net):
        if isinstance(arcs, basestring):
            return dict(self._str_to_arc(arc,net) for arc in arcs.split())
        else:
            return dict(arcs or {})
    
    def _str_to_arc(self, arc_str, net):
        if net is None:
            raise ValueError("Expected petri `net` instance, but got None")
        if '::' in arc_str:
            place_name, _, weight = arc_str.rpartition('::')
            weight = int(weight)
        else:
            place_name = arc_str
            weight = 1
        place = net[place_name]
        return place,weight
            
        
    @property
    def is_enabled(self):
        return all(place.tokens>=weight for place,weight in self.input_arcs.iteritems())
    
    def fire(self):
        """
            Fire the transition. It's assumed that it can fire.
        """
        assert(self.is_enabled)
        for place, weight in self.input_arcs.iteritems():
            place.remove_tokens(weight)
        for place, weight in self.output_arcs.iteritems():
            place.add_tokens(weight)
            
    def input_arcs_to_json_struct(self):
        return dict((place.unique_id, weight) for place,weight in self.input_arcs.iteritems())
    
    def output_arcs_to_json_struct(self):
        return dict((place.unique_id, weight) for place,weight in self.output_arcs.iteritems())
    
    @classmethod 
    def input_arcs_from_json_struct(cls, input_arcs_obj, places_dct, **kwargs):
        input_arcs = {}
        for uid,weight in input_arcs_obj.iteritems():
            input_arcs[places_dct[uid]] = weight
        return input_arcs
    
    @classmethod 
    def output_arcs_from_json_struct(cls, output_arcs_obj, places_dct, **kwargs):
        output_arcs = {}
        for uid,weight in output_arcs_obj.iteritems():
            output_arcs[places_dct[uid]] = weight
        return output_arcs
        
        
class Place(Serializable):
    tokens_to_serialize = True
    unique_id_to_serialize = True
    
    def __init__(self, unique_id=None, tokens=0):
        """
        unique_id - unique identifier (hash if None)
        tokens - number of tokens in initial marking
        """
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
        
    def __repr__(self):
        return "%s(%r,%r)" % (self.__class__.__name__, self.tokens,self.unique_id)
    
    __str__ = __repr__
    
    
class PetriNet(Serializable):
    PLACE_CLS = Place
    TRANSITION_CLS = Transition
    
    def __init__(self, places=None, transitions=None):
        self.places = dict(places or {})
        self.transitions = dict(transitions or {}) 
        
    def add_place(self, place):
        assert(place.unique_id not in self.places)
        self.places[place.unique_id] = place
        
    def add_transition(self, transition):
        assert(transition.unique_id not in self.transitions)
        self.transitions[transition.unique_id] = transition
        
    def get_places(self):
        return [self.places[key] for key in sorted(self.places.keys())]
    
    def get_transitions(self):
        return [self.transitions[key] for key in sorted(self.transitions.keys())]
        
    def __getitem__(self, key):
        return self.places[key]
        
    def new_place(self, *args, **kwargs):
        """
            Creates a place and immediately adds it to this petri net
        """
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
        
    def transitions_to_json_struct(self):
        return [transition.to_json_struct() for transition in self.transitions.itervalues()]
        
    def places_to_json_struct(self):
        return [place.to_json_struct() for place in self.places.itervalues()]
    
    @classmethod
    def places_from_json_struct(cls, places_obj, **kwargs):
        places = {}
        for place_obj in places_obj:
            place_obj = cls.PLACE_CLS.from_json_struct(place_obj)
            places[place_obj.unique_id] = place_obj
        return places
    
    @classmethod
    def transitions_from_json_struct(cls, transitions_obj, fields_values, **kwargs):
        places = fields_values.get('places')
        if places is None:
            raise RequiredException('places')
        transitions = {}
        for transition_obj in transitions_obj:
            transition_obj = cls.TRANSITION_CLS.from_json_struct(transition_obj, places_dct=places)
            transitions[transition_obj.unique_id] = transition_obj
        return transitions
    
    @classmethod
    def from_string(cls, s, place_cls=Place, trans_cls=Transition):
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
                    net.new_place(name, tokens)
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
            for place_name in inp_lst+outp_lst:
                if place_name not in net.places:
                    net.new_place(unique_id=place_name)
            net.new_transition(unique_id=name, input_arcs=inp, output_arcs=outp)
        return net
            

    
    def __str__(self):
        places = sorted(self.places.items(),key=lambda x:x[0])
        return 'PetriNet({' + \
              ', '.join('%r: %r'%(uid, place) for uid, place in places) + \
              '})'
        
    
    
if __name__=='__main__':       

    def format(p):
        return json.dumps(p.to_json_struct(),indent=4, sort_keys=True)
    

    net1 = PetriNet.from_string("""
    p2 -> t1 -> p1 p4
    p3 -> t2 -> p5
    """)
    
    p = net1.to_json_struct()
    
    print format(net1)
    
    net2 = PetriNet.from_json_struct(p)
    
    a = format(net1)
    b = format(net2)
    print a
    print '################################'
    print b
    print a==b
    
    
    
    print net1.transitions['t1'].input_arcs
    
    
    

