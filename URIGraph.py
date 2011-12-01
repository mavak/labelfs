#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import errno
import shelve
import atexit
from fnmatch import fnmatch
import re
from urlparse import urlparse
from random import getrandbits

# TODO save labels attached on a file into the xattr of this file
# TODO: quote uris?

def uri2path(uri):
  if uri.find("label://")==0:
    return uri[8:]
  else:
    return urlparse(uri)[2]

class URIGraph():
  def __init__(self,graphfile):
    self.graph={}
    try:
      self.graph = shelve.open(graphfile,writeback=True)
      atexit.register(self.graph.close)
    except:
      print "cannot shelve.open",graphfile

    if not 'nodes' in self.graph:
      self.graph['nodes'] = {}
    if not 'uris' in self.graph:
      self.graph['uris'] = {}
    if not 'names' in self.graph:
      self.graph['names'] = {}
    #if not 'schemes' in self.graph:
    #  self.graph['schemes'] = {}
    if not 'parents' in self.graph:
      self.graph['parents']={}
    if not 'childs' in self.graph:
      self.graph['childs']={}
    if not 'roots' in self.graph:
      self.graph['roots']={}

    self.interpreter=Interpreter(self)

  def query(self,query_str):
    for uri in self.interpreter.query(query_str):
      yield uri

  def create(self,uri):
    if uri != "":
      if uri in self.graph['uris']:
        return -errno.EEXIST
      #TODO think lenght
      id=(("%%0%dX" % (8 * 2)) % getrandbits(8 * 8)).decode("ascii") 
      self.graph['nodes'][id] = uri
      self.graph['uris'][uri] = id
      if uri.find("label://")==0:
        name=uri[8:]
      else:
        name = os.path.basename(uri2path(uri))
      if not name in self.graph['names']:
        self.graph['names'][name] = {id: "1"}
      else:
        self.graph['names'][name][id] = "1"
      self.graph['childs'][id] = {}
      self.graph['parents'][id] = {}

  def change_uri(self,old_uri,new_uri):
    if old_uri != '' and new_uri != '':
      if self.exists_node(new_uri):
        return -errno.EEXIST
      id=self.get_id(old_uri)
      if id in self.graph['nodes']:
        del self.graph['uris'][old_uri]
        self.graph['nodes'][id]=new_uri
        self.graph['uris'][new_uri] = id
    # TODO. si canvia el basename, canviar self.graph['names']

  def get_ids(self,key):
    if key in self.graph['nodes']:
      yield key
    elif key in self.graph['uris']:
      yield self.graph['uris'][key]
    elif key in self.graph['names']:
      for id in self.graph['names'][key]:
        yield id

  def get_id(self,uri_or_name):
    for id in self.get_ids(uri_or_name):
      return id
    return 0

  def get_uris(self,name):
    if name in self.graph['names']:
      for id in self.graph['names'][name]:
        yield self.graph['nodes'][id]
  
  def exists(self,uri):
    if self.get_id(uri):
      return 1
    return 0

  def delete(self,uri_or_name):
    for id in self.get_ids(uri_or_name):
      name = os.path.basename(uri2path(self.graph['nodes'][id]))
      uri=""
      if id in self.graph['nodes']:
        uri=self.graph['nodes'][id]
        del self.graph['nodes'][id]

      if uri in self.graph['uris']:
        del self.graph['uris'][uri]

      if name in self.graph['names']:
        if id in self.graph['names'][name]:
          del self.graph['names'][name][id]
        if self.graph['names'][name] == {}:
          del self.graph['names'][name]
        
      if id in self.graph['parents']:
        for parent in self.graph['parents'][id]: 
          if parent in self.graph['childs']:
            if id in self.graph['childs'][id]:
              del self.graph['childs'][parent][id]
        del self.graph['parents'][id]
        
      if id in self.graph['childs']:
        for child in self.graph['childs'][id]:
          if child in self.graph['parents']:
            if id in self.graph['parents'][child]:
              del self.graph['parents'][child][id]
        del self.graph['childs'][id]

  def set_root(self,uri_or_name):
    for id in self.get_ids(uri_or_name):
      self.graph['roots'][id]=1

  def unset_root(self,uri_or_name):
    for id in self.get_ids(uri_or_name):
      if id in self.graph['roots']:
        del self.graph['roots'][id]

  def get_roots(self):
    for id in self.graph['roots']:
      yield self.graph['nodes'][id]

  def add(self,parents,childs):
    for child in childs:
      for child_id in self.get_ids(child):
        for parent in parents:
          for parent_id in self.get_ids(parent):
            self.graph['parents'][child_id][parent_id]=1
            self.graph['childs'][parent_id][child_id]=1

  def remove(self,parents,child):
    for child_id in self.get_ids(child):
      for parent in parents:
        for parent_id in self.get_ids(parent):
          if parent_id in self.graph['parents'][child_id]:
            del self.graph['parents'][child_id][parent_id]
          if parent_id in self.graph['childs']:
            if child_id in self.graph['childs'][parent_id]:
              del self.graph['childs'][parent_id][child_id]

  def get_childs(self,parent):
    for id in self.get_ids(parent):
      if id in self.graph['childs']:
        for child in self.graph['childs'][id]:
          yield self.graph['nodes'][child]

  def printgraph(self):
    print "@#@ NODES @#@"
    for id in self.graph['nodes']:
      print "ID:",id,"uri",self.graph['nodes'][id]
    print
    print "~&~ RELATIONS ~&~"
    print "      && PARENTS &&"
    for child_id in self.graph['parents']:
      print "OF",self.graph['nodes'][child_id],":"
      for parent_id in self.graph['parents'][child_id]:
        print "       @",self.graph['nodes'][parent_id]
    print "      ~~ CHILDS ~~"
    for parent_id in self.graph['childs']:
      print "OF ",self.graph['nodes'][parent_id],":"
      for child_id in self.graph['childs'][parent_id]:
        print "      ",self.graph['nodes'][child_id]
    print "      // ROOTS //"
    for root in self.graph['roots']:
      print "      ",self.graph['nodes'][root]

