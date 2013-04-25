
from net_properties import PetriProperties
import collections
from pprint import pprint
import igraph
# This is prototype, no premature optimisation please

def get_next_state(state, trans):
    result = tuple(s+t for (s,t) in zip(state, trans))
    if any(r<0 for r in result):
        return None
    return result

class ReachabilityGraph(object):
    def __init__(self, net, properties=None):
        self.net = net
        if properties is None:
            properties = PetriProperties(self.net)
        self.properties = properties
        
        self.explored = {}
        self.move_tuples = map(lambda lst:tuple(int(c) for c in lst), self.properties.incidence_matrix.transpose().tolist())
        self.move_names = [transition.unique_id for transition in self.net.get_sorted_transitions()]
        print self.move_tuples
        
        
    def explore(self, initial):
        names = {}
        stack = collections.deque([initial])
        while stack:
            state = stack.pop()
            names[state] = 'S%d'%(len(names)+1)
            neighbours = {}
            self.explored[state] = neighbours
            for i, tpl in enumerate(self.move_tuples):
                next_state = get_next_state(state, tpl)
                if next_state:
                    if next_state not in self.explored:
                        stack.append(next_state)
                    neighbours[self.move_names[i]] = next_state
        if True:
            
            G = igraph.Graph(directed=True)
            
            labels = {}
            print self.explored
            for v, neighbours in self.explored.iteritems():
                print v,neighbours
                name = names[v]
                G.add_vertex(name)
                for trans, neighbour in neighbours.iteritems():
                    to_name = names[neighbour]
                    G.add_vertex(to_name)
                    G.add_edge(name, to_name)
            
                    
        
            layout = G.layout("kk")
            for p in layout:
                print p
            #igraph.plot(G, layout=layout )
            
        
    
        
        
        
if __name__ == '__main__':
    import json
    import petri
    with open('bus_sim.json','rb') as f:
        net = petri.PetriNet.from_json_struct(json.load(f))
    r = ReachabilityGraph(net)
    r.explore(net.get_state())