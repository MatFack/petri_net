# -*- coding: utf-8 -*-

import numpy as np
import tss

def _reverse_index(lst):
    return dict(pair[::-1] for pair in enumerate(lst))

def get_ts_invariants(petri_net, places=None, transitions=None):
    if not places:
        places = _reverse_index(petri_net.get_sorted_places())
    if not transitions:
        transitions = _reverse_index(petri_net.get_sorted_transitions())
    A = np.zeros((len(places), len(transitions)))
    for transition,col in transitions.iteritems():
        for place,weight in transition.input_arcs.iteritems():
            row = places[place]
            A[row,col] -= weight
        for place,weight in transition.output_arcs.iteritems():
            row = places[place]
            A[row,col] += weight
    t_inv = tss.solve(A)
    s_inv = tss.solve(A.transpose())
    return t_inv, s_inv

def get_deadlocks_traps(petri_net, places=None, transitions=None):
    if not places:
        places = _reverse_index(petri_net.get_sorted_places())
    if not transitions:
        transitions = _reverse_index(petri_net.get_sorted_transitions())
    cols = len(places)
    dl_rows = 0
    tr_rows = 0
    for transition in transitions:
        dl_rows += len(transition.output_arcs)
        tr_rows += len(transition.input_arcs)
    dl_A = np.zeros((dl_rows, cols))
    tr_A = np.zeros((tr_rows, cols))
    dl_i = 0
    tr_i = 0
    for transition in transitions:
        #deadlocks
        for place_out in transition.output_arcs:
            #setting positive
            for place_in in transition.input_arcs:
                col = places[place_in]
                dl_A[dl_i, col] = 1
            #setting one negative
            col = places[place_out]
            dl_A[dl_i, col] = -1
            dl_i += 1
        #traps
        for place_in in transition.input_arcs:
            #setting positive
            for place_out in transition.output_arcs:
                col = places[place_out]
                tr_A[tr_i, col] = 1
            #setting one negative
            col = places[place_in]
            tr_A[tr_i, col] = -1
            tr_i += 1
    
    deadlocks = tss.solve(dl_A, True, limit=1)
    traps = tss.solve(tr_A, True, limit=1)
    return deadlocks, traps
    
    
def marked_trap(trap, places):
    for m, place in zip(trap, places):
        if m and place.tokens:
            return True
    return False

def get_marked_traps(traps, places):
    for trap in traps:
        if marked_trap(trap, places):
            yield trap
            
def get_liveness(deadlocks, traps, places):
    marked_traps = list(get_marked_traps(traps, places))
    print marked_traps
    for deadlock in deadlocks:
        for trap in marked_traps:
            #check if deadlock has a marked trap in it
            if all(deadlock>=trap):
                break
        else:
            return deadlock
    return None
    
def get_uncovered(invariants, objs):
    uncovered = []
    if not invariants:
        return objs[:]
    inv = sum(invariants)
    for i, val in enumerate(inv):
        if val==0:
            uncovered.append(objs[i])
    return uncovered
    
if __name__=='__main__':
    import petri,json
    """
    net1 = petri.PetriNet()
    key = net1.new_place('1key', 1)
    cr1 = net1.new_place('2cr1')
    cr2 = net1.new_place('3cr2')
    pend1 = net1.new_place('4pend1')
    pend2 = net1.new_place('6pend2')
    quiet1 = net1.new_place('5quiet1')
    quiet2 = net1.new_place('7quiet2')
    
    a1 = net1.new_transition('a1', '5quiet1', '4pend1')
    a2 = net1.new_transition('a2', '7quiet2', '6pend2')
    b1 = net1.new_transition('b1', '4pend1 1key', '2cr1')
    b2 = net1.new_transition('b2', '6pend2 1key', '3cr2')
    c1 = net1.new_transition('c1', '2cr1', '5quiet1 1key')
    c1 = net1.new_transition('c2', '3cr2', '7quiet2 1key')
    """
    net1 = petri.PetriNet.from_string("""
    # 
    p2 -> t1 -> p1 p3
    p1 -> t2 -> p3
    p1 -> t3 -> p4
    p3 p4 -> t4 -> p2
    """)
    places = net1.get_sorted_places()
    transitions = net1.get_sorted_transitions()
    
    def format(p):
        return json.dumps(p.to_json_struct(),indent=2, sort_keys=True)
    
    print format(net1)
    t,s = get_ts_invariants(net1)
    print "T",t
    print "S",s
    
    uncovered_transitions = get_uncovered(t, transitions)
    
    
    if uncovered_transitions:
        print "Net can't be bounded and live simultaneaously"
    else:
        print "Net can be bounded and live"
    
    uncovered_places = get_uncovered(s, places)
    
    if uncovered_places:
        print "Places %s aren't covered by positive S-invariants."%(' '.join(str(place) for place in places))
        print "Therefore they can be unlimited"
    else:
        print "Net is bounded"
    
    
    
    d,t = get_deadlocks_traps(net1)
    print "Deadlocks"
    for dd in d:
        print dd
    print "Traps"
    for tt in t:
        print tt
    dl = get_liveness(d, t, places)
    if dl is None:
        print "Net is live!"
    else:
        print "Net isn't alive, deadlock %s isn't covered"%dl
    