# GRAMMAR
# expr -> expr | term | expr - term | term
# term -> term * fact | term & fact | fact
# fact -> fact > nodes | nodes [+> ->] nodes | nodes
# nodes  ->  (expr) | ^nodes | [@ X R +R -R] nodes | scheme:nodes | name | *

class Interpreter():
  def __init__(self,urigraph):
    self.urigraph=urigraph

    # TODO: que en les queries se puguen usar tant la key com el value de les reserved_words
    # FUTURE TODO: descendants
    self.RESERVED_WORDS = {
      'create'       : '@'
      ,'delete'      : 'X'
      ,'root'        : 'R'
      ,'set_root'    : '+R'
      ,'unset_root'  : '-R'
      ,'child'   : '>'  # what to do with that? tots els que son fills i pares al mateix temps
      ,'parent'  : '<'
      ,'add'         : '+>'
      ,'remove'      : '->'
      ,'not'      : '^'       # set operations
      ,'all'      : '*'
      ,'any'      : '?'
      ,'intersect': '&'
      ,'union'    : '|'
      ,'except'   : '¬'
      ,'open'     : '['
      ,'close'    : ']'
      ,'print'    : '¬'
       }
    self.scheme_char_regex = re.compile('[a-z]')
    self.scheme_regex = re.compile('[a-z]*:')

  def query(self,query_str):
    self._pos=0
    self._length = len(query_str)
    self._query = query_str
    self.next_token()
    result = self.expr()
    for key in result:
      if key in self.urigraph.graph['nodes']:
        yield self.urigraph.graph['nodes'][key]

  def next_token(self):
    token = ''
    pos = self._pos
    length = self._length
    query = self._query
    if pos<length:
      while pos<length and query[pos]==" ": 
        pos+=1
      if pos<length:
        for rw_name in self.RESERVED_WORDS:
          rw=self.RESERVED_WORDS[rw_name]
          if query[pos]==rw[0]:
            found=1
            for i in range(len(rw)):
              if pos+i<length:
                if query[pos + i] != rw[i]:
                  found=0
                  break
              else:
                found=0
                break
            if found:
              token=rw
              pos+=len(rw)
              break
    if token=='' and pos<length and (query[pos]=='"' or query[pos] == "'"):
      quot=query[pos]
      token=query[pos] 
      pos+=1
      while pos<length and query[pos]!=quot:
        if query[pos]=="\\" and (query[pos+1]==quot):
          token+=query[pos+1]
          pos+=2
        else:
          token+=query[pos]
          pos+=1
      if pos<length and (query[pos]==quot):
        token+=quot
        pos+=1
      else:
        print "error query quotation",query,pos
        return ""
    if token=='' and pos<length:
      while pos<length and self.scheme_char_regex.match(query[pos]):
        token+=query[pos]
        pos+=1
      if token != "" and pos<length and query[pos] == ':':
        token+=':'
        pos+=1
      else:
        print "error query scheme",query,pos
        return ""
    self._pos = pos
    self.token = token
    return token

  def expr(self):
    result=self.term()
    if self.token == self.RESERVED_WORDS['union']:
      self.next_token()
      if self.token != "":
        result2 = self.expr()
        result = result | result2
      else:
        print "Error token: expected expresion"
    elif self.token == self.RESERVED_WORDS['except']:
      self.next_token()
      if self.token != "":
        result2 = self.expr()
        result = result - result2
      else:
        print "Error token: expected expresion"
    return result

  def term(self):
    result=self.fact()
    if self.token == self.RESERVED_WORDS['intersect']:
      self.next_token()
      if self.token != "":
        post_nodes = self.term()
        result = result & post_nodes
      else:
        print "Error token: expected expresion"      
    return result
    
  def fact(self):
    result=set([])
    pre_node_is_all=0
    if self.token == self.RESERVED_WORDS['all']:
      self.next_token()
      pre_node_is_all=1
    else:
      pre_nodes = self.nodes()
    if self.token == self.RESERVED_WORDS['child']:
      self.next_token()
      if self.token == "":
        print "Error token: expected factor"
      elif self.token == self.RESERVED_WORDS['all']:
        self.next_token()
        if pre_node_is_all:
          result = set(self.urigraph.graph['parents'].keys())
        else:
          for parent in pre_nodes:
            if parent in self.urigraph.graph['childs']:
              result = result | set(self.urigraph.graph['childs'][parent].keys())
      else:
        post_nodes = self.fact()
        if pre_node_is_all:
          for child in post_nodes:
            if child in self.urigraph.graph['parents']:
              result = result | set([child])              
        else:
          for child in post_nodes:
            if child in self.urigraph.graph['parents']:
              is_child_of_all_parents_in_pre_nodes=1
              for parent in pre_nodes:
                if not parent in self.urigraph.graph['parents'][child]:
                  is_child_of_all_parents_in_pre_nodes=0
              if is_child_of_all_parents_in_pre_nodes:
                result = result | set([child])

    elif self.token == self.RESERVED_WORDS['parent']:
      self.next_token()
      if self.token == "":
        print "Error token: expected factor"
      elif self.token == self.RESERVED_WORDS['all']:
        self.next_token()
        if pre_node_is_all:
          result = result | set(self.urigraph.graph['childs'].keys())
        else:
          for child in pre_nodes:
            if child in self.urigraph.graph['parents']:
              result = result | set(self.urigraph.graph['parents'][child].keys())
      else:
        post_nodes = self.fact()
        if pre_node_is_all:
          for parent in post_nodes:
            if parent in self.urigraph.graph['childs']:
              result = result | set(parent)              
        else:
          for parent in post_nodes:
            if parent in self.urigraph.graph['childs']:
              is_parent_of_all_childs_in_fact=1
              for child in pre_nodes:
                if not child in self.urigraph.graph['childs'][parent]:
                  is_parent_of_all_childs_in_fact=0
              if is_parent_of_all_childs_in_fact:
                result = result | set(parent)

    elif self.token == self.RESERVED_WORDS['add']:
      self.next_token()
      if self.token == "":
        print "Error token: expected factor"
      elif self.token == self.RESERVED_WORDS['all']:
        self.next_token()
        if pre_node_is_all:
          for parent in self.urigraph.graph['childs']:
            for child in self.urigraph.graph['parents']:
              self.urigraph.add([parent],[child])
        else:
          for parent in pre_nodes:
            for child in self.urigraph.graph['nodes']:
              self.urigraph.add([parent],[child])
      else:
        post_nodes = self.nodes()
        if pre_node_is_all:
          for child in post_nodes:
            for parent in self.urigraph.graph['childs']:
              self.urigraph.add([parent],[child])              
        else:
          for parent in pre_nodes:
            for child in post_nodes:
              self.urigraph.add([parent],[child])              

    elif self.token == self.RESERVED_WORDS['remove']:
      self.next_token()
      if self.token == "":
        print "Error token: expected factor"
      elif self.token == self.RESERVED_WORDS['all']:
        self.next_token()
        if pre_node_is_all:
          for parent in self.urigraph.graph['childs']:
            for child in self.urigraph.graph['parents']:
              self.urigraph.remove([parent],[child])
        else:
          for parent in fact:
            for child in self.urigraph.graph['nodes']:
              self.urigraph.remove([parent],[child])
      else:
        post_nodes = self.nodes()
        if pre_node_is_all:
          for child in fact2:
            for parent in self.urigraph.graph['childs']:
              self.urigraph.remove([parent],[child])              
        else:
          for parent in fact:
            for child in fact2:
              self.urigraph.remove([parent],[child])
    elif pre_node_is_all:
      result = set(self.urigraph.graph['nodes'])
    else:
      result=pre_nodes  
    return result

  def nodes(self):
    # TODO: Afegir algun caracter que siginfique algun element ? (o ningun) (o algun)
    result = set([])

    if self.token == "": 
      pass
    elif self.token == self.RESERVED_WORDS['not']:
      self.next_token()
      nodes = self.nodes()
      result = set(self.urigraph.graph['nodes']) - nodes

    elif self.token == self.RESERVED_WORDS['open']:
      self.next_token()
      result = self.expr()
      if self.token == self.RESERVED_WORDS['close']:
        self.token = self.next_token()
      else:
        print "Error token: expected:",self.RESERVED_WORDS['close'], "got:",self.token

    elif self.token == self.RESERVED_WORDS['create']:
      self.next_token()
      nodes = self.nodes()
      for uri in nodes:
        self.urigraph.create(uri)
        result = result | set([self.urigraph.graph['uris'][uri]])

    elif self.token == self.RESERVED_WORDS['delete']:
      self.next_token()
      nodes = self.nodes()
      for uri in nodes:
        if uri in self.urigraph.graph['uris']:
          result = result | set([self.urigraph.graph['uris'][uri]])
          self.urigraph.delete()

    elif self.token == self.RESERVED_WORDS['root']:
      self.next_token()
      if self.token == self.RESERVED_WORDS['all']:
        self.next_token()
        result = result | set(self.urigraph.graph['roots'].keys())
      else:
        nodes = self.nodes()
        for node in nodes:
          if node in self.urigraph.graph['roots']:
            result = result | set([node])

    elif self.token == self.RESERVED_WORDS['set_root']:
      self.next_token()
      nodes = self.nodes()
      for node in nodes:
        self.urigraph.set_root(node)

    elif self.token == self.RESERVED_WORDS['unset_root']:
      self.next_token()
      if self.token == self.RESERVED_WORDS['all']:
        self.next_token()
        self.urigraph.graph['roots'] = {}
      else:
        nodes = self.fact()
        for node in nodes:
          self.urigraph.unset_root(node)

    elif self.scheme_regex.match(self.token):
      scheme=self.token
      self.next_token()
      nodes = self.nodes()
      for node in nodes:
        if node in self.urigraph.graph['nodes']:
          if self.urigraph.graph['nodes'][node].find(scheme) == 0:
            result = result | set([node])

    elif self.token == self.RESERVED_WORDS['print']:
      self.next_token()
      self.urigraph.printgraph()

    elif self.token[0] == '"' or self.token[0] == "'":
      uri=self.token[1:-1] #remove quotes
      self.next_token()
      if uri in self.urigraph.graph['uris']:
        result=set([self.urigraph.graph['uris'][uri]])
      elif uri in self.urigraph.graph['names']:
        result=set(self.urigraph.graph['names'][uri].keys())
      else:
        result=set([uri])
    return result

if __name__ == "__main__":
  import os.path
  import sys
  graph = URIGraph("%s/.lfs/lfs.graph" % os.path.expanduser('~'))
  if len(sys.argv)==1:
    graph.printgraph()  
  if len(sys.argv)==2:
    print "::::nodes::::"
    count = 0
    for node in graph.query(sys.argv[1]):
      print node
      count += 1
    print "Total:",count
