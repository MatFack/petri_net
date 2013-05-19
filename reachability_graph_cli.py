# -*- coding: utf-8 -*-

import os
if os.name is 'nt':
    import util.win32_unicode_argv
import petri.reachability_graph
import petri.petri
import petri.net_properties
import argparse
import json
from pprint import pprint    
    

if __name__=='__main__':
  
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-o", "--output", dest="out_filename",
                  help="write output to FILE", metavar="FILE")
    
    parser.add_argument('input_file')
    JSON_FORMAT, TEXT_FORMAT = 'json', 'text'
    parser.add_argument("-f", "--format",
                  default=JSON_FORMAT, choices=[TEXT_FORMAT, JSON_FORMAT],
                  help="input file format")
    
    args = parser.parse_args()
    whole_result = {}
    encoder = json.JSONEncoder()
    errors = total = problems =0
    filename = args.input_file
    with open(filename, 'rb') as f:
        data = f.read()
    if args.format == JSON_FORMAT:
        data = json.loads(data)
        net = petri.petri.PetriNet.from_json_struct(data)
    elif args.format == TEXT_FORMAT:
        net = petri.petri.PetriNet.from_string(data)
    properties = petri.net_properties.PetriProperties(net)
    rg = petri.reachability_graph.ReachabilityGraph(net, properties)
    rg.explore(net.get_state())
    dct = rg.to_json_struct()
    whole_result = dct
    if args.out_filename: 
        result = encoder.encode(whole_result)
        with open(args.out_filename, 'wb') as f:
            f.write(result)
    else:
        pprint(whole_result)
