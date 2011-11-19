#!/usr/bin/python
# -*- coding: utf-8 -*-
import fuse # No ve per defecte en Ubuntu!
import lfsengine
import os,sys,stat,urlparse
import errno
from threading import RLock

fuse.fuse_python_api = (0, 2)

# ¿si dos cançons estan en posicions diferents en dos cd's
# com salvem el fet de que per a ordenar-les estem acostumats a canviarles de nom?
# Fa falta tindre algo més en compte a l'hora de fer relacions que la posicio? el temps? grau d'afinitat?
# quan se crea un node la part "1 - " del nom fa que automàticament se cree la etiqueta "`1` + " - " + pathlist[-1]" i s'apega al node, a aquesta etiqueta se li apega pathlist[-1]. El node s'ha de crear sense el "1 - "

# eliminar lfs-store, *com a molt utilitzarlo per a guardar els shelves (com a collections o biblioteques...). Quan se cree un "fitxer" en el engine se guardarà la uri, i es la que usarem com a path.



EXECUTE_PREFIX = '$$'
EXECUTE_PREFIX_LEN = len(EXECUTE_PREFIX)

def pathlist(path):
  return [node for node in path.split('/') if node != ""]


def usage():
  return """
  LabelFS - fuse filesystem for organizing files in a Directed Graph of labels
  Author: Gerard Falco (gerardfalco@gmail.com)
  
  USAGE (command line):
  
    {prog} [-f] [-d] -o lfsdb=<lfsdb> <mp>
  
  USAGE (fstab):
  
    {prog}# <mp> fuse allow_other[,<options>] 0 0
  
  PARAMETERS:
  
    lfs-db: lfs database file 
    mp: mount point
    options: labelfs-specific options
    -f: no-fork mode
    -d: debug mode
  
  DESCRIPTION
  
  LabelFS implements a filesystem for organizing files in a directed graph of labels.

  See UserGuide in: code.google.com/p/labelfs
  
  """.format(prog = os.path.basename(sys.argv[0]))

