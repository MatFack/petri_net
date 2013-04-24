# -*- coding: utf-8 -*-

import numpy as np
import tss
import json
import re
import itertools
import inspect
import collections
  
    
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
    
def _reverse_index(lst):
    return {obj:i for i,obj in enumerate(lst)}

def _id_compress(objects, vector):
    return [obj.unique_id for obj in itertools.compress(objects, vector)]
    
class PetriProperties(object):
    def __init__(self, net=None):
        self._net = net
        self._reset()
        
    def _reset(self):
        self.incidence_matrix = None
        self.Ax_ineq_sol = None
        self.t_invariants = None
        self.s_invariants = None
        self.t_uncovered = None
        self.s_uncovered = None
        self.A_rank = None
        self.AT_rank = None
        self.place_limits = None
        self.deadlock_matrix = None
        self.trap_matrix = None
        self.deadlocks = None
        self.traps = None
        self.marked_traps = None
        self.uncovered_deadlocks = None
        self.structural_uncovered_deadlocks = None
        self.liveness = None
        self.bounded_by_s = None
        self.structural_boundness = None
        self.repeatable = None
        self.structural_liveness = None
        # Simple properties
        self.state_machine = None
        self.marked_graph = None
        
    def __getattribute__(self, attr):
        result = super(PetriProperties, self).__getattribute__(attr)
        if result is not None:
            return result
        compute_func_name = '_compute_'+attr
        try:
            compute_func =  super(PetriProperties, self).__getattribute__(compute_func_name)
        except AttributeError:
            compute_func = None
        if compute_func is None:
            return result
        compute_func()
        return super(PetriProperties, self).__getattribute__(attr)
    
    @property
    def _fields(self):
        for field in dir(self):
            if not field.startswith('_'):
                yield field
    
    def __iter__(self):
        for field in self._fields:
            value = super(PetriProperties, self).__getattribute__(field)
            if value is not None:
                yield field, value
            else:
                err_field = field+'_error'
                try:
                    error = super(PetriProperties, self).__getattribute__(err_field)
                except AttributeError:
                    pass
                else:
                    yield err_field, error
    
    def _set_error(self, field, value):
        setattr(self, field, None)
        setattr(self, field+'_error', value)

    def _compute_incidence_matrix(self):
        transitions = self._net.get_sorted_transitions()
        places = _reverse_index(self._net.get_sorted_places())
        A = np.zeros((len(places), len(self._net.transitions)))
        for col, transition in enumerate(transitions):
            for arc in transition.input_arcs:
                row = places[arc.place]
                A[row,col] -= abs(arc.weight)
            for arc in transition.output_arcs:
                row = places[arc.place]
                A[row,col] += abs(arc.weight)
        self.incidence_matrix = A
        
    def _compute_t_invariants(self):
        #- incidence_matrix
        A = self.incidence_matrix
        Ax_sol, A_rank = tss.solve(A, ineq=1)
        #+ A_rank
        self.A_rank = A_rank
        ineq_sol = []
        t_inv = []
        for v in Ax_sol:
            if (A*np.matrix(v).transpose()==0).all():
                t_inv.append(v)
            else:
                ineq_sol.append(v)
        #+ t_invariants
        self.t_invariants = t_inv
        #+ Ax_ineq_sol
        self.Ax_ineq_sol = ineq_sol
        #+ structural_boundness
        self.structural_boundness = not bool(ineq_sol)
        #+ repeatable
        self.repeatable = bool(t_inv)
        
    _compute_repeatable = _compute_structural_boundness = _compute_A_rank = _compute_Ax_ineq_sol = _compute_t_invariants
    
    def _compute_s_invariants(self):
        A = self.incidence_matrix
        s_inv, AT_rank = tss.solve(A.transpose())
        #+ s_invariants
        self.s_invariants = s_inv
        #+ AT_rank
        self.AT_rank = AT_rank
    
    _compute_AT_rank = _compute_s_invariants
    
    def _compute_t_uncovered(self):
        #- t_invariants
        t = self.t_invariants
        #+ t_uncovered
        self.t_uncovered = [obj.unique_id for obj in get_uncovered(t, self._net.get_sorted_transitions())]
    
    def _compute_s_uncovered(self):
        #- s_invariants
        s = self.s_invariants
        #+ s_uncovered
        self.s_uncovered = [obj.unique_id for obj in get_uncovered(s, self._net.get_sorted_places())] 
        
    def _compute_place_limits(self):
        places = self._net.get_sorted_places()
        state = self._net.get_state()
        limits = [None] * len(places)
        #- s_invariants
        s = self.s_invariants
        for s_inv in s:
            for i, s_inv_val in enumerate(s_inv):
                if s_inv_val==0:
                    continue
                new_val = scalar_mul(s_inv, state) / float(s_inv_val)
                if limits[i] is None or new_val<limits[i]:
                    limits[i] = new_val
        #+ place_limits
        self.place_limits = {obj.unique_id:limit for obj,limit in zip(places, limits) if limit is not None}
        #+ bounded_by_s
        self.bounded_by_s = (len(self.place_limits) == len(places))
        
    _compute_bounded_by_s = _compute_place_limits
        
    def _compute_deadlock_matrix(self):
        places = _reverse_index(self._net.get_sorted_places())
        transitions = self._net.get_sorted_transitions()
        cols = len(places)
        dl_rows = 0
        tr_rows = 0
        # If place has no input arcs -> place is a deadlock.
        # If place has no output arcs -> http://cdn.instanttrap.com/trap.jpg
        place_no_input = set(self._net.get_sorted_places())
        place_no_output = set(self._net.get_sorted_places())
        
        for transition in transitions:
            dl_rows += len(transition.output_arcs)
            tr_rows += len(transition.input_arcs)
            for arc in transition.output_arcs:
                place_no_input.discard(arc.place)
            for arc in transition.input_arcs:
                place_no_output.discard(arc.place)
        
        print place_no_input
        
        dl_rows += len(place_no_input)
        tr_rows += len(place_no_output)
        
        dl_A = np.zeros((dl_rows, cols))
        tr_A = np.zeros((tr_rows, cols))
        
        for i,p in enumerate(place_no_input):
            dl_A[i,places[p]] = 1
            
        for i,p in enumerate(place_no_output):
            tr_A[i,places[p]] = 1
        
        dl_i = len(place_no_input)
        tr_i = len(place_no_output)
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
        #+ deadlock_matrix
        self.deadlock_matrix = dl_A
        #+ trap_matrix
        self.trap_matrix = tr_A
        
    _compute_trap_matrix = _compute_deadlock_matrix
    
    def _compute_deadlocks(self):
        #  [_id_compress(places, deadlock_vector) for deadlock_vector in deadlock_vectors]
        #- deadlock_matrix
        #+ deadlocks
        self.deadlocks, _ = tss.solve(self.deadlock_matrix, True, limit=1) 
        
    def _compute_traps(self):
        #- trap_matrix
        #+ traps
        self.traps, _ = tss.solve(self.trap_matrix, True, limit=1) 
        
    def _compute_marked_traps(self):
        marked_traps = []
        places = self._net.get_sorted_places()
        #- traps
        traps = self.traps
        for trap_vector in traps:
            if is_marked_trap(trap_vector, places):
                marked_traps.append(trap_vector)
        #+ marked_traps
        self.marked_traps = marked_traps
                
    def _get_uncovered_deadlocks(self, only_marked_traps):
        uncovered_deadlocks = []
        #- deadlocks
        deadlocks = self.deadlocks
        if only_marked_traps:
            #- marked_traps
            traps = self.marked_traps
        else:
            #- traps
            traps = self.traps
        for deadlock_vector in deadlocks:
            for trap in traps:
                if all(deadlock_vector >= trap):
                    break
            else:
                uncovered_deadlocks.append(deadlock_vector)
        #+ uncovered_deadlocks
        return uncovered_deadlocks
        
    def _compute_uncovered_deadlocks(self):
        self.uncovered_deadlocks = self._get_uncovered_deadlocks(only_marked_traps=True)
        
    def _compute_structural_uncovered_deadlocks(self):
        self.structural_uncovered_deadlocks = self._get_uncovered_deadlocks(only_marked_traps=False)
        
    def _compute_liveness(self):
        #- uncovered_deadlocks
        #+ liveness
        self.liveness = (not bool(self.uncovered_deadlocks)) 
        
    def _compute_structural_liveness(self):
        #- structural_uncovered_deadlocks
        #+ structural_liveness
        self.structural_liveness = not bool(self.structural_uncovered_deadlocks)
        
    def _compute_state_machine(self):
        result = True
        for transition in self._net.get_transitions_iter():
            if not(len(transition.input_arcs) == len(transition.output_arcs) <= 1):
                result = False
                break
        #+ state_machine
        self.state_machine = result
        
    def _is_marked_graph(self):
        place_input = collections.defaultdict(lambda:0)
        place_output = collections.defaultdict(lambda:0)
        for transition in self._net.get_transitions_iter():
            for arc in transition.input_arcs:
                v = place_output[arc.place]+1
                if v>1: return False
                place_output[arc.place] = v
            for arc in transition.output_arcs:
                v = place_input[arc.place]+1
                if v>1: return False
                place_input[arc.place] = v
        for place in itertools.chain(place_input, place_output):
            if place_input[place]!=place_output[place]:
                return False
        return True
        
        
        
    def _compute_marked_graph(self):
        #+ marked_graph
        self.marked_graph = self._is_marked_graph()
        
    


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
        sys.argv.extend([ '-f', 'json','test5.json' ])
    p = PetriProperties()
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-o", "--output", dest="filename",
                  help="write output to FILE", metavar="FILE")
    
    parser.add_argument('input_file', nargs='+')
    
    parser.add_argument("-f", "--format",
                  default=JSON_FORMAT, choices=[TEXT_FORMAT, JSON_FORMAT],
                  help="input file format")
    
    all_properties = ','.join(p._fields)
    parser.add_argument("-p", "--properties", dest="properties",
              default=all_properties,
              help="properties to be computed")
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
            
        props = PetriProperties(net)
        
        for prop in args.properties.split(','):
            if prop not in props._fields:
                
                props._set_error(prop, "Unknown property")
            else:
                getattr(props, prop)
        
        
        dct = dict(props)
        for prop_name, prop_value in dct.iteritems():
            print '####',prop_name
            print prop_value
        continue
        print props.uncovered_deadlocks
        
        #for dl in props.deadlocks:
        #    print dl
        break
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
            
        Ax_sol, t, A_rank, s,AT_rank = get_ts_invariants(net)
        if AT_rank < len(transitions):
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
            #trap_vector = 
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