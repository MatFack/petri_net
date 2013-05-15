# -*- coding: utf-8 -*-

import re
from collections import defaultdict

'''

'''

def skb(x):
    if '|' not in x or x=='EPS':
        return x
    
    b = {'(':')',
         '{':'}'}
    if x.count("{") + x.count("(")==1 and x[0] in ('{', '(') and b[x[0]] == x[-1] :
        return x
    return '('+x+')' 
    
COUNT = 0
    
sentinel = object()
    
def _make_regex(fr, to, graph, k, cache):
    global COUNT
    global sentinel
    COUNT += 1
    try:
        if len(cache['graph'][fr])==0:
            return None
    except:
        return None
    if k==0:
        val = graph.get((fr, to), None)
        if val and fr==to:
            val = '{'+val+'}'
        return val
    a = cache.get((fr, to, k-1), sentinel)
    if a is sentinel:
        a = _make_regex(fr, to, graph, k-1, cache)
        cache[(fr, to, k-1)] = a
    
    b = cache.get((fr, k, k-1), sentinel)
    if b is sentinel:
        b = _make_regex(fr, k, graph, k-1, cache)
        cache[(fr, k, k-1)] = b
        
    d = cache.get((k, to, k-1), sentinel)
    if d is sentinel:    
        d = _make_regex(k, to, graph, k-1, cache)
        cache[(k, to, k-1)] = d
    
    c = cache.get((k, k, k-1), sentinel)
    if c is sentinel:
        c = _make_regex(k, k, graph, k-1, cache)
        cache[(k, k, k-1)] = c
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
            nv[v] = len(nv)+1
        tr = graph[v]
        lst = []
        for c, subv in tr.iteritems():
            if subv not in nv:
                nv[subv] = len(nv)+1
            lst.append((c, nv[subv]))
        new_graph[nv[v]] = lst
    new_new_graph = {}
    for vv in new_graph:
        for bb,toto in new_graph[vv]:
            val = new_new_graph.get((vv, toto), '')
            if val: val+= '|'
            val += bb
            new_new_graph[(vv, toto)] = val
    start = nv[start]
    new_fin = [nv[fin] for fin in finish]
    cache = {}
    cache['graph'] = new_graph
    k = len(graph)
    for fin in new_fin:
        result.append(_make_regex(start, fin, new_new_graph, k, cache))
    return "| \n".join(skb(x or 'EPS') for x in result)

