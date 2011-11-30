#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import shelve
import atexit
from fnmatch import fnmatch
import errno
import re
import random

# TODO La "key" d'un node ha de ser la seva uri, no el seu name. El nom s'extrau de la uri.
# TODO save labels attached on a file into the xattr of this file

def pathlist(path):
  return [node for node in path.split('/') if node != ""]

QUERY_PREFIX = '!'
QUERY_PREFIX_LEN = len(QUERY_PREFIX)

# GRAMATICA
# expr -> expr + term | expr - term | term
# term -> term * fact | term / fact | fact
# fact -> ^set | set
# set  -> func fact | func fact,fact | (expr) | name | *

# reserved words (tokens)
rws = {
   'file'     : '~'
  ,'label'    : '#'
  ,'parent'   : '>'
  ,'child'    : '<'
  ,'add'      : '+'
  ,'rem'      : '-'
  ,'sep'      : ','
  ,'not'      : '^'
  ,'all'      : '*'
  ,'any'      : '?'
  ,'intersect': '&'
  ,'union'    : '|'
  ,'except'   : '¬'
  ,'open'     : '['
  ,'close'    : ']'
  ,'new'      : '@'
  ,'del'      : 'X'
   }

class URIGraph():
  def __init__(self,lfsfile):
    self.lfs={}
    try:
      self.lfs = shelve.open(lfsfile,writeback=True)
      atexit.register(self.lfs.close)
    except:
      print "cannot shelve.open",a[0]

    if not 'nodes' in self.lfs:
      self.lfs['nodes'] = {}
    if not 'uris' in self.lfs:
      self.lfs['uris'] = {}
    if not 'parents' in self.lfs:
      self.lfs['parents']={}
    if not 'childs' in self.lfs:
      self.lfs['childs']={}

    self.interpreter=_interpreter(self.lfs)

  def query(self,query_str):
    self.interpreter._query(query_str)     
    return []

  def create_node(self,uri):
    if uri != "":
      if self.exists_node(uri):
        return -errno.EEXIST
      #TODO lenght
      id=(("%%0%dX" % (8 * 2)) % random.getrandbits(8 * 8)).decode("ascii") 
      self.lfs['nodes'][id] = uri
      self.lfs['uris'][uri] = id
      self.lfs['childs'][id] = {}
      self.lfs['parents'][id] = {}

  def get_id(self,uri):
    if uri in self.lfs['uris']:
      return self.lfs['uris'][uri]
    return 0
  
  def exists_node(self,uri):
    if self.get_id(uri):
      return 1
    return 0

  def delete_node(self,uri):
    id=self.get_id(uri)

    if id in self.lfs['nodes']:
      del self.lfs['nodes'][id]

    if uri in self.lfs['uris']:
      del self.lfs['uris'][uri]
      
    if id in self.lfs['parents']:
      for parent in self.lfs['parents'][id]: 
        if parent in self.lfs['childs']:
          if id in self.lfs['childs'][id]:
            del self.lfs['childs'][parent][id]
      del self.lfs['parents'][id]
      
    if id in self.lfs['childs']:
      for child in self.lfs['childs'][id]:
        if child in self.lfs['parents']:
          if id in self.lfs['parents'][child]:
            del self.lfs['parents'][child][id]
      del self.lfs['childs'][id]
      
  def change_uri(self,old_uri,new_uri):
    if old_uri != '' and new_uri != '':
      if self.exists_node(new_uri):
        return -errno.EEXIST
      id=self.get_id(old_uri)
      if id in self.lfs['nodes']:
        del self.lfs['uris'][old_uri]
        self.lfs['nodes'][id]=new_uri
        self.lfs['uris'][new_uri] = id

  def exists_relation(self,parent_id,child_id):
    # TODO: controlar que no s'inserte una relacio ciclica (funcio recursiva)
    return child_id in self.lfs['parents'] and parent_id in self.lfs['parents'][child_id]
    #or/and self.lfs['childs'][parent_id][child_id]

  def add_label_ids_to_node_ids(self,parent_ids,child_ids):
    for child_id in child_ids:
      if child_id in self.lfs['nodes']:        
        for parent_id in parent_ids:
          if parent_id != child_id:
            if parent_id in self.lfs['nodes']:
              if not self.exists_relation(child_id,parent_id):
                self.lfs['parents'][child_id][parent_id]=1
                self.lfs['childs'][parent_id][child_id]=1

  def remove_label_ids_from_node_ids(self,parent_ids,child_ids):
    for child_id in child_ids:
      for parent_id in parent_ids:            
        if parent_id != child_id:
          if child_id in self.lfs['parents']:
            if parent_id in self.lfs['parents'][child_id]:
              del self.lfs['parents'][child_id][parent_id]
          if parent_id in self.lfs['childs']:
            if child_id in self.lfs['childs'][parent_id]:
              del self.lfs['childs'][parent_id][child_id]
 

  def add_label_to_node(self,parent,child):
    child_id = self.get_id(child)
    parent_id = self.get_id(parents)            
    self.add_label_ids_to_node_ids([parent_id],[child_id])

  def add_labels_to_node(self,parents,child):
    child_id = self.get_id(child)
    parent_ids = []
    for parent in parents:
      parent_id = self.get_id(parent)            
      parent_ids.append(parent_id)
    self.add_label_ids_to_node_ids(parent_ids,[child_id])

  def add_labels_to_nodes(self,parents,childs):
    child_ids = []
    parent_ids = []
    for child in childs:
      child_id = self.get_id(child)
      child_ids.append(child_id)
    for parent in parents:
      parent_id = self.get_id(parent)
      parent_ids.append(parent_id)
    self.add_label_ids_to_node_ids(parent_ids,child_ids)

  def remove_label_from_node(self,parent,child):
    child_id = self.get_id(child)
    parent_id = self.get_id(parent)
    self.remove_label_ids_from_node_ids([parent_id],[child_id])

  def remove_labels_from_node(self,parents,child):
    child_id = self.get_id(child)
    parent_ids = []
    for parent in parents:
      parent_id = self.get_id(parent,)
      parent_ids.append(parent_id)
      self.remove_label_ids_from_node_ids(parent_ids,[child_id])

  def remove_labels_from_nodes(self,parents,childs):
    child_ids = []
    parent_ids = []
    for child in childs:
      child_id = self.get_id(child)
      child_ids.append(child_id)
    for parent in parents:
      parent_id = self.get_id(parent)
      parent_ids.append(parent_id)
    self.remove_label_ids_to_node_ids(parent_ids,child_ids)


  def printlfs(self):
    print "@#@ NODES @#@"
    for id in self.lfs['nodes']:
      print "ID:",id,"uri",self.lfs['nodes'][id]
    print
    print "~&~ RELATIONS ~&~"
    print "      && PARENTS &&"
    for child_id in self.lfs['parents']:
      print "OF",child_id,self.lfs['nodes'][child_id],":"
      for parent_id in self.lfs['parents'][child_id]:
        print "       @",parent_id,self.lfs['nodes'][parent_id]
    print "      ~~ CHILDS ~~"
    for parent_id in self.lfs['childs']:
      print "OF @",parent_id,self.lfs['nodes'][parent_id],":"
      for child_id in self.lfs['childs'][parent_id]:
        print "      ",tyype,parent_id,self.lfs['nodes'][child_id]

  def empty_brain(self):
    self.lfs['nodes'] = {}
    self.lfs['parents'] = {}
    self.lfs['childs'] = {}


