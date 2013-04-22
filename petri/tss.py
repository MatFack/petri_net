# -*- coding: utf-8 -*-

import numpy as np
from pprint import pprint
import re

 
def gcd(x,y):
    while x:
        x, y = y % x, x
    return y
 
def simplify(arr):
    
    com_div = reduce(lambda a,b: gcd(abs(a),abs(b)) if ((a!=0) and (b!=0)) else a+b,arr)
    if com_div==0: return arr
    arr = arr / com_div
    #print com_div,"*",arr
    return arr
 

def filter_minimal(lst):
    if not lst:
        return lst
    max_coord = max(np.max(arr) for arr in lst)*2
    lst2 = [arr*max_coord for arr in lst]
    n = len(lst)
    to_delete = set()
    for i in xrange(n-1):
        if i in to_delete:
            continue
        for j in xrange(i+1,n):
            if j in to_delete:
                continue
            if all(lst2[i]>=lst[j]):
                to_delete.add(i)
                break
            elif all(lst[i]<=lst2[j]):
                to_delete.add(j)
    return [lst[i] for i in xrange(len(lst)) if i not in to_delete]

def filter_equal(lst):
    n = len(lst)
    to_delete = set()
    for i in xrange(n-1):
        if i in to_delete:
            continue
        for j in xrange(i+1,n):
            if j in to_delete:
                continue
            if all(lst[i]==lst[j]):
                to_delete.add(i)
                break
    return [lst[i] for i in xrange(len(lst)) if i not in to_delete]

def combinations_number(value_vec):
    return np.sum(value_vec>0)*np.sum(value_vec<0)+np.sum(value_vec==0)             
 
def solve(matr, ineq=False, limit=-1):
    """
    Get TSS for equation A*x = 0
    If ineq is True, get TSS for A*x >= 0, 0<=x<=1
    """
    A = []
    for row in matr:
        A.append(np.array(row).flatten())
    N = len(A)
    rank = 0
    try:
        M = A[0].shape[0]
    except IndexError:
        return [], rank
    vec_base = [np.zeros((M,),dtype=int) for i in xrange(M)]
    for i in xrange(M):
        vec_base[i][i] = 1
    prev_solutions = []
    row_number = min( ((i, combinations_number(A[i])) for i in xrange(N)), key=lambda x:x[1])[0]
    sol_row = A.pop(row_number)
    for i in xrange(M):
        if ineq:
            if sol_row[i] >= 0:
                prev_solutions.append(vec_base[i])
        else:
            if sol_row[i] == 0:
                prev_solutions.append(vec_base[i])            
    while True:
        if not all(x==0 for x in sol_row):
            rank += 1
        vec_collection = get_generating_collection(sol_row,vec_base, limit)
        vec_collection += prev_solutions
        #print "LEN of vec_collection",len(vec_collection)
        #a = time.time()
        if not ineq:
            vec_collection = filter_minimal(vec_collection)
        else:
            vec_collection = filter_equal(vec_collection)
        #b = time.time()-a
        #print "LEN of filtered vec_collection",len(vec_collection)
        #print "Took",b,"seconds"
        prev_solutions = []
        if not A:
            return vec_collection, rank
        vec_values = []
        next_row_i = -1
        min_score = len(vec_collection)**2
        for i, row in enumerate(A):
            score = 0
            neg,pos = 0,0
            for vec in vec_collection:
                val = np.dot(row, vec)
                if val==0:
                    score+=1
                elif val<0:
                    neg+=1
                else:
                    pos+=1
                    if ineq:
                        score+=1
            score += neg*pos
            if min_score>score:
                min_score = score
                next_row_i = i
        next_row = A.pop(next_row_i)
        for vec in vec_collection:
            val = np.dot(next_row, vec)
            vec_values.append(val)
            if ineq:
                if val >= 0:
                    prev_solutions.append(vec)
            else:
                if val==0:
                    prev_solutions.append(vec)
        if not vec_values:
            return [], rank
        new_vec_values = simplify(vec_values)
        vec_values = new_vec_values
        if all(val>0 for val in vec_values) or all(val<0 for val in vec_values):
            break
        sol_row = np.array(vec_values)
        vec_base = vec_collection
    return [], rank
  
        
def get_generating_collection(lst,vec_base, limit):
    N = lst.shape[0]
    vec_collection = []
    for i in xrange(N):
        for j in xrange(i+1,N):
            if lst[i] * lst[j] < 0:
                new_vec = vec_base[i]*abs(lst[j])+vec_base[j]*abs(lst[i])
                new_vec = simplify(new_vec).astype(int)
                if limit>0:
                    if any(elem > limit for elem in new_vec):
                        continue
                vec_collection.append(new_vec)
    return vec_collection
    
    
    
if __name__=='__main__':
    s = """p1 t1 p2 p3
p1 t2 p4
p3 t3 p4
p4 t4 p1
p3 p2 t5 p1"""
    lines = s.split('\n')
    transitions = []
    states = set()
    for line in lines:
        inp,trans_name,outp = re.split(r'\s(t\d+)\s', line)
        inp = inp.split()
        outp = outp.split()
        states.update(inp)
        states.update(outp)
        transitions.append((inp, trans_name, outp))
    x = [np.zeros(len(transitions)) for state in states]
    for inp,trans_name, outp in transitions:
        col = int(trans_name[1:])-1
        for inp_s in inp:
            row = int(inp_s[1:])-1
            x[row][col] -= 1
        for outp_s in outp:
            row = int(outp_s[1:])-1
            x[row][col] += 1
    pprint(x)
    A = np.matrix(x)
    sol = solve(A)
    print "T-invariants:"
    for s in sol:
        print s
        A = np.matrix(x)
    sol, _ = solve(A.transpose())
    print "S-invariants:"
    for s in sol:
        print s
    print "Ineq"
    A = np.matrix([[-3,-4,5,-6],
                   [2,3,-3,1]])
    sol, _ = solve(A, ineq=True)
    for s in sol:
        print s