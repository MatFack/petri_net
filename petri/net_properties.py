# -*- coding: utf-8 -*-

import numpy as np
import tss
import json
import re
import itertools

def _reverse_index(lst):
    return dict(pair[::-1] for pair in enumerate(lst))

def get_ts_invariants(petri_net, places=None, transitions=None):
    if places is None:
        places = _reverse_index(petri_net.get_sorted_places())
    if transitions is None:
        transitions = _reverse_index(petri_net.get_sorted_transitions())
    A = np.zeros((len(places), len(transitions)))
    for transition,col in transitions.iteritems():
        for arc in transition.input_arcs:
            row = places[arc.place]
            A[row,col] -= abs(arc.weight)
        for arc in transition.output_arcs:
            row = places[arc.place]
            A[row,col] += abs(arc.weight)
    print A
    Ax_sol, t_rank = tss.solve(A, ineq=1)
    ineq_sol = []
    t_inv = []
    for v in Ax_sol:
        if (A*np.matrix(v).transpose()==0).all():
            t_inv.append(v)
        else:
            ineq_sol.append(v)
    s_inv, s_rank = tss.solve(A.transpose())
    return ineq_sol, t_inv, t_rank, s_inv, s_rank

def get_deadlocks_traps(petri_net, places=None, transitions=None):
    if not places:
        places = _reverse_index(petri_net.get_sorted_places())
    if not transitions:
        transitions = _reverse_index(petri_net.get_sorted_transitions())
    if not places and not transitions:
        return [], []
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
        for arc_out in transition.output_arcs:
            place_out = arc_out.place
            #setting positive
            for arc_in in transition.input_arcs:
                place_in = arc_in.place
                col = places[place_in]
                dl_A[dl_i, col] = 1
            #setting one negative
            col = places[place_out]
            dl_A[dl_i, col] = -1
            dl_i += 1
        #traps
        for arc_in in transition.input_arcs:
            place_in = arc_in.place
            #setting positive
            for arc_out in transition.output_arcs:
                place_out = arc_out.place
                col = places[place_out]
                tr_A[tr_i, col] = 1
            #setting one negative
            col = places[place_in]
            tr_A[tr_i, col] = -1
            tr_i += 1
    deadlocks, _ = tss.solve(dl_A, True, limit=1) 
    traps, _ = tss.solve(tr_A, True, limit=1) 
    return deadlocks, traps
    
    
def is_marked_trap(trap, places):
    for m, place in zip(trap, places):
        if m and place.tokens:
            return True
    return False
         
def scalar_mul(vec1, vec2):
    return sum(v1*v2 for v1,v2 in zip(vec1, vec2))
            
#def deadlock_contains_trap(:
            
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
       
class NumpyAwareJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray) and obj.ndim == 1:
            return [x for x in obj]
        return json.JSONEncoder.default(self, obj)
      
class Tristate(object):
    """ True - Yes, False - No, None - Unknown """
    def __init__(self, value=None):
        if any(value is v for v in (True, False, None)):
            self.value = value
        else:
            raise ValueError("Tristate value must be True, False, or None")

    def __eq__(self, other):
        return self.value is other
    def __ne__(self, other):
        return self.value is not other
    def __nonzero__(self):   # Python 3: __bool__()
        raise TypeError("Tristate value may not be used as implicit Boolean")

    def __str__(self):
        return str(self.value)
    def __repr__(self):
        return "Tristate(%s)" % self.value        

