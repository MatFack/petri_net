# -*- coding: utf-8 -*-

import numpy as np
import tss as tss
import itertools
import collections
import traceback

# TODO: Add ability to count traps and deadlocks separately
  
PROPERTY_FALSE, PROPERTY_PARTIALLY, PROPERTY_FULLY = 'false', 'partially', 'fully'
    
def is_marked_trap(trap, places):
    for m, place in zip(trap, places):
        if m and place.tokens:
            return True
    return False
         
def scalar_mul(vec1, vec2):
    return sum(v1*v2 for v1,v2 in zip(vec1, vec2))
    
def get_uncovered(invariants, objs):
    uncovered = []
    if not invariants:
        return objs[:]
    inv = sum(invariants)
    for i, val in enumerate(inv):
        if val==0:
            uncovered.append(objs[i])
    return uncovered
      
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

    def __repr__(self):
        return "Tristate(%s)" % self.value 
    
    __str__ = __repr__      
    
def _reverse_index(lst):
    return {obj:i for i,obj in enumerate(lst)}

def _id_compress(objects, vector):
    return [obj.unique_id for obj in itertools.compress(objects, vector)]
    
def sum_weight(arcs):
    return sum(abs(arc.weight) for arc in arcs)
    
class CantComputeError(Exception):
    pass

class ArraySubclass(np.ndarray):
    def __new__(cls, data):
            if isinstance(data, ArraySubclass):
                    return data
            if isinstance(data, np.ndarray):
                    return data.view(cls)
            arr = np.array(data)
            return np.ndarray.__new__(ArraySubclass, shape=arr.shape, dtype=arr.dtype, buffer=arr)
    
