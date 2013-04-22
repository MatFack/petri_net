# -*- coding: utf-8 -*-

import re
from collections import defaultdict
 
def skb(x):
    if len(x)==1 or x=='EPS':
        return x
    
    b = {'(':')',
         '{':'}'}
    if x.count("{") + x.count("(")==1 and x[0] in ('{', '(') and b[x[0]] == x[-1] :
        return x
    return '('+x+')' 
    

def _make_regex(fr, to, graph, k, cache):
    val = cache.get((fr, to, k), None)
    try:
        if len(cache['graph'][fr])==0:
            return None
    except:
        return None
    if val:
        return val
    if k==0:
        val = graph.get((fr, to), None)
        if val and fr==to:
            val = '{'+val+'}'
        return val
    a = _make_regex(fr, to, graph, k-1, cache)
    b = _make_regex(fr, k, graph, k-1, cache)
    d = _make_regex(k, to, graph, k-1, cache)
    c = _make_regex(k, k, graph, k-1, cache)
    old_c = c
    if c is None:
        c = 'EPS'
    else:
        if not(c.count("{")==1 and c[0]=='{' and c[-1] == '}'):
            c = '{'+c+'}'
    if (not b) or (not d):
        return a
    else:
        if b == old_c:
            b = 'EPS'
        if d == old_c:
            d = 'EPS'
        bcd = '*'.join(filter(lambda x:x!='EPS', (skb(b), c, skb(d))))
        if a:
            if b == 'EPS' and d == 'EPS':
                if a == old_c:
                    return bcd
            bcd = skb(a)+'|'+bcd
        return bcd

def make_regex(start, finish, graph):
    
    result = []
    nv = {}
    new_graph = {}
    for v in graph:
        if v not in nv:
            nv[v] = len(nv)
        tr = graph[v]
        lst = []
        for c, subv in tr:
            if subv not in nv:
                nv[subv] = len(nv)
            lst.append((c, nv[subv]))
        new_graph[nv[v]] = lst
    new_new_graph = {}
    for vv in new_graph:
        for bb,toto in new_graph[vv]:
            new_new_graph[(vv, toto)] = bb
    start = nv[start]
    new_fin = [nv[fin] for fin in finish]
    cache = {}
    cache['graph'] = new_graph
    k = len(graph)
    for fin in new_fin:
        result.append(_make_regex(start, fin, new_new_graph, k, cache))
    return "| \n".join(skb(x or 'EPS') for x in result)


#regex = make_regex(start,finish, graph)
#print regex