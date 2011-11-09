#!/usr/bin/python
# -*- coding: utf-8 -*-
import shelve
import atexit
from fnmatch import fnmatch
import errno
import re
import random

# ./labelengine.py -d -o lfsdb=/path/to/lfs.db "query"
# TODO save labels attached on a file into the xattr of this file
# la "key" d'un node file ha de ser la seva uri, no el seu name. Poden haver dos nodes en el mateix nom, pero no la mateixa uri, tot se consulta per uri..., (etiquetar uri) uri-labeler

TYPE_LABEL=0
TYPE_FILE=1

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
   

class LfsEngine():
  def __init__(self,*a,**kw):
    self.NodeEngine = NodeEngine(a[0])

  def query(self,le_query_str,offset=-1):
    for r in self.NodeEngine._lfs_query(le_query_str):
      yield r

  def execute(self,le_query_str):
    for r in self.NodeEngine._lfs_query(le_query_str):
      pass
    
  def getid(self,name,tyype=-1):
    return self.NodeEngine.getid(name,tyype)
  
  #def get_uri(self, name) # assumir type=FILE

  def exists_node(self,name,tyype=-1):
    return self.NodeEngine.exists_node(name,tyype)

  def create_label(self,name):
    return self.NodeEngine.create_label(name)

  def create_file(self,name,uri):
    return self.NodeEngine.create_file(name,uri)

  def delete_node(self,name):
    self.NodeEngine.delete_node(name)
    
  def rename_node(self,old_name,new_name):
    self.NodeEngine.rename_node(old_name,new_name)

  def exists_relation(self,parentid,childid):
    return self.NodeEngine.exists_relation(parentid,childid)

  def add_label_to_node(self,parent,child):
    self.NodeEngine.add_label_to_node(parent,child)

  def add_labels_to_node(self,parents,child):
    self.NodeEngine.add_labels_to_node(parents,child)

  def add_labels_to_nodes(self,parents,childs):
    self.NodeEngine.add_labels_to_nodes(parents,childs)

  def remove_label_from_node(self,parent,child):
    self.NodeEngine.remove_label_from_node(parent,child)

  def remove_labels_from_node(self,parents,child):
    self.NodeEngine.remove_labels_from_node(parents,child)

  def remove_labels_from_nodes(self,parents,childs):
    self.NodeEngine.remove_labels_from_nodes(parents,childs)

  def printlfs(self):
    self.NodeEngine.printlfs()

  def empty_brain(self):
    self.NodeEngine.empty_brain()



