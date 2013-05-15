
#from net_properties import PetriProperties
import collections
from pprint import pprint
from util.serializable import Serializable, RequiredException

DEBUG = False

def spec_add(a, b):
    if a == 'w' or b=='w':
        return 'w'
    return a+b

def smaller(a, b):
    if a=='w':
        return b=='w'
    return b=='w' or a<b


def get_next_state(state, trans, req):
    lst = []
    for s, a, r in zip(state, trans, req):
        if s != 'w':
            if s+r <0:
                return None
        lst.append(spec_add(s, a))
    return tuple(lst)
    result = tuple(spec_add(s, t) for (s,t) in zip(state, trans))
    if any(r<0 for r in result):
        return None
    return result

def greater_than(marking1, marking2):
    result = []
    for m1, m2 in zip(marking1, marking2):
        if m2=='w':
            if m1=='w':
                result.append('w')
            else:
                return None
        else:
            if m1 == 'w' or m1 > m2:
                result.append('w')
            elif m1==m2:
                result.append(m1)
            elif m1<m2:
                return None
    return result
            
            

class ReachabilityGraph(Serializable):
    
    explored_to_serialize = True
    bounded_to_serialize = True
    dead_states_to_serialize = True
    place_limits_to_serialize = True
    max_tokens_number_to_serialize = True
    names_to_serialize = True
    
    def __init__(self, net=None, properties=None):
        self.net = net
        self.properties = properties
        self.reset()
        self.explored = {}
        if net is not None:
            places = {place:i for i,place in enumerate(self.net.get_sorted_places())}
            self.move_names = [transition.unique_id for transition in self.net.get_sorted_transitions()]
            self.transition_moves = {}
            for transition in self.net.get_sorted_transitions():
                req_tuple = [0]*len(places)
                move_tuple = [0]*len(places)
                for arc in transition.input_arcs:
                    n = places[arc.place]
                    req_tuple[n] -= abs(arc.weight)
                    move_tuple[n] -= abs(arc.weight)
                for arc in transition.output_arcs:
                    n = places[arc.place]
                    move_tuple[n] += abs(arc.weight)
                self.transition_moves[transition.unique_id] = (tuple(move_tuple), tuple(req_tuple))

        
    def reset(self):
        self.bounded = None
        self.dead_states = []
        self.place_limits = []
        self.max_tokens_number = 0
      
    def get_backward_names(self):
        return {name:state for (state, name) in self.names.iteritems()}
        
    def names_to_json_struct(self, **kwargs):
        return self.get_backward_names()
    
    def names_from_json_struct(self, names_obj, **kwargs):
        self.names_deserialized = True
        return {tuple(state):name for (name, state) in names_obj.iteritems()}
        
    def explored_to_json_struct(self, **kwargs):
        return {self.names[state]:neighbours for (state, neighbours) in self.explored.iteritems()}
    
    def explored_from_json_struct(self, explored_obj, **kwargs):
        if not getattr(self, 'names_deserialized', None):
            raise RequiredException('names')
        del self.names_deserialized
        backward_names = self.get_backward_names() 
        def tuplify(dct):
            for name, value in dct.iteritems():
                dct[name] = tuple(value)
            return dct
        tuplify(backward_names)
        return {backward_names[name]:tuplify(neighbours) for (name, neighbours) in explored_obj.iteritems()}
        
    def explore(self, initial):
        self.reset()
        self.bounded = True
        self.names = {}
        for tokens in initial:
            self.place_limits.append([tokens, tokens])
        stack = collections.deque([(initial, 0)])
        cur_path = collections.deque()
        while stack:
            state, level = stack.pop()
            tokens_number = reduce(spec_add, state)
            if tokens_number == 'w':
                self.bounded = False
            if smaller(self.max_tokens_number, tokens_number):
                self.max_tokens_number = tokens_number
            for limit, token_val in zip(self.place_limits, state):
                min_val, max_val = limit
                if not smaller(min_val, token_val):
                    min_val = token_val
                if not smaller(token_val, max_val):
                    max_val = token_val
                limit[0], limit[1] = min_val, max_val
            if state in self.explored:
                continue
            while cur_path and cur_path[-1][-1] >= level:
                cur_path.pop()
            cur_path.append((state, level))
            state_name = 'S%d'%(len(self.names)+1)
            self.names[state] = state_name
            neighbours = {}
            self.explored[state] = neighbours
            for trans_name, (move, req) in self.transition_moves.iteritems():
                next_state = get_next_state(state, move, req)
                if next_state:
                    if not (self.properties and self.properties.bounded_by_s == True):
                        for s, _ in reversed(cur_path):
                            res = greater_than(next_state, s)
                            if res:
                                next_state = tuple(res)
                                break
                    if next_state not in self.explored:
                        stack.append((next_state, level+1))
                    neighbours[trans_name] = next_state
            if not neighbours:
                self.dead_states.append(state_name)
                
        
if __name__ == '__main__':
    import json
    import petri
    with open('../examples/trash/infinite.json','rb') as f:
        net = petri.PetriNet.from_json_struct(json.load(f))
    r = ReachabilityGraph(net)
    r.explore(net.get_state())
    for s in r.explored:
        print s,r.explored[s]
    print r.explored