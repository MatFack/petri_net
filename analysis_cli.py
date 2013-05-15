

# -*- coding: utf-8 -*-

import os
if os.name is 'nt':
    import util.win32_unicode_argv
import petri.reachability_graph
import petri.petri
import petri.dfa_analysis
import argparse
import json
from pprint import pprint    
    
def to_state(s, states):
    return tuple(eval(s))


if __name__=='__main__':
  
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-o", "--output", dest="out_filename",
                  help="write output to FILE", metavar="FILE")
    
    parser.add_argument('input_file')
    
    parser.add_argument('initial_state')
    
    parser.add_argument('final_state', nargs='+')

    args = parser.parse_args()
    encoder = json.JSONEncoder()
    filename = args.input_file
    with open(filename, 'rb') as f:
        data = json.load(f)
    graph = petri.reachability_graph.ReachabilityGraph.from_json_struct(data)
    initial_state = to_state(args.initial_state, graph.names)
    final_states = [to_state(final_state, graph.names) for final_state in args.final_state]
    print graph.explored
    result = petri.dfa_analysis.make_regex(initial_state, final_states, graph.explored)
    if args.out_filename: 
        with open(args.out_filename, 'wb') as f:
            f.write(result)
    else:
        print result
