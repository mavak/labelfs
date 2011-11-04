#!/usr/bin/python
# -*- coding: utf-8 -*-
import fuse
from fuse import Fuse   # No ve per defecte en Ubuntu!
import lfsengine
import stat
import os    

from os.path import realpath,isfile,isdir,basename,dirname,join,exists,normpath,expanduser
import errno
import sys
from threading import RLock

fuse.fuse_python_api = (0, 2)

# ¿si dos cançons estan en posicions diferents en dos cd's
# com salvem el fet de que per a ordenar-les estem acostumats a canviarles de nom?
# Fa falta tindre algo més en compte a l'hora de fer relacions que la posicio? el temps? grau d'afinitat?
# quan se crea un node la part "1 - " del nom fa que automàticament se cree la etiqueta "`1` + " - " + pathlist[-1]" i s'apega al node, a aquesta etiqueta se li apega pathlist[-1]. El node s'ha de crear sense el "1 - "

# eliminar lfs-store, *com a molt utilitzarlo per a guardar els shelves (com a collections o biblioteques...). Quan se cree un "fitxer" en el engine se guardarà la uri, i es la que usarem com a path.



EXECUTE_PREFIX = '$$'
EXECUTE_PREFIX_LEN = len(EXECUTE_PREFIX)
  
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
  
  """.format(prog = basename(sys.argv[0]))

class LabelFs(Fuse):
  def __init__(self, *args, **kw):
    self.lfsdb = "%s/.lfs.db" % expanduser('~')
    Fuse.__init__(self, version=kw['version'],usage=kw['usage'])
    self.flags = 0
    self.multithreaded = True
    self.parser.add_option(mountopt="lfsdb", metavar="PATH", default=self.lfsdb, help="use filesystem from under PATH [default:  default]")
    self.parse(values=self, errex=1)
    self.lfsdbdir = dirname(self.lfsdb)
    self.le = lfsengine.LabelEngine(self.lfsdb)
    
  def main(self, *a, **kw):
    self.file_class = self.LabelFsFile
    Fuse.main(self, *a, **kw)
    return 0
  
  def pathlist(self,path):
    return [node for node in path.split('/') if node != ""]
  
  def getattr (self, path):
    if path.find(EXECUTE_PREFIX)>-1:
      if path.find('+')>-1 or path.find('-')>-1:
        return -errno.ENOENT
      else:
        return os.lstat("%s" % (self.lfsdb))
    bn = basename(path)
    if bn != '':
      pl = self.pathlist(path)
      lenpl = len(pl)
      le_query = '"%s" & ^<#*' % bn
      pl.reverse()
      if self.le.exists_node(bn,lfsengine.TYPE_LABEL):
        if lenpl > 1:
          le_query = '#"%s"%s' % ('"& <[#"'.join(pl),']'*(lenpl-1))
        for node in self.le.query(le_query):
          return os.lstat(self.lfsdbdir)
      elif self.le.exists_node(bn,lfsengine.TYPE_FILE):
        if lenpl > 1:
          le_query = '~"%s" & <"%s"' % (bn,'" & <"'.join(pl[1:]))  
        for node in self.le.query(le_query):
          if 'uri' in node:
            return os.lstat(node['uri'])
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
        pl = self.pathlist(path)
        le_query = '~[<"%s"] | #<"%s"' % ('" & <"'.join(pl),pl[-1])
    for node in self.le.query(le_query):
      dirents.append(node['name'])
    for r in dirents:
      yield fuse.Direntry(r)
      
  def access(self, path, mode):
    uri = ""
    for node in self.le.query('"%s"' % basename(path)):
      if 'uri' in node:
        if not os.access(node['uri'], mode):
          return -errno.EACCES
  
  def open (self, path, flags):
    for node in self.le.query('"%s"' % basename(path)):
      if 'uri' in node:
        return self.LabelFsFile(node['uri'], flags)
      
  def readlink(self, path):
    for node in self.le.query('"%s"' % basename(path)):
      if 'uri' in node:
        return os.readlink(node['uri'])
  
  def mknod(self, path, mode, dev):
    bn = basename(path)
    dl = self.pathlist(dirname(path))
    uri = "%s/%s" % (self.lfsdbdir,bn)
    self.le.create_file(bn,uri)
    if len(dl)>0:
      le_query = '+["%s"],["%s"]' % ('" | "'.join(dl),bn)
      self.le.execute(le_query)
    os.mknod(uri, mode, dev)
    
  def create (self, path, fi_flags, mode):
    bn = basename(path)
    dl = self.pathlist(dirname(path))
    uri = "%s/%s" % (self.lfsdbdir,bn)
    self.le.create_file(bn,uri)
    if len(dl)>0:
      le_query = '+["%s"],["%s"]' % ('" | "'.join(dl),bn)
      self.le.execute(le_query)
    f = self.LabelFsFile(uri, fi_flags, mode)
    return f
  
  def utime(self, path, times):
    for node in self.le.query('"%s"' % basename(path)):
      if 'uri' in node:
        os.utime(node['uri'], times)

  def unlink(self, path):
    bn = basename(path)
    #for node in self.le.query('"%s"' % bn):
    #  if 'uri' in node:
    #    if exists(node['uri']): 
    #      os.unlink(node['uri'])
    self.le.delete_node(bn)
  
  def mkdir(self, path, mode):
    execute_prefix_position = path.find(EXECUTE_PREFIX)
    if execute_prefix_position>-1:
       self.le.execute(path[execute_prefix_position+EXECUTE_PREFIX_LEN:])
    else:
      bn = basename(path)
      dl = self.pathlist(dirname(path))
      self.le.create_label(bn)
      if len(dl)>0: 
        le_query = '+["%s"],["%s"]' % ('" | "'.join(dl[-1:]),bn)
        self.le.execute(le_query)
      le_query = '+["%s"],[~<"%s"]' % ('" | "'.join(dl),bn)
      self.le.execute(le_query)
      
  def rmdir(self, path):
    bn = basename(path)
    self.le.delete_node(bn)

  def symlink(self, target, link):
    bn = basename(link)
    dl = self.pathlist(dirname(link))
    if isfile(target):
      self.le.create_file(bn,target)
      if len(dl)>0:
        le_query = '+["%s"],["%s"]' % ('" | "'.join(dl),bn)
        self.le.execute(le_query)
    else:
      for i in range(len(dl)): 
        self.le.create_label(dl[i])
        le_query = '+["%s"],["%s"]' % (dl[i-1],dl[i])
        self.le.execute('+["%s"],["%s"]' % ('" | "'.join(dl[:i]),dl[i]))
      flag_can_link = 1
      for r,d,fs in os.walk(target):
        rel = r.replace(target,"")
        dl = self.pathlist(rel)
        for i in range(len(dl)):
          self.le.create_label(dl[i])
          if i > 0:
            le_query = '+["%s"],["%s"]' % (dl[i-1],dl[i])
            self.le.execute(le_query)
        for f in fs:
          self.le.create_file(f,"%s/%s" % (r,f))
          le_query = '+["%s"],["%s"]' % ('" | "'.join(dl),f)
          self.le.execute(le_query)

  def link(self, target, link):
    if isfile(link):
      bn = basename(link)
      dl = self.pathlist(dirname(link))
      self.le.create_file(bn,target)
      if len(dl)>0:
        le_query = '+["%s"],["%s"]' % ('" | "'.join(dl),bn)
        self.le.execute(le_query)
          
  def rename(self, old, new):
    oldbn = basename(old)
    newbn = basename(new)
    execute_prefix_position = newbn.find(EXECUTE_PREFIX)
    if execute_prefix_position>-1:
      self.le.execute(newbn[execute_prefix_position:])
      self.le.delete_node(oldbn)
      if exists("%s/%s" % (self.lfsdb,oldbn)): 
        os.rmdir("%s/%s" % (self.lfsdb,oldbn))
    else:
      olddn = dirname(old)
      newdn = dirname(new)
      olddl = self.pathlist(olddn)
      newdl = self.pathlist(newdn)
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
    for node in self.le.query('"%s"' % basename(path)):
      if 'uri' in node:
        os.chmod(node['uri'], mode)

  def chown(self, path, user, group):
    for node in self.le.query('"%s"' % basename(path)):
      if 'uri' in node:
        os.chown(node['uri'], user, group)

  def truncate(self, path, lenght):
    for node in self.le.query('"%s"' % basename(path)):  
      f = open(node['uri'], "a")
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
