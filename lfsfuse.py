#!/usr/bin/python
# -*- coding: utf-8 -*-
import fuse # No ve per defecte en Ubuntu!
import URIGraph
import os,sys,stat,urlparse
import errno
from threading import RLock

fuse.fuse_python_api = (0, 2)

# ¿si dos cançons estan en posicions diferents en dos cd's
# com salvem el fet de que per a ordenar-les estem acostumats a canviarles de nom?
# Fa falta tindre algo més en compte a l'hora de fer relacions que la posicio? el temps? grau d'afinitat?
# quan se crea un node la part "1 - " del nom fa que automàticament se cree la etiqueta "`1` + " - " + path2labels[-1]" i s'apega al node, a aquesta etiqueta se li apega path2labels[-1]. El node s'ha de crear sense el "1 - "

#TODO: roots, rename, symlink, ...

QUERY_PATH = 'query'
QUERY_PATH_LEN = len(QUERY_PATH)


def pathlist(path):
  return [node for node in path.split('/') if node != ""]

def uri2path(uri):
  if uri.find("label://")==0:
    return uri[8:]
  else:
    return urlparse.urlparse(uri)[2]

def usage():
  return """
  LabelFS - fuse filesystem for organizing URIs in a Directed Graph
  Author: Gerard Falco (gerardfalco@gmail.com)
  
  USAGE (command line):
  
    {prog} [-f] [-d] -o graphdb=<graphdb> <mp>
 
  USAGE (fstab):
  
    {prog}# <mp> fuse allow_other[,<options>] 0 0
  
  PARAMETERS:
  
    graph: URIGraph database file 
    mp: mount point
    options: GraphFS-specific options
    -f: no-fork mode
    -d: debug mode
  
  DESCRIPTION
  
  GraphFS implements a filesystem for organizing URIS in a directed graph.

  See UserGuide in: code.google.com/p/labelfs
  
  """.format(prog = os.path.basename(sys.argv[0]))

