import os,sys
cmd_folder = "%s/.." % os.path.dirname(os.path.abspath(__file__))
if cmd_folder not in sys.path:
  sys.path.insert(0, cmd_folder)
import lfsengine

class LfsController:
  def __init__(self,lfsdb_path):
    self.le = lfsengine.LfsEngine(lfsdb_path)
    self.le.printlfs()

  def query(self,query):
    for n in self.le.query(query):
      yield n

  def create_nodes_from_uris(self,uris,path):
    refresh_name=0
    for uri in uris:
      uri = uri.replace("file://","")
      bn = basename(uri)
      if isfile(uri):
        self.le.create_file(bn,uri)
        refresh_name=uri
        if len(path)>0:
          le_query = '+["%s"],["%s"]' % ('" | "'.join(path),bn)
          self.le.execute(le_query)
      else:
        for i in range(len(path)): 
          self.le.create_label(path[i])
          refresh_name=uri
          le_query = '+["%s"],["%s"]' % (path[i-1],path[i])
          self.le.execute('+["%s"],["%s"]' % ('" | "'.join(path[:i]),path[i]))
        for r,d,fs in os.walk(uri):
          rel = r.replace(uri,"")
          pl = pathlist(rel)
          for i in range(len(pl)):
            self.le.create_label(pl[i])
            refresh_name=pl[i]
            if i > 0:
              le_query = '+["%s"],["%s"]' % (pl[i-1],pl[i])
              self.le.execute(le_query)
          for f in fs:
            self.le.create_file(f,"%s/%s" % (r,f))
            refresh_name=f
            le_query = '+["%s"],["%s"]' % ('" | "'.join(pl),f)
            self.le.execute(le_query)
    refresh_name and _signals.emit('node-created',1)

  def create_label(self,name):
    self.le.create_label(name)

  def create_file(self,name,uri):
    self.le.create_file(name,uri)
