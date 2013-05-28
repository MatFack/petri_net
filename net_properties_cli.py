
from petri.net_properties import PetriProperties, Tristate


            
import os
import sys
if os.name is 'nt':
    import util.win32_unicode_argv
import petri.petri
import argparse
import json
import traceback
import glob
import numpy as np

class NumpyAwareJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        #print type(obj)
        elif isinstance(obj, Tristate):
            return obj.value
        return json.JSONEncoder.default(self, obj)
    
    
def get_filenames(filenames):
    for fname in filenames:
        if any(c in fname for c in '*?[]'):
            for name in glob.glob(fname):
                yield name
        else:
            yield fname




if __name__=='__main__':
       
        
    p = PetriProperties()
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    
    parser.add_argument("-o", "--output", dest="out_filename",
                  help="write output to FILE", metavar="FILE")
    
    parser.add_argument('input_file', nargs='+')
    JSON_FORMAT, TEXT_FORMAT = 'json', 'text'
    parser.add_argument("-f", "--format",
                  default=JSON_FORMAT, choices=[TEXT_FORMAT, JSON_FORMAT],
                  help="input file format")
    
    all_properties = ','.join(field for field in p._fields if not field.endswith('_error'))
    parser.add_argument("-p", "--properties", dest="properties",
              default=all_properties,
              help="properties to be computed")
    args = parser.parse_args()
    from pprint import pprint
    whole_result = {}
    encoder = NumpyAwareJSONEncoder(indent=2, encoding='utf-8')
    errors = total = problems =0
    for filename in get_filenames(args.input_file):
        total += 1
        try:
            with open(filename, 'rb') as f:
                data = f.read()
            if args.format == JSON_FORMAT:
                data = json.loads(data)
                net = petri.petri.PetriNet.from_json_struct(data)
            elif args.format == TEXT_FORMAT:
                net = petri.petri.PetriNet.from_string(data)
                
            props = PetriProperties(net)
            were_errors = props._process_properties(args.properties.split(','))
            if were_errors:
                problems += 1
            dct = dict(props)
            whole_result[filename] = dct
        except Exception, e:
            print e
            whole_result[filename] = traceback.format_exc()
            errors+=1
    if args.out_filename: 
        #print repr(whole_result)
        result = encoder.encode(whole_result)
        with open(args.out_filename, 'wb') as f:
            f.write(result)
    else:
        pprint(whole_result)
        print "#"*80
    print "Successfully processed %d out of %d nets, %d of which had some errors"%(total-errors, total, problems)