class LabelFs(fuse.Fuse):
  def __init__(self, *args, **kw):
    self.lfsdb = "%s/.lfs.db" % os.path.expanduser('~')
    fuse.Fuse.__init__(self, version=kw['version'],usage=kw['usage'])
    self.flags = 0
    self.multithreaded = True
    self.parser.add_option(mountopt="lfsdb", metavar="PATH", default=self.lfsdb, help="use filesystem from under PATH [default:  default]")
    self.parse(values=self, errex=1)
    self.lfsdbdir = os.path.dirname(self.lfsdb)
    self.le = lfsengine.LfsEngine(self.lfsdb)
    
  def main(self, *a, **kw):
    self.file_class = self.LabelFsFile
    fuse.Fuse.main(self, *a, **kw)
    return 0

  def get_uris(self,path):
    if path == "/":
      yield "file://%s" % self.lfsdbdir
    else:
      pl = pathlist(path)
      lenpl = len(pl)
      le_query = '*'
      if lenpl > 1:
        le_query_labels = '#* & <#"%s"%s' % ('"& <[#"'.join(pl), ']'*(len(pl)-1))
        le_query_files = '~* & <"%s"' % ('" & <"'.join(pl[1:]))
        le_query = "%s | %s" % (le_query_labels, le_query_files)
      for node in self.le.query(le_query):
        path_of_node=urlparse.urlparse(node['uri'])[2]        
        if os.path.basename(path_of_node) == os.path.basename(path):
          yield node['uri']


  def get_uri(self,path):
    for uri in self.get_uris(path):
      return uri
    return ""

  def getattr (self, path):
    if path.find(EXECUTE_PREFIX)>-1:
      if path.find('+')>-1 or path.find('-')>-1:
        return -errno.ENOENT
      else:
        return os.lstat("%s" % (self.lfsdb))
    if path != '/':
      uri = self.get_uri(path)
      if uri != "":
        pl = pathlist(path)
        lenpl = len(pl)
        le_query = '"%s" & ^<#*' % uri
        pl.reverse()
        if self.le.exists_node(uri,lfsengine.TYPE_LABEL):
          return os.lstat(self.lfsdbdir)
        elif self.le.exists_node(uri,lfsengine.TYPE_FILE):
          path_of_file=urlparse.urlparse(uri)[2]
          return os.lstat(path_of_file)
      return -errno.ENOENT
    return os.lstat(self.lfsdbdir)

  def statfs(self):
    return os.statvfs(self.lfsdb)
  
  def readdir (self, path, offset):
    dirents = [ '.', '..' ]
    exeprepos = path.find(EXECUTE_PREFIX)
    le_query=""
    if exeprepos>-1:
      if not path.find('+')>-1 and not path.find('-')>-1:
       le_query = path[exeprepos+EXECUTE_PREFIX_LEN:]
    else:
      le_query = '#^<#* | ~^<#*'
      if path != '/':
        pl = pathlist(path)
        le_query = '~[<"%s"] | #<"%s"' % ('" & <"'.join(pl),pl[-1])
    for node in self.le.query(le_query):
      path_of_file=urlparse.urlparse(node['uri'])[2]
      name=pathlist(path_of_file)[-1]
      dirents.append(name)
    for r in dirents:
      yield fuse.Direntry(r)
      
  def access(self, path, mode):
    return os.access(urlparse.urlparse(self.get_uri(path))[2], mode)
  
  def open(self, path, flags):
    return self.LabelFsFile(urlparse.urlparse(self.get_uri(path))[2], flags)
      
  def readlink(self, path):
    return os.readlink(urlparse.urlparse(self.get_uri(path))[2])
  
  def mknod(self, path, mode, dev):
    pl = pathlist(os.path.dirname(path))
    nod_path = "%s/%s" % (self.lfsdbdir,os.path.basename(path))
    uri = "file://%s" % nod_path
    self.le.create_file(uri)
    if len(pl)>0:
      le_query = '+["%s"],["%s"]' % ('" | "'.join(pl),uri)
      self.le.execute(le_query)
    os.mknod(nod_path, mode, dev)
    
  def create(self, path, fi_flags, mode):
    pl = pathlist(os.path.dirname(path))
    file_path = "%s/%s" % (self.lfsdbdir,os.path.basename(path))
    uri = "file://%s" % file_path
    self.le.create_file(uri)
    if len(pl)>0:
      le_query = '+["%s"],["%s"]' % ('" | "'.join(pl),uri)
      self.le.execute(le_query)
    f = self.LabelFsFile(file_path, fi_flags, mode)
    return f
  
  def utime(self, path, times):
    os.utime(urlparse.urlparse(self.get_uri(path))[2], times)

  def unlink(self, path):
    bn = os.path.basename(path)
    #for node in self.le.query('"%s"' % bn):
    #  if 'uri' in node:
    #    if os.path.exists(urlparse.urlparse(self.get_uri(path))[2]): 
    #      os.unlink(urlparse.urlparse(self.get_uri(path))[2])
    self.le.delete_node(bn)
  
  def mkdir(self, path, mode):
    execute_prefix_position = path.find(EXECUTE_PREFIX)
    if execute_prefix_position>-1:
       self.le.execute(path[execute_prefix_position+EXECUTE_PREFIX_LEN:])
    else:
      uri = os.path.basename(path)
      pl = pathlist(os.path.dirname(path))
      self.le.create_label(uri)
      if len(pl)>0: 
        le_query = '+["%s"],["%s"]' % ('" | "'.join(pl[-1:]),uri)
        self.le.execute(le_query)
      le_query = '+["%s"],[~<"%s"]' % ('" | "'.join(pl),uri)
      self.le.execute(le_query)
      
  def rmdir(self, path):
    self.le.delete_node(self.get_uri(path))

  def symlink(self, target, link):
    link_basename = os.path.basename(link)
    link_path_list = pathlist(os.path.dirname(link))
    if os.path.isfile(target):
      target_uri="file://%s" % target
      self.le.create_file(target_uri)
      if len(link_path_list)>0:
        le_query = '+["%s"],["%s"]' % ('" | "'.join(link_path_list),target_uri)
        self.le.execute(le_query)
    else:
      for i in range(len(link_path_list)): 
        self.le.create_label(link_path_list[i])
        le_query = '+["%s"],["%s"]' % (link_path_list[i-1],link_path_list[i])
        self.le.execute('+["%s"],["%s"]' % ('" | "'.join(link_path_list[:i]),link_path_list[i]))
      for root,directory,files in os.walk(target):
        target_relative_path_list = pathlist(root.replace(target,""))
        for i in range(len(target_relative_path_list)):
          self.le.create_label(target_relative_path_list[i])
          if i > 0:
            le_query = '+["%s"],["%s"]' % (target_relative_path_list[i-1],target_relative_path_list[i])
            self.le.execute(le_query)
        for file in files:
          file_uri="file://%s/%s" % (root,file)
          self.le.create_file(file_uri)
          le_query = '+["%s"],["%s"]' % ('" | "'.join(relative_path_list),file_uri)
          self.le.execute(le_query)

  def link(self, target, link):
    if os.path.isfile(link):
      uri = "file://%s" % target
      self.le.create_file("file://%s" % target)      
      pl = pathlist(os.path.dirname(link))
      if len(pl)>0:
        le_query = '+["%s"],["%s"]' % ('" | "'.join(dl),uri)
        self.le.execute(le_query)
          
  def rename(self, old, new):
    # TODO: Actualitzar a URIs
    oldbn = os.path.basename(old)
    newbn = os.path.basename(new)
    execute_prefix_position = newbn.find(EXECUTE_PREFIX)
    if execute_prefix_position>-1:
      self.le.execute(newbn[execute_prefix_position:])
      self.le.delete_node(oldbn)
      if os.path.exists("%s/%s" % (self.lfsdb,oldbn)): 
        os.rmdir("%s/%s" % (self.lfsdb,oldbn))
    else:
      olddn = os.path.dirname(old)
      newdn = os.path.dirname(new)
      olddl = pathlist(olddn)
      newdl = pathlist(newdn)
      isfileoldbn = self.le.exists_node(oldbn,lfsengine.TYPE_FILE)
      isfilenewbn = self.le.exists_node(newbn,lfsengine.TYPE_FILE)
      islabelnewbn = self.le.exists_node(newbn,lfsengine.TYPE_LABEL)
      if oldbn != newbn:
        if isfilenewbn:
          return -errno.ENOENT
        elif islabelnewbn:
          le_query = '+["%s"],["%s"] & +[>"%s"],["%s"] & +["%s"],[~<"%s"]' % ('" | "'.join(newdl[-1:]),newbn,oldbn,newbn,newbn,oldbn)
          self.le.execute(le_query)
          self.le.delete_node(oldbn)
        else:
          self.le.rename_node(oldbn,newbn)
          # !!Actualitzar les URL
          # os.rename("%s/%s" % (self.lfsdb,oldbn), "%s/%s" % (self.lfsdb,newbn))
      if olddl != newdl:
        if newdn == '/':
          le_query = '-["%s"],["%s"]' % ('" | "'.join(olddl[-1:]),newbn)
          self.le.execute(le_query)
        else:
          if isfileoldbn:
            le_query = '+["%s"],["%s"]' % ('" | "'.join(newdl),newbn)
            self.le.execute(le_query)
          else:
            le_query = '+["%s"],["%s"] & +["%s"],[~<"%s"]' % ('" | "'.join(newdl[-1:]),newbn,'" | "'.join(newdl),newbn)
            self.le.execute(le_query)

  def chmod(self, path, mode):
    os.chmod(urlparse.urlparse(self.get_uri(path))[2], mode)

  def chown(self, path, user, group):
    os.chown(urlparse.urlparse(self.get_uri(path))[2], user, group)

  def truncate(self, path, lenght):
    f = open(urlparse.urlparse(self.get_uri(path))[2], "a")
    f.truncate(lenght)
    f.close()
  
  def fsinit (self, *args):
    self.asgid = int(self.asgid)
    self.asuid = int(self.asuid)
    if self.asgid:
      os.setgid(self.asgid)
    if self.asuid:
      os.setuid(self.asuid)
    return 0
  
  def fsdestroy (self, *args):
    return -errno.ENOSYS
  
  class LabelFsFile(object):
    def __init__(self, path, flags, *mode):
      self.fd = os.open(path, flags)
      self.direct_io = 0
      self.keep_cache = 0
      self.lock = RLock()
      
    def read(self, length, offset):
      self.lock.acquire()
      try:
        os.lseek(self.fd, offset, os.SEEK_SET)
        buf = os.read(self.fd, length)
        return buf
      finally:
        self.lock.release()

    def write(self, buf, offset):
      self.lock.acquire()
      try:
        os.lseek(self.fd, offset, os.SEEK_SET)
        bytes = os.write(self.fd, buf)
        return bytes
      finally:
        self.lock.release()
    
    def release(self, flags):
      self.lock.acquire()
      try:
        os.close(self.fd)
      finally:
        self.lock.release()

    def fsync(self, isfsyncfile):
      self.lock.acquire()
      try:
        if isfsyncfile and hasattr(os, 'fdatasync'):
          os.fdatasync(self.fd)
        else:
          os.fsync(self.fd)
      finally:
        self.lock.release()

    def flush(self):
      self.lock.acquire()
      try:
        os.close(os.dup(self.fd))
      finally:
        self.lock.release()

    def fgetattr(self):
      self.lock.acquire()
      try:
        return os.fstat(self.fd)
      finally:
        self.lock.release()

    def ftruncate(self, len):
      self.lock.acquire()
      try:
        os.ftruncate(self.fd, len)
      finally:
        self.lock.release()

def main(args):
  if len(args) == 1:
    print usage()
    return -1
  server = LabelFs(version="%prog " + fuse.__version__,usage=usage(), dash_s_do='setsingle')
  return server.main()

if __name__ == '__main__':
  rval = main(sys.argv)
  if rval != 0:
    sys.exit(rval)