class _interpreter():
  def __init__(self,lfs):
    self._lfs=lfs

  def _query(self,query_str):
    self._pos=0
    self._length = len(query_str)
    self._query = query_str

    token = self._get_token()
    expr,token = self.expr(token)
    for key in expr:
      yield self._lfs['nodes'][key]

  def _get_token(self):
    token = ''
    pos = self._pos
    length = self._length
    query = self._query
    if pos<length:
      while pos<length and query[pos]==" ": pos+=1
      for rw_name in rws:
        rw=rws[rw_name]
        if query[pos]==rw[0]:
          found=1
          for i in range(len(rw)):
            if query[pos + i] != rw[i]:
              found=0
              break
          if found:
            token=rw
            pos+=len(rw)
            break
    if token=='' and pos<length and  (query[pos]=='"'): 
      pos+=1
      while pos < length and fnmatch(query[pos],'*') and query[pos]!='"':
        if query[pos]=="\\" and (query[pos+1]=='"' or query(pos+1)=="'"):
          token+=query[pos+1]
          pos+=2
        else:
          token+=query[pos]
          pos+=1
      if pos<length and (query[pos]=="\""):
        pos+=1
      else:
        print "error token",query,"[",pos,"]"
        return 0
    self._pos = pos
    return token

  def expr(self,token):
    expr = set([])
    term,token = self.term(token)
    expr = term
    if token == rws['union']:
      union,token = self.union(token)
      expr2,token = self.expr(token)
      expr = expr | expr2
    elif token == rws['except']:
      exceept,token = self.exceept(token)
      expr2,token = self.expr(token)
      expr = expr - expr2
    return expr,token

  def term(self,token):
    term = set([])
    fact,token = self.fact(token)
    term = fact
    if token == rws['intersect']:
      intersect,token = self.intersect(token)
      expr,token = self.expr(token)
      term = term & expr
    return term,token
    
  def fact(self,token):
    fact = set([])
    if token == rws['not']:
      noot,token = self.noot(token)
      seet,token = self.seet(token)
      fact = set(self._lfs['nodes']) - seet
    else:
      seet,token = self.seet(token)
      fact = seet
    return fact,token

  def seet(self,token):
    # TODO: Afegir algun caracter que siginfique algun element ? (o ningun) (o algun)
    seet = set([])
    if token == rws['open']:
      token = self._get_token()
      fact,token = self.expr(token)
      seet = fact
      token = self._get_token()
    elif token == rws['close']:
      token = self._get_token
    elif token == rws['file']:
      token = self._get_token()
      fact,token = self.fact(token)
      for node in fact:
        if self._lfs['nodes'][node].find('file://') == 0:
          seet = seet | set([node])
    elif token == rws['label']:
      token = self._get_token()
      fact,token = self.fact(token)
      for node in fact:
        if self._lfs['nodes'][node].find('label://') == 0:
          seet = seet | set([node])
    elif token == rws['parent']:
      token = self._get_token()
      fact,token = self.fact(token)
      # TODO! Ha de ser pare de tots els childs, no només d'algun
      for child in fact:
        if child in self._lfs['parents']:
          seet = seet | set(self._lfs['parents'][child])
    elif token == rws['child']:
      token = self._get_token()
      fact,token = self.fact(token)
      # TODO! Ha de ser fill de tots els parents, no només d'algun
      for parent in fact:
        if parent in self._lfs['childs']:
          seet = seet | set(self._lfs['childs'][parent])
    elif token == rws['add']:
      token = self._get_token()
      fact,token = self.fact(token)
      fact2 = []
      if token == rws['sep']:
        token = self._get_token()
        fact2,token = self.fact(token)
      else:
        print "Error token: expected:",rws['sep'], "got:",token
      self.add_label_ids_to_node_ids(fact,fact2)
      seet = seet | set(fact) | set(fact2)
    elif token == rws['rem']:
      token = self._get_token()
      fact,token = self.fact(token)
      fact2 = []
      if token == rws['sep']:
        token = self._get_token()
        fact2,token = self.fact(token)
      else:
        print "Error token: expected:",rws['sep'], "got:",token
      self.remove_label_ids_from_node_ids(fact,fact2)
      seet = seet | set(fact) | set(fact2)
    elif token == rws['all']:
      seet = set(self._lfs['nodes'])
      token = self._get_token()
    elif fnmatch(token, '*'):
      for node in self._lfs['nodes']:
        node_uri=self._lfs['nodes'][node]
        if fnmatch(token, '^[a-z]://*'):  
          if node_uri == token:
            seet = set([node])
        elif os.path.basename(urlparse.urlparse(self._lfs['nodes'][node])[2])==token:
          seet = set([node])
      token = self._get_token()
    else:
      print "error seet",token
      return 0
    return seet,token

  def intersect(self,token):
    if not rws['intersect'] == token:
      print "error intersect", token
      return 0
    token = self._get_token()
    return "",token

  def exceept(self,token):
    if not rws['except'] == token:
      print "error exceept", token
      return 0
    token = self._get_token()
    return "",token

  def union(self,token):
    if not rws['union'] == token:
      print "error union", token
      return 0
    token = self._get_token()
    return "",token

  def noot(self,token):
    if not rws['not'] == token:
      print "error noot", token
      return 0
    token = self._get_token()
    return "",token

  def open(self,token):
    if not token == rws['open']:
      print "error open", token
      return 0
    token = self._get_token()
    return "",token
        
  def close(self,token):
    if not token == rws['close']:
      print "error close", token
      return 0
    token = self._get_token()
    return "",token



if __name__ == "__main__":
  import os.path
  import sys
  le = LfsEngine("%s/.lfs.db" % os.path.expanduser('~'))
  if len(sys.argv)==1:
    le.printlfs()  
  if len(sys.argv)==2:
    print "::::nodes::::"    
    nodes = le.query(sys.argv[1])
    count = 0
    for r in nodes:
      print r
      count += 1
    print "Total:",count
