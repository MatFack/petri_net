
from net_properties import PetriProperties
import collections
from pprint import pprint
import igraph
# This is prototype, no premature optimisation please

DEBUG = False

def spec_add(a, b):
    if a == 'w' or b=='w':
        return 'w'
    return a+b

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
            
            

class ReachabilityGraph(object):
    def __init__(self, net, properties=None):
        self.net = net
        if properties is None:
            properties = PetriProperties(self.net)
        self.properties = properties
        
        self.explored = {}
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

        
        
    def explore(self, initial):
        self.names = {}
        stack = collections.deque([(initial, 0)])
        cur_path = collections.deque()
        while stack:
            state, level = stack.pop()
            if state in self.explored:
                continue
            while cur_path and cur_path[-1][-1] >= level:
                cur_path.pop()
            cur_path.append((state, level))
            self.names[state] = 'S%d'%(len(self.names)+1)
            neighbours = {}
            self.explored[state] = neighbours
            for trans_name, (move, req) in self.transition_moves.iteritems():
                next_state = get_next_state(state, move, req)
                if next_state:
                    for s, _ in reversed(cur_path):
                        res = greater_than(next_state, s)
                        if res:
                            next_state = tuple(res)
                            break
                    if next_state not in self.explored:
                        stack.append((next_state, level+1))
                    neighbours[trans_name] = next_state
        if DEBUG:
            G = igraph.Graph(directed=True)
            print "STATES",len(self.explored)
            for state in self.explored:
                name = self.names[state]
                G.add_vertex(name)
            labels = {}
            arcs = 0
            for v, neighbours in self.explored.iteritems():
                name = self.names[v]
                for trans, neighbour in neighbours.iteritems():
                    to_name = self.names[neighbour]
                    arcs+=1
                    G.add_edge(name, to_name, name=trans)
            G.vs["label"] = G.vs["name"]
            G.es["label"] = G.es["name"]
            layout = G.layout("kk")
            igraph.plot(G)
            
        
if __name__ == '__main__':
    import json
    import petri
    with open('../examples/pots.json','rb') as f:
        net = petri.PetriNet.from_json_struct(json.load(f))
    r = ReachabilityGraph(net)
    r.explore(net.get_state())
    for s in r.explored:
        print s,r.explored[s]
    print r.explored