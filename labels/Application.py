from gi.repository import Gtk, Gdk, Gio
import sys, os, urllib, urlparse
import xml.sax.saxutils

import Window


def pathlist(path):
  return [node for node in path.split('/') if node != ""]

def uri2path(uri):
  if uri.find("label://")==0:
    return uri[8:]
  else:
    return urlparse.urlparse(uri)[2]

def trick_query(query):
  query=query.replace('file://','file:/ / ')
  query=query.replace('label://','label:/ /')
  query=query.replace("'","%27")
  return query

def lfs_query(query):
  query="%s/Labels/query/%s" % (os.path.expanduser('~'),trick_query(query))
  try:
    for uri in os.listdir(query):
      yield uri.replace("%27","'")
  except:
    None

def lfs_execute(query):
  query="%s/Labels/'$%s'" % (os.path.expanduser('~'),trick_query(query))
  try:
    #print "QUERY",query
    os.system("ls %s > /dev/null 2> /dev/null" % query)
    return 1
  except:
    return 0


class Application():
  def __init__(self):
    self.win = Window.Window()

    provider = Gtk.CssProvider();
    provider.load_from_path("%s/gtk-style.css" % os.path.abspath(os.path.dirname(sys.argv[0])));    
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, 600);

    self.new_label_entry = self.win.tree_view_frame.new_node_bar.new_label_entry
    self.new_file_entry = self.win.tree_view_frame.new_node_bar.new_file_entry
    self.tree_view = self.win.tree_view_frame.tree_view
    self.location_bar = self.win.query_view_frame.location_bar
    self.icon_view = self.win.query_view_frame.icon_view

    self.new_label_entry.connect('activate',self.on_new_label_entry_activate)
    self.new_file_entry.connect('activate',self.on_new_file_entry_activate)

    self.tree_view.selection.connect("changed",self.on_tree_view_selection_change)
    self.tree_view.connect("drag-begin", self.on_tree_view_drag_data_get_cb)
    self.tree_view.connect('row-expanded', self.on_tree_view_row_expanded)
    self.tree_view.connect('key_release_event',self.on_tree_view_key_release)

    self.icon_view.connect("drag-data-received", self.on_icon_view_drag_data_received)
    self.icon_view.connect("key_release_event", self.on_icon_view_key_release)
    self.icon_view.connect('item-activated',self.on_icon_view_item_activated)

    self.app_start()

  def app_start(self):

    self.current_path = []

    self.refresh_tree_view()
    self.refresh_location_bar()
    self.refresh_icon_view()

  # Operations on model of view
  def refresh_tree_view(self,tree_iter=None):
    def refresh_tree_path(tree,tree_path,data):
      tree_iter=self.tree_view.tree_store.get_iter(tree_path)
      child = self.tree_view.tree_store.iter_children(tree_iter)
      # Remove current childs of iter. Caution! not remove all items, remove last after insertion
      while self.tree_view.tree_store.iter_n_children(tree_iter) > 1:
        child_name = self.tree_view.tree_store.get_value(child,0)
        self.tree_view.tree_store.remove(child)
        child=self.tree_view.tree_store.iter_children(tree_iter)
      # Add queried child labels
      query=''
      name = self.tree_view.tree_store.get_value(tree_iter,0)
      if name == 'roots':
        query = 'label:R*'
      else:
        query = 'label:"%s">*' % name
      for uri in lfs_query(query):
        if uri.find('label:') == 0:
          uri=xml.sax.saxutils.escape(uri)
          name=os.path.basename(uri2path(uri))
          parent2=self.tree_view.tree_store.append(tree_iter, (name,))
          parent3=self.tree_view.tree_store.append(parent2, ('.',))
      # Remove last iter
      if child != None:
        self.tree_view.tree_store.remove(child)
    if tree_iter != None:
      refresh_tree_path(self.tree_view,self.tree_view.tree_store.get_path(tree_iter),"")
    else:
      if not self.tree_view.tree_store.get_iter_first():
        parent=self.tree_view.tree_store.append(None, ('roots',))
        self.tree_view.tree_store.append(parent, ('.',))
        path=Gtk.TreePath("0")
        self.tree_view.expand_row(path,False)
      self.tree_view.map_expanded_rows(refresh_tree_path,None)

  def refresh_location_bar(self,path=None):
    if path == None:
      path = self.current_path
    if len(path) == 0:
      for child in self.location_bar.toolbar.get_children():
        self.location_bar.toolbar.remove(child)
      ttb = Gtk.ToggleToolButton(label='roots')
      ttb.get_style_context().add_class("location-button")
      ttb.set_active(1)
      self.location_bar.toolbar.add(ttb)
    else:
      for child in self.location_bar.toolbar.get_children():
        self.location_bar.toolbar.remove(child)
      for node in path:
        ttb = Gtk.ToggleToolButton(label=node)
        ttb.get_style_context().add_class("location-button")
        ttb.set_active(1)
        self.location_bar.toolbar.add(ttb)
    self.location_bar.show_all()

  def refresh_icon_view(self):
    self.icon_view.list_store.clear()
    query = 'file:R*'
    if len(self.current_path)>0:
      query = 'file:[label:"%s">*]' % ('" > label:"'.join(self.current_path))
      #query = '"file://%s">*' % ('" > "label://'.join(self.current_path))
    for uri in lfs_query(query):
      if uri.find('file:') == 0:
        pixbuf = self.icon_view.render_icon(Gtk.STOCK_FILE, Gtk.IconSize.DIALOG, None)
        icon=Gio.content_type_get_icon(Gio.content_type_guess(uri,None)[0])
        icon_info=Gtk.IconTheme.get_default().lookup_by_gicon(icon,48,Gtk.IconLookupFlags.FORCE_SIZE|Gtk.IconLookupFlags.GENERIC_FALLBACK)
        if icon_info:
          pixbuf = icon_info.load_icon()
        uri=xml.sax.saxutils.escape(uri)
        name=os.path.basename(uri2path(uri))
      
        self.icon_view.list_store.append([pixbuf,name,uri,0])


  # event operations on lfs-model and view-model
  def on_tree_view_selection_change(self,tree_selection):
    (model, pathlist) = tree_selection.get_selected_rows()
    self.current_path=[]
    tree_iter=None
    for path in pathlist :
      tree_iter = model.get_iter(path)
      name = model.get_value(tree_iter,0)
      if name != 'roots':
        self.current_path.insert(0,name)
      parent = model.iter_parent(tree_iter)
      while parent != None:
        parent_name = model.get_value(parent,0)
        if parent_name != 'roots':
          self.current_path.insert(0,parent_name)
        parent = model.iter_parent(parent)

    self.refresh_tree_view(tree_iter)
    self.refresh_location_bar(self.current_path)
    self.refresh_icon_view()

  def on_tree_view_drag_data_get_cb(self, context, selection):
      treeselection = self.tree_view.get_selection()
      (model, iter) = treeselection.get_selected()
      text = self.tree_view.tree_store.get_value(iter, 0)
      
  def on_tree_view_row_expanded(self,tree_view,tree_iter,path):
    self.refresh_tree_view(tree_iter)          

  def on_tree_view_key_release(self,widget,event):
    if event.keyval == 65535:
      tree_selection = self.tree_view.get_selection()
      (model, pathlist) = tree_selection.get_selected_rows()
      for path in pathlist :
        tree_iter = model.get_iter(path)
        selected_name = model.get_value(tree_iter,0)
        lfs_execute('X"label://%s"' % selected_name)
        parent = model.iter_parent(tree_iter)
        self.refresh_tree_view(parent)
        while parent != None:
          parent_name = model.get_value(parent,0)
          if parent_name != 'root':
            lfs_execute('"label://%s"->"label://%s"' % parent_name,selected_name)
            self.refresh_tree_view(parent)
          parent = model.iter_parent(parent)
    
  def on_new_label_entry_activate(self,entry):
    text = self.new_label_entry.get_text()
    if text != "":
      lfs_execute('@"label://%s"' % text)
      for label in self.current_path:
        lfs_execute('"label://%s"+>"label://%s"',label,text)
    self.refresh_tree_view()

  def on_new_file_entry_activate(self,entry):
    text = self.new_file_entry.get_text()
    if text != "":
      path="%s/%s" % (os.path.expanduser("~"),text)
      os.system("touch %s" % path)
      uri="file://%s" % path
      lfs_execute('@"%s"' % uri)
      for label in self.current_path:
        lfs_execute('"label://%s"+>"%s"',label,uri)
    self.refresh_icon_view()

  def on_icon_view_drag_data_received(self, widget, drag_context, x, y, data, info, time):
    for uri in data.get_uris():
      uri_path = urllib.url2pathname(uri2path(uri))
      basename = os.path.basename(uri_path)
      if os.path.isfile(uri_path):
        lfs_execute('@"%s"' % uri)
        if len(self.current_path)>0:
          lfs_execute('["%s"]+>["%s"]' % ('" | "'.join(self.current_path),uri))
        else:
          lfs_execute('R+"%s"' % uri)
      elif os.path.isdir(uri_path):
        #for i in range(len(self.current_path)):
        #  lfs_execute('@"label://%s"' % self.current_path[i])
        #  if i > 0:
        #    lfs_execute('+["label://%s"],["label://%s"]' % ('" | "label://'.join(self.current_path[:i]),self.current_path[i]))
        #  else:
        #    lfs_execute('R+"label://%s"' % self.current_path[i])
        uri_path_list=pathlist(uri_path)
        last_dir_in_uri=uri_path_list[-1]
        lfs_execute('@"label://%s"' % last_dir_in_uri)
        if len(self.current_path)>0:
          lfs_execute('["label://%s"]+>["label://%s"]' % ('" | "label://'.join(self.current_path),last_dir_in_uri))
        else:
          lfs_execute('R+"label://%s"' % last_dir_in_uri)
        for root,directory,files in os.walk(uri_path):
          relative_path = root.replace(uri_path,"")
          relative_path_list = pathlist(relative_path)
          relative_path_list.insert(0,last_dir_in_uri)
          for i in range(len(relative_path_list)):
            lfs_execute('@"label://%s"' % relative_path_list[i])
            if i > 0:
              lfs_execute('["label://%s"]+>["label://%s"]' % (relative_path_list[i-1],relative_path_list[i]))
            else:
              lfs_execute('R+"label://%s"' % relative_path_list[i])
          len_rpl=len(relative_path_list)
          for file in files:
            uri="file://%s/%s" % (root,file)
            lfs_execute('@"%s"' % uri)
            if len_rpl > 0:
              lfs_execute('["label://%s"]+>["%s"]' % ('" | "label://'.join(relative_path_list),uri))
            else:
              lfs_execute('R+"label://%s"' % uri)
    self.refresh_icon_view()
    self.refresh_tree_view()

  def on_icon_view_item_activated(self, widget, tree_path):
    pathlist = self.icon_view.get_selected_items()
    activated_uris=[]
    for path in pathlist:
      tree_iter = self.icon_view.list_store.get_iter(path)
      uri = xml.sax.saxutils.unescape(self.icon_view.list_store.get_value(tree_iter,2))
      os.system("xdg-open '%s'" % uri)      
      #Mac("open " % uri)
      #Win("start " % uris)
          
  def on_icon_view_key_release(self,widget,event):
    if event.keyval == 65535:
      pathlist = self.icon_view.get_selected_items()
      any_selected=0
      for path in pathlist:
        any_selected=1
        tree_iter = self.icon_view.list_store.get_iter(path)
        selected_name = xml.sax.saxutils.unescape(self.icon_view.list_store.get_value(tree_iter,1))
        lfs_execute('X"%s"' % selected_name)
      if any_selected: 
        self.refresh_icon_view()
  