class NodeEngine():
  def __init__(self,lfsdb_file):
    lfs={}
    try:
      lfs = shelve.open(lfsdb_file,writeback=True)
      atexit.register(lfs.close)
    except:
      print "cannot shelve.open",a[0]

    self._lfs=self.init_lfs(lfs)
    self._result = []
    self._pos = 0
    self._query = ""
    self._length = 0

  def init_lfs(self,lfs):
    self.lfs=lfs
    if not 'ids' in self.lfs:
      self.lfs['ids'] = {}
    if not 'names' in self.lfs:
      self.lfs['names'] = {}
    if not 'types' in self.lfs:
      self.lfs['types'] = {TYPE_FILE : {},TYPE_LABEL : {}}
    if not 'parents' in self.lfs:
      self.lfs['parents']={}
    if not 'childs' in self.lfs:
      self.lfs['childs']={}


  ## INTERPRETER
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
    if token=='' and pos<length  \
    and  (query[pos]=='"'): 
      pos+=1
      while pos < length and fnmatch(query[pos],'*')  \
      and query[pos]!='"':
        if query[pos]=="\\"  \
        and (query[pos+1]=='"'  \
        or query(pos+1)=="'"):
          token+=query[pos+1]
          pos+=2
        else:
          token+=query[pos]
          pos+=1
      if pos<length  \
      and (query[pos]=="\""):
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
      fact = set(self.lfs['ids']) - seet
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
        if self.lfs['ids'][node]['type']==TYPE_FILE:
          seet = seet | set([node])
    elif token == rws['label']:
      token = self._get_token()
      fact,token = self.fact(token)
      for node in fact:
        if self.lfs['ids'][node]['type']==TYPE_LABEL:
          seet = seet | set([node])
    elif token == rws['parent']:
      token = self._get_token()
      fact,token = self.fact(token)
      # TODO! Ha de ser pare de tots els childs, no només d'algun
      for child in fact:
        if child in self.lfs['parents']:
          seet = seet | set(self.lfs['parents'][child])
    elif token == rws['child']:
      token = self._get_token()
      fact,token = self.fact(token)
      # TODO! Ha de ser fill de tots els parents, no només d'algun
      for parent in fact:
        if parent in self.lfs['childs']:
          seet = seet | set(self.lfs['childs'][parent])
    elif token == rws['add']:
      token = self._get_token()
      fact,token = self.fact(token)
      fact2 = []
      if token == rws['sep']:
        token = self._get_token()
        fact2,token = self.fact(token)
      else:
        print "Error token: expected:",rws['sep'], "got:",token
      self.add_labelids_to_nodeids(fact,fact2)
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
      self.remove_labelids_from_nodeids(fact,fact2)
      seet = seet | set(fact) | set(fact2)
    elif token == rws['all']:
      seet = set(self.lfs['ids'])
      token = self._get_token()
    elif fnmatch(token, '*'):
      for node in self.lfs['ids']:
        if self.lfs['ids'][node]['name']==token:
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


  def _lfs_query(self,query_str):
    self._pos=0
    self._length = len(query_str)
    self._query = query_str
    token = self._get_token()
    expr,token = self.expr(token)
    for nodeid in expr:
      yield self.lfs['ids'][nodeid]
    # END INTERPRETER


  def query(self,le_query_str,offset=-1):
    for r in self._lfs_query(le_query_str):
      yield r

  def execute(self,le_query_str):
    for r in self._lfs_query(le_query_str):
      pass
    

  def getid(self,name,tyype=-1):
    if name in self.lfs['names']:
      if tyype == -1:
        return self.lfs['names'][name] # realment esta retornant el id
      else:
        if self.lfs['ids'][self.lfs['names'][name]]['type'] == tyype:
          return self.lfs['names'][name] # realment esta retornant el id
    return -1
  
  #def get_uri(self, name) set_uri# assumir type=FILE

  def exists_node(self,name,tyype=-1):
    return self.getid(name,tyype)  in self.lfs['ids']

  def create_label(self,name):
    if name != "":
      if self.exists_node(name):
        return -errno.EEXIST
      iid=(("%%0%dX" % (8 * 2)) % random.getrandbits(8 * 8)).decode("ascii") #TODO lenght
      self.lfs['ids'][iid]={'name':name,'type':TYPE_LABEL}
      self.lfs['names'][name]=iid
      self.lfs['parents'][iid] = {}
      self.lfs['childs'][iid] = {}
      self.lfs['types'][TYPE_LABEL][iid] = 1
      return iid

  def create_file(self,name,uri):
    if name!= "":
      if self.exists_node(name):
        return -errno.EEXIST
      iid=(("%%0%dX" % (8 * 2)) % random.getrandbits(8 * 8)).decode("ascii") #TODO lenght
      self.lfs['ids'][iid]={'name':name,'type':TYPE_FILE, 'uri':uri}
      self.lfs['names'][name]=iid
      self.lfs['parents'][iid] = {}
      self.lfs['types'][TYPE_FILE][iid] = 1
      return iid

  def delete_node(self,name):
    nodeid = self.getid(name)
    if nodeid in self.lfs['ids']:
      del self.lfs['ids'][nodeid]
      
      if nodeid in self.lfs['parents']:
        for parent in self.lfs['parents'][nodeid]: 
          del self.lfs['childs'][parent][nodeid]
        del self.lfs['parents'][nodeid]
        
      if nodeid in self.lfs['childs']:
        for child in self.lfs['childs'][nodeid]: 
          del self.lfs['parents'][child][nodeid]
        del self.lfs['childs'][nodeid]
        
      if nodeid in self.lfs['types'][TYPE_LABEL]:
        del self.lfs['types'][TYPE_LABEL][nodeid]
        
      if nodeid in self.lfs['types'][TYPE_FILE]:
        del self.lfs['types'][TYPE_FILE][nodeid]
        
      if name in self.lfs['names']:
        del self.lfs['names'][name]

  def rename_node(self,old_name,new_name):
    if old_name != '' and new_name != '':
      if self.exists_node(new_name):
        return -errno.EEXIST
      iid=self.getid(old_name)
      if iid in self.lfs['ids']:
        del self.lfs['names'][old_name]
        self.lfs['ids'][iid]['name']=new_name
        self.lfs['names'][new_name] = iid

  def exists_relation(self,parentid,childid):
    # TODO: controlar que no s'inserte una relacio ciclica
    return childid in self.lfs['parents'] and parentid in self.lfs['parents'][childid]
    #or/and self.lfs['childs'][parentid][childid]

  def add_labelids_to_nodeids(self,parentids,childids):
    for childid in childids:
      if childid in self.lfs['ids']:        
        for parentid in parentids:
          if parentid != childid and parentid in self.lfs['ids'] and self.lfs['ids'][parentid]['type'] == TYPE_LABEL \
          and not self.exists_relation(childid,parentid):
            self.lfs['parents'][childid][parentid]=1
            self.lfs['childs'][parentid][childid]=1

  def add_label_to_node(self,parent,child):
    childid = self.getid(child)
    parentid = self.getid(parent,TYPE_LABEL)            
    self.add_labelids_to_nodeids([parentid],[childid])

  def add_labels_to_node(self,parents,child):
    childid = self.getid(child)
    parentids = []
    for parent in parents:
      parentid = self.getid(parent,TYPE_LABEL)            
      parentids.append(parentid)
    self.add_labelids_to_nodeids(parentids,[childid])

  def add_labels_to_nodes(self,parents,childs):
    childids = []
    parentids = []
    for child in childs:
      childid = self.getid(child)
      childids.append(childid)
    for parent in parents:
      parentid = self.getid(parent,TYPE_LABEL)
      parentids.append(parentid)
    self.add_labelids_to_nodeids(parentids,childids)

  def remove_labelids_from_nodeids(self,parentids,childids):
    for childid in childids:
      for parentid in parentids:            
        if parentid != childid:
          if 'parents' in self.lfs and childid in self.lfs['parents'] and parentid in self.lfs['parents'][childid]:
            del self.lfs['parents'][childid][parentid]
          if 'childs' in self.lfs and parentid in self.lfs['childs'] and childid in self.lfs['childs'][parentid]:
            del self.lfs['childs'][parentid][childid]

  def remove_label_from_node(self,parent,child):
    childid = self.getid(child)
    parentid = self.getid(parent,TYPE_LABEL)
    self.remove_labelids_from_nodeids([parentid],[childid])

  def remove_labels_from_node(self,parents,child):
    childid = self.getid(child)
    parentids = []
    for parent in parents:
      parentid = self.getid(parent,TYPE_LABEL)
      parentids.append(parentid)
      self.remove_labelids_from_nodeids(parentids,[childid])

  def remove_labels_from_nodes(self,parents,childs):
    childids = []
    parentids = []
    for child in childs:
      childid = self.getid(child)
      childids.append(childid)
    for parent in parents:
      parentid = self.getid(parent,TYPE_LABEL)
      parentids.append(parentid)
    self.remove_labelids_to_nodeids(parentids,childids)


  def printlfs(self):
    print "@#@ NODES @#@"
    print self.lfs
    print
    print "~&~ RELATIONS ~&~"
    print "      && PARENTS &&"
    for childid in self.lfs['parents']:
      tyype = "#"
      if self.lfs['ids'][childid]['type'] == TYPE_LABEL: tyype = "@"
      print "OF",tyype,childid,self.lfs['ids'][childid]['name'],":"
      for parentid in self.lfs['parents'][childid]:
        print "       @",parentid,self.lfs['ids'][parentid]['name']
    print "      ~~ CHILDS ~~"
    for parentid in self.lfs['childs']:
      print "OF @",parentid,self.lfs['ids'][parentid]['name'],":"
      for childid in self.lfs['childs'][parentid]:
        tyype = "@"
        if self.lfs['ids'][childid]['type'] == TYPE_LABEL: tyype = "@"
        print "      ",tyype,parentid,self.lfs['ids'][childid]['name']


  def empty_brain(self):
    self.lfs['ids'] = {}
    self.lfs['names'] = {}
    self.lfs['types'] = {TYPE_FILE : {},TYPE_LABEL : {}}
    self.lfs['parents'] = {}
    self.lfs['childs'] = {}

def usage():
  print """
  labelfs lfs.db 'query'
  labelfs lfs.db --empty-brain
"""
if __name__ == "__main__":
  import os
  import sys
  from os.path import isfile,isdir,dirname,basename
  if len(sys.argv)>1:
    if isdir(sys.argv[1]):
      le = LfsEngine(sys.argv[1])
  if len(sys.argv)>2:
    if sys.argv[2] == '--empty_brain':
      le.empty_brain()
    elif sys.argv[2] == "--print":
      le.printlfs()
    elif sys.argv[2] == '-t':
      le.create_label(sys.argv[3])
    elif sys.argv[2] == '-f':
      le.create_file(sys.argv[3])
    else:
      print "::::nodes::::"    
      nodes = le.query(sys.argv[2])
      count = 0
      for r in nodes:
        print r
        count += 1
      print "Total:",count