class LabelFs(fuse.Fuse):
  def __init__(self, *args, **kw):
    self.lfsdir = "%s/.lfs/" % os.path.expanduser('~')
    fuse.Fuse.__init__(self, version=kw['version'],usage=kw['usage'])
    self.flags = 0
    self.multithreaded = True
    self.parser.add_option(mountopt="lfsdir", metavar="PATH", default=self.lfsdir, help="use filesystem from under PATH [default:  default]")
    self.parse(values=self, errex=1)

    self.urigraph = URIGraph.URIGraph("%s/lfs.graph" % self.lfsdir)
    
  def main(self, *a, **kw):
    self.file_class = self.LabelFsFile
    fuse.Fuse.main(self, *a, **kw)
    return 0

  ##
  def query_uri(self,path):
    basename = os.path.basename(path)
    dirs = pathlist(os.path.dirname(path))
    query = '"%s"' % basename
    if len(dirs) > 0:
      query = 'label:"%s" > label:"%s"' % (dirs[-1],basename)  
      for uri in self.urigraph.query(query):
        return uri
      query = 'label:["%s"] > file:"%s"' % ('" | "'.join(dirs),basename)
    for uri in self.urigraph.query(query):
      return uri

  def realpath(self,path):
    if path == '/':
      return os.path.expanduser('~')
    uri=self.query_uri(path)
    if uri:
      uri_path=uri2path(uri)
      if os.path.basename(uri_path) == os.path.basename(path):
        if uri.find('label://') == 0:
          return self.lfsdir
        else:
          return uri_path
    return "-1"
  ##

  def getattr(self, path):
    QP_pos = path.find(QUERY_PATH)
    if QP_pos>-1 and QP_pos<3:
      return os.lstat(self.lfsdir)
    realpath=self.realpath(path)
    return os.lstat(realpath)

  def statfs(self):
    return os.statvfs(os.path.expanduser('~'))
  
  def readdir (self, path, offset):
    dirents = [ '.', '..' ]

    QP_pos = path.find(QUERY_PATH)
    if QP_pos>-1 and QP_pos<3:
      query=path[QUERY_PATH_LEN+QP_pos+1:]
      if query == "":
        query='R | R>*'
      else:
        while query.find('/ /') > -1:
          query=query.replace('/ /','//')
      for uri in self.urigraph.query(query):
        dirents.append(uri)

    elif path != '/':
      pl = pathlist(path)
      for child in self.urigraph.query('label:[label:"%s" > *]' % pl[-1]):
        dirents.append(os.path.basename(uri2path(child)))
      for child in self.urigraph.query('file:[label:"%s">*]' % ('" > label:"'.join(pl))):
        dirents.append(os.path.basename(uri2path(child)))

    else:
      childs=set([])
      for root in self.urigraph.get_roots():
        dirents.append(os.path.basename(uri2path(root)))
    
    for r in dirents:
      yield fuse.Direntry(r)
      
  def access(self, path, mode):
    os.access(self.realpath(path), mode)
  
  def open(self, path, flags):
    realpath=self.realpath(path)
    #if realpath == "-1":
    #  print "open ",path
    #  file_path = os.path.abspath(path[1:]) #(os.path.expanduser('~'),os.path.basename(path))
    #  print "file_path",file_path
    #  file_uri = "file://%s" % file_path
    #  self.urigraph.create(file_uri)
    #  self.urigraph.add(pathlist(os.path.dirname(path)), [file_uri])
    #  return -errno.ENOSYS
    #else:
    return self.LabelFsFile(realpath, flags)
      
  def readlink(self, path):
    return os.readlink(self.realpath(path))
  
  def mknod(self, path, mode, dev):
    nod_path = "%s/%s" % (os.path.expanduser('~'),os.path.basename(path))
    #os.mknod(nod_path, mode, dev)
    return -errno.ENOENT    

  def create(self, path, fi_flags, mode):
    print "create ",path, fi_flags, mode
    file_path = os.path.abspath(path[1:]) #(os.path.expanduser('~'),os.path.basename(path))
    print "file_path",file_path
    file_uri = "file://%s" % file_path
    self.urigraph.create(file_uri)
    self.urigraph.add(pathlist(os.path.dirname(path)), [file_uri])
    #return self.LabelFsFile("/dev/null", fi_flags)
  
  def utime(self, path, times):
    os.utime(self.realpath(path), times)

  def unlink(self, path):
    self.urigraph.delete(self.query_uri(path))
  
  def mkdir(self, path, mode):
    uri = 'label://%s' % os.path.basename(path)
    self.urigraph.create(uri)    

    dirname=pathlist(os.path.dirname(path))
    if len(dirname)>0:
      self.urigraph.add(dirname,[uri])
    else:
      self.urigraph.set_root(uri)
      
  def rmdir(self, path):
    self.urigraph.delete(self.query_uri(path))

  def symlink(self, target, link):
    target=os.path.abspath(target)
    link_dirs=pathlist(os.path.dirname(link))
    len_link_dirs=len(link_dirs)
    if os.path.isfile(target):
      uri = 'file://%s' % target
      self.urigraph.create(uri)
      if len(link_dirs) > 0:
        self.urigraph.add(link_dirs,[uri])
      else:
        self.urigraph.set_root(uri)
    else:
      uri="label://%s" % os.path.basename(link)
      self.urigraph.create(uri)
      if len(link_dirs) > 0:
        self.urigraph.add(link_dirs[-1:],[uri])
      else:
        self.urigraph.set_root(uri)
      target_dirname=os.path.dirname(target)
      for root,dirnames,files in os.walk(target):
        target_dirs = pathlist(root.replace(target_dirname,""))
        len_target_dirs = len(target_dirs)
        for dirname in dirnames:
          label_uri="label://%s" % dirname
          self.urigraph.create(label_uri)  
          if len_target_dirs > 0:
            self.urigraph.add(target_dirs[-1:], [label_uri])
        for file in files:
          file_uri="file://%s/%s" % (root,file)
          self.urigraph.create(file_uri)
          if len_target_dirs > 0:
            self.urigraph.add(target_dirs,[file_uri])
          if len_link_dirs > 0:
            self.urigraph.add(link_dirs,[file_uri])

  def link(self, target, link):
    if os.path.isfile(target):
      uri = 'file://%s' % target
      self.urigraph.create(uri)
      self.urigraph.add(pathlist(os.path.dirname(link)),[uri])

  def rename(self,old,new):
    #TODO: what to do?
    new_basename = os.path.basename(new)
    old_dirname = os.path.dirname(old)
    new_dirname = os.path.dirname(new)
    old_dirname_list = pathlist(old_dirname)
    new_dirname_list = pathlist(new_dirname)
    is_file_old_basename = self.urigraph.exists_file(old_basename)
    is_file_new_basename = self.urigraph.exists_file(new_basename)
    is_label_new_basename = self.urigraph.exists_label(new_basename)
    if old_basename != new_basename:
      if is_file_new_basename:
        return -errno.ENOENT
      elif is_label_new_basename:
        self.add([],[])
        le_query = '["%s"]+>["%s"] & ["%s">*]+>["%s"] & +["%s"],[~<"%s"]' % ('" | "'.join(new_dirname_list[-1:]), new_basename, old_basename, new_basename, new_basename, old_basename)
        self.urigraph.execute(le_query)
        self.urigraph.delete_node(old_basename)
      else:
        self.urigraph.rename_node(old_basename,new_basename)
    if old_dirname_list != new_dirname_list:
      if new_dirname == '/':
        le_query = '["%s"]+>["%s"]' % ('" | "'.join(old_dirname_list[-1:]), new_basename)
        self.urigraph.execute(le_query)
      else:
        if is_file_old_basename:
          le_query = '["%s"]+>["%s"]' % ('" | "'.join(new_dirname_list),new_basename)
          self.urigraph.execute(le_query)
        else:
          le_query = '["%s"]+>["%s"] & ["%s"]+>["%s">file:*]' % ('" | "'.join(new_dirname_list[-1:]),new_basename,'" | "'.join(new_dirname_list),new_basename)
          self.urigraph.execute(le_query)


    old_uri=self.urigraph.get_uri(old)
    self.urigraph.rename(old,new)
    new_uri=self.urigraph.get_uri(new)
    if new_uri != old_uri:
      None
      #if self.urigraphis file 
      #os.rename(uri2path(old_uri),uri2path(new_uri)

  def chmod(self, path, mode):
    os.chmod(self.realpath(path), mode)

  def chown(self, path, user, group):
    os.chown(self.realpath(path), user, group)

  def truncate(self, path, lenght):
    f = open(self.realpath(path), "a")
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

  lfsdir="%s/.lfs/" % os.path.expanduser('~')
  if not os.path.isdir(lfsdir):
    os.system("mkdir %s" % lfsdir)

  server = LabelFs(version="%prog " + fuse.__version__,usage=usage(), dash_s_do='setsingle',lfsdir=lfsdir)
  return server.main()

if __name__ == '__main__':
  rval = main(sys.argv)
  if rval != 0:
    sys.exit(rval)