class PetriProperties(object):
    def __init__(self, net=None):
        self._net = net
        self._ignored_fields = {'place_input_arcs', 'place_output_arcs','place_input_transitions', 'place_output_transitions'}
        self._reset()
        
    def _reset(self, net=None):
        if net is not None:
            self._net = net
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
        self.structural_liveness = None
        # Not actually properties
        self.place_input_arcs = None
        self.place_output_arcs = None
        self.place_input_transitions = None
        self.place_output_transitions = None
        # Simple properties
        self.state_machine = None
        self.marked_graph = None
        self.free_choice = None
        self.extended_free_choice = None
        self.simple = None
        self.asymmetric = None
        # Properties we get from TSS
        #TODO: How is "kerovana" translated?
        self.regulated = None
        self.structural_boundedness = None
        # These properties can be partial.
        self.conservativeness = None #TODO: The only problem left!
        self.repeatable = None
        self.consistency = None
        for field in self._fields:
            if self._get_error(field) is not None:
                self._set_error(field, None)
        
    def __getattribute__(self, attr):
        result = super(PetriProperties, self).__getattribute__(attr)
        if result is not None:
            return result
        error = self._get_error(attr) 
        if error is not None:
            raise CantComputeError(error)
            return None
        compute_func_name = '_compute_'+attr
        try:
            compute_func =  super(PetriProperties, self).__getattribute__(compute_func_name)
        except AttributeError:
            compute_func = None
        if compute_func is None:
            return result
        try:
            compute_func()
        except CantComputeError, ex:
            self._set_error(attr, ex.message)
            raise
        except Exception:
            error = traceback.format_exc()
            self._set_error(attr, error)
            raise CantComputeError(error)
        return super(PetriProperties, self).__getattribute__(attr)
    
    @property
    def _fields(self):
        for field in dir(self):
            if not field.startswith('_') and field not in self._ignored_fields:
                yield field
                
    def _process_properties(self, properties=None):
        fields = set(self._fields)
        if properties is None:
            properties = fields
        were_errors = False
        for prop in properties:
            if prop not in fields:
                self._set_error(prop, "Unknown property")
            else:
                try:
                    getattr(self, prop)
                except Exception, ex:
                    were_errors = True
        return were_errors
    
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
        
    def _get_error(self, field):
        try:
            return super(PetriProperties, self).__getattribute__(field+'_error')
        except AttributeError:
            return None

    def _compute_incidence_matrix(self):
        transitions = self._net.get_sorted_transitions()
        places = _reverse_index(self._net.get_sorted_places())
        A = np.zeros((len(places), len(transitions)))
        for col, transition in enumerate(transitions):
            for arc in transition.input_arcs:
                row = places[arc.place]
                A[row,col] -= abs(arc.weight)
            for arc in transition.output_arcs:
                row = places[arc.place]
                A[row,col] += abs(arc.weight)
        A = A.astype('int32')
        self.incidence_matrix = A
        
    def _compute_t_invariants(self):
        #- incidence_matrix
        A = self.incidence_matrix
        t_inv, A_rank = tss.solve(A)
        #+ t_invariants
        self.t_invariants = t_inv
        #+ A_rank
        self.A_rank = A_rank
        
    _compute_A_rank = _compute_t_invariants
    
    def _compute_Ax_ineq_sol(self):
        #- incidence_matrix
        A = self.incidence_matrix
        solutions, _ = tss.solve(A, ineq=True)
        ineq_sol = []
        for v in solutions:
            if not (A*np.matrix(v).transpose()==0).all():
                ineq_sol.append(v)
        #+ Ax_ineq_sol
        self.Ax_ineq_sol = ineq_sol
        #+ structural_boundedness
        self.structural_boundedness = not bool(ineq_sol)
        
    _compute_structural_boundedness = _compute_Ax_ineq_sol
    
    def _compute_conservativeness(self):
        # ??????????????????????
        #+ conservativeness
        #self.conservativeness = conservativeness
        pass

            
    def _compute_repeatable(self):
        # It's repeatable when it's covered by T invariants + Ax_ineq_sol-s?
        result = PROPERTY_FALSE
        #- t_invariants
        t_inv = self.t_invariants
        #- Ax_ineq_sol
        ineq_sol = self.Ax_ineq_sol
        new_lst = t_inv + ineq_sol
        if new_lst:
            s = sum(new_lst)
            if (s!=0).all():
                result = PROPERTY_FULLY
            else:
                result = PROPERTY_PARTIALLY
        self.repeatable = result
        
    def _compute_consistency(self):
        result = PROPERTY_FULLY
        #- t_uncovered
        if self.t_uncovered:
            result = PROPERTY_PARTIALLY
        #- t_invariants
        if not self.t_invariants:
            result = PROPERTY_FALSE
            
        #+ consistency
        self.consistency = result
        
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
        
    def _compute_place_input_transitions(self):
        place_input_arcs = collections.defaultdict(lambda:[])
        place_output_arcs = collections.defaultdict(lambda:[])
        place_input_transitions = collections.defaultdict(lambda:[])
        place_output_transitions = collections.defaultdict(lambda:[])
        for transition in self._net.get_transitions_iter():
            for arc in transition.output_arcs:
                place_input_arcs[arc.place].append(arc)
                place_input_transitions[arc.place].append(transition)
            for arc in transition.input_arcs:
                place_output_arcs[arc.place].append(arc)
                place_output_transitions[arc.place].append(transition)
                
        for k,v in place_input_arcs.iteritems():
            place_input_arcs[k] = frozenset(v)
            
        for k,v in place_output_arcs.iteritems():
            place_output_arcs[k] = frozenset(v)
            
        for k,v in place_input_transitions.iteritems():
            place_input_transitions[k] = frozenset(v)
            
        for k,v in place_output_transitions.iteritems():
            place_output_transitions[k] = frozenset(v)
                
        #+ place_input_transitions
        self.place_input_transitions = place_input_transitions
        #+ place_output_transitions
        self.place_output_transitions = place_output_transitions
        
        #+ place_input_arcs
        self.place_input_arcs = place_input_arcs
        #+ place_output_arcs
        self.place_output_arcs = place_output_arcs
        
    _compute_place_output_arcs = _compute_place_input_arcs = _compute_place_output_transitions =_compute_place_input_transitions
        
    def _compute_deadlock_matrix(self):
        places = _reverse_index(self._net.get_sorted_places())
        transitions = self._net.get_sorted_transitions()
        cols = len(places)
        dl_rows = 0
        tr_rows = 0
        # If place has no input arcs -> place is a deadlock.
        # If place has no output arcs -> http://cdn.instanttrap.com/trap.jpg
        for transition in transitions:
            dl_rows += len(transition.output_arcs)
            tr_rows += len(transition.input_arcs)
        
        #- place_input
        places_without_input = [place for place in places if not self.place_input_arcs[place]]
        
        #- place_output
        places_without_output = [place for place in places if not self.place_output_arcs[place]]
        
        dl_rows += len(places_without_input)
        tr_rows += len(places_without_output)
        
        dl_A = np.zeros((dl_rows, cols))
        tr_A = np.zeros((tr_rows, cols))
        
        for i,p in enumerate(places_without_input):
            dl_A[i,places[p]] = 1
            
        for i,p in enumerate(places_without_output):
            tr_A[i,places[p]] = 1
        
        dl_i = len(places_without_input)
        tr_i = len(places_without_output)
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
        
        self.deadlocks = [ArraySubclass(dl) for dl in self.deadlocks] 
        uncovered_deadlocks = []
        structural_uncovered_deadlocks = []
        
        places = self._net.get_sorted_places()
        
        #- traps
        traps = self.traps
        for deadlock in self.deadlocks:
            deadlock.has_trap = deadlock.has_marked_trap = False
            for trap in traps:
                if all(deadlock>=trap):
                    deadlock.has_trap = True
                    if is_marked_trap(trap, places):
                        deadlock.has_marked_trap = True
                        break
            if not deadlock.has_trap:
                structural_uncovered_deadlocks.append(deadlock)
            elif not deadlock.has_marked_trap:
                uncovered_deadlocks.append(deadlock)
        
        #+ uncovered_deadlocks
        self.uncovered_deadlocks = uncovered_deadlocks
        #+ structural_uncovered_deadlocks
        self.structural_uncovered_deadlocks = uncovered_deadlocks
                
    _compute_uncovered_deadlocks = _compute_structural_uncovered_deadlocks = _compute_deadlocks   
        
        
    def _compute_traps(self):
        #- trap_matrix
        #+ traps
        self.traps, _ = tss.solve(self.trap_matrix, True, limit=1) 
        for i, trap in enumerate(self.traps):
            self.traps[i] = ArraySubclass(trap)
        marked_traps = []
        places = self._net.get_sorted_places()
        for trap_vector in self.traps:
            trap_vector.is_marked_trap = False
            if is_marked_trap(trap_vector, places):
                marked_traps.append(trap_vector)
                trap_vector.is_marked_trap = True
        #+ marked_traps
        self.marked_traps = marked_traps
          
    _compute_marked_traps = _compute_traps
                
    def _compute_liveness(self):
        #- uncovered_deadlocks
        #- free_choice
        if self.free_choice:
            liveness = Tristate(not bool(self.uncovered_deadlocks))
        else:
            liveness = Tristate(None)
        self.liveness = liveness
        
    def _compute_structural_liveness(self):
        #- structural_uncovered_deadlocks
        if self.free_choice:
            structural_liveness = Tristate(not bool(self.structural_uncovered_deadlocks))
        else:
            structural_liveness = Tristate(None)
        #+ structural_liveness
        self.structural_liveness = structural_liveness
        
    def _compute_state_machine(self):
        result = True
        for transition in self._net.get_transitions_iter():
            if not(sum_weight(transition.input_arcs) == sum_weight(transition.output_arcs) <= 1):
                result = False
                break
        #+ state_machine
        self.state_machine = result     
        
    def _compute_marked_graph(self):
        result = True
        #- place_input
        #- place_output
        for place in self._net.get_places_iter():
            if not(sum_weight(self.place_input_arcs[place]) == sum_weight(self.place_output_arcs[place]) <= 1):
                result = False
                break
    
        #+ marked_graph
        self.marked_graph = result
        
    def _check_output_place_property(self, check_property):
        places = self._net.get_places()
        result = True
        for i in xrange(len(places)-1):
            place1 = places[i]
            #- place_output_arcs
            poa1 = self.place_output_arcs[place1]
            #- place_output_transitions
            pot1 = self.place_output_transitions[place1]
            if not pot1:
                continue
            for j in xrange(i+1,len(places)):
                place2 = places[j]
                #- place_output_arcs
                poa2 = self.place_output_arcs[place2]
                #- place_output_transitions
                pot2 = self.place_output_transitions[place2]
                if not pot2:
                    continue
                if not pot2.intersection(pot1, pot2):
                    continue
                if not check_property(poa1, poa2, pot1, pot2):
                    result = False
                    break
        return result
        
    def _compute_free_choice(self):
        #+ free_choice
        self.free_choice = self._check_output_place_property(lambda poa1, poa2, pot1, pot2:sum_weight(poa1)==sum_weight(poa2)<=1)
        
    def _compute_extended_free_choice(self):
        #+ extended_free_choice
        self.extended_free_choice = self._check_output_place_property(lambda poa1, poa2, pot1, pot2:pot1==pot2)

    def _compute_simple(self):
        #+ simple
        self.simple = self._check_output_place_property(lambda poa1, poa2, pot1, pot2:(sum_weight(poa1)<=1) or (sum_weight(poa2)<=1))

    def _compute_asymmetric(self):
        #+ asymmetric
        self.asymmetric = self._check_output_place_property(lambda poa1, poa2, pot1, pot2:pot1.issubset(pot2) or pot2.issubset(pot1))

    def _compute_regulated(self):
        result = False
        #- A_rank
        rank_complete = self.A_rank == len(self._net.get_places()) > 0
        if rank_complete and self.marked_graph:
            result = Tristate(True)
        elif not rank_complete:
            result = Tristate(False)
        else:
            result = Tristate(None)
        #+ regulated
        self.regulated = result
            