if __name__=='__main__':
    
    #
    # Covered by S invariants -> net is bounded
    # If net is bounded and live -> net is covered by positive T invariants, so this is useless.
    #
    #
    # Each deadlock 
    #
    #
    
    JSON_FORMAT, TEXT_FORMAT = 'json', 'text'
    import petri
    import argparse
    import itertools
    import glob
    DEBUG = True
    if DEBUG:
        import sys
        sys.argv.extend([ '-f', 'json', 'mumu.json' ])
    
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-o", "--output", dest="filename",
                  help="write output to FILE", metavar="FILE")
    
    parser.add_argument('input_file', nargs='+')
    
    parser.add_argument("-f", "--format",
                  default=JSON_FORMAT, choices=[TEXT_FORMAT, JSON_FORMAT],
                  help="input file format")
    
    args = parser.parse_args()
    from pprint import pprint
    whole_result = {}
    for filename in (itertools.chain(*[glob.glob(filepath) for filepath in args.input_file])):
        with open(filename, 'rb') as f:
            data = f.read()
        if args.format == JSON_FORMAT:
            data = json.loads(data)
            net = petri.PetriNet.from_json_struct(data)
        elif args.format == TEXT_FORMAT:
            net = petri.PetriNet.from_string(data)
            
        places = net.get_sorted_places()
        transitions = net.get_sorted_transitions()
        state = net.get_state()
        # 0 - property False, 1 - partially, 2 - strictly
        result = {'invariants':
                {'T': {
                    'vectors': [],
                    'uncovered' : None,
                    },
                 'S': {
                    'vectors': [],
                    'uncovered' : None,
                    'limits': None
                    },
                },
              'deadlocks': [],
              'traps'    : [],
              'properties' :
                {
                    'bounded' : Tristate(None),
                    'live'    : False,
                    'contradictory':True,
                    'repeatable': 0,
                    'regulated': Tristate(None)
                 }
              }
            
        Ax_sol, t, t_rank, s,s_rank = get_ts_invariants(net)
        if s_rank < len(transitions):
            result['properties']['regulated'] = Tristate(False)
        for t_inv in t:
            result['invariants']['T']['vectors'].append(t_inv)
        uncovered_transitions = [obj.unique_id for obj in get_uncovered(t, net.get_sorted_transitions())]
        result['invariants']['T']['uncovered'] = uncovered_transitions
        
        limits = [None] * len(places)
        
        for s_inv in s:
            result['invariants']['S']['vectors'].append(s_inv)
            for i, s_inv_val in enumerate(s_inv):
                if s_inv_val==0:
                    continue
                new_val = scalar_mul(s_inv, state) / float(s_inv_val)
                if limits[i] is None or new_val<limits[i]:
                    limits[i] = new_val
                
        uncovered_places = [obj.unique_id for obj in get_uncovered(s, net.get_sorted_places())]
        result['invariants']['S']['uncovered'] = uncovered_places
        result['invariants']['S']['limits'] = {obj.unique_id:limit for obj,limit in zip(net.get_sorted_places(),limits) if limit is not None}
        if not uncovered_places:
            result['properties']['bounded'] = Tristate(True)
        if t:
            result['properties']['contradictory'] = False
            
        
        deadlocks, traps = get_deadlocks_traps(net)
        
        
        
        marked_traps = []
        
        for trap_vector in traps:
            marked = is_marked_trap(trap_vector, places)
            if marked:
                marked_traps.append(trap_vector)
            trap_vector = [obj.unique_id for obj in itertools.compress(places, trap_vector)]
            dct = {'vector' : trap_vector,
                   'marked' : marked}
            result['traps'].append(dct)
             
        has_uncovered_deadlocks = False
             
        for deadlock_vector in deadlocks:
            uncovered = True
            for trap in marked_traps:
                if all(deadlock_vector >= trap):
                    uncovered = False
                    break
            has_uncovered_deadlocks = has_uncovered_deadlocks or uncovered
            deadlock_vector = [obj.unique_id for obj in itertools.compress(places, deadlock_vector)]
            dct = {'vector': deadlock_vector,
                   'uncovered': uncovered}
            result['deadlocks'].append(dct)
        
        strict_positive = any((x>0).all() for x in Ax_sol)
        
        print strict_positive
        
        result['properties']['live'] = (not has_uncovered_deadlocks) and bool(traps)
        result['properties']['structurally_bounded'] = not bool(Ax_sol)
        # TODO: Structural boundness - WTF???
        # TODO: Regulated - is it places or transitions count to be compared with rank???
        # TODO:
        whole_result[filename] = result
        
    pprint(whole_result)
        
    
    #if opt

    
    """ 
    with open('bus_sim2.json', 'rb') as f:
        obj = json.load(f)
    net1 = petri.PetriNet.from_json_struct(obj)
    print net1.get_state()
    places = net1.get_sorted_places()
    print 'Marking'
    for place in places:
        print place.unique_id,
        
    
    transitions = net1.get_sorted_transitions()
    
    def format(p):
        return json.dumps(p.to_json_struct(),indent=2, sort_keys=True)
    
    t,s = get_ts_invariants(net1)
    
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
    """