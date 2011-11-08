import os,sys
cmd_folder = "%s/.." % os.path.dirname(os.path.abspath(__file__))
if cmd_folder not in sys.path:
  sys.path.insert(0, cmd_folder)
import lfsengine

def pathlist(path):
  return [node for node in path.split('/') if node != ""]

class LfsController:
  def __init__(self,lfsdb_path):
    self.le = lfsengine.LfsEngine(lfsdb_path)
    #self.le.printlfs()

  def query(self,query):
    for n in self.le.query(query):
      yield n

  def create_nodes_from_uris_in_path(self,uris,path):
    print "yeeep"
    for uri in uris:
      print "guay"
      uri = uri.replace("file://","")
      bn = os.path.basename(uri)
      if os.path.isfile(uri):
        self.le.create_file(bn,uri)
        if len(path)>0:
          le_query = '+["%s"],["%s"]' % ('" | "'.join(path),bn)
          self.le.execute(le_query)
      else:
        print "*uri* ",uri," *path* ",path
        for i in range(len(path)): 
          self.le.create_label(path[i])
          print "create",path[i]
          le_query = '+["%s"],["%s"]' % (path[i-1],path[i])
          self.le.execute('+["%s"],["%s"]' % ('" | "'.join(path[:i]),path[i]))
        for r,d,fs in os.walk(uri):
          rel = r.replace(uri,"")
          pl = pathlist(rel)
          print "pl",pl
          for i in range(len(pl)):
            self.le.create_label(pl[i])
            if i > 0:
              le_query = '+["%s"],["%s"]' % (pl[i-1],pl[i])
              self.le.execute(le_query)
          for f in fs:
            self.le.create_file(f,"%s/%s" % (r,f))
            le_query = '+["%s"],["%s"]' % ('" | "'.join(pl),f)
            self.le.execute(le_query)

  def create_label(self,name):
    self.le.create_label(name)

  def create_file(self,name,uri):
    self.le.create_file(name,uri)

  def delete_node(self,name):
    self.le.delete_node(name)
