from gi.repository import Gtk, Gdk, Gio
import sys, os, urllib, urlparse
import xml.sax.saxutils

path=os.path.abspath(os.path.dirname(sys.argv[0]))

cmd_folder = "%s/.." % path #os.path.dirname(os.path.abspath(__file__))
if cmd_folder not in sys.path:
  sys.path.insert(0, cmd_folder)
import lfsengine

import Window


def pathlist(path):
  return [node for node in path.split('/') if node != ""]

class Application():
  def __init__(self):
    self.lfs = lfsengine.LfsEngine("%s/.lfs.db" % os.path.expanduser('~'))
    self.win = Window.Window()

    provider = Gtk.CssProvider();
    provider.load_from_path("%s/gtk-style.css" % path);    
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
      # Remve current childs of iter. Caution! not remove all items, remove last after insertion
      while self.tree_view.tree_store.iter_n_children(tree_iter) > 1:
        child_name = self.tree_view.tree_store.get_value(child,0)
        self.tree_view.tree_store.remove(child)
        child=self.tree_view.tree_store.iter_children(tree_iter)
      # Add queried child labels
      le_query=''
      name = self.tree_view.tree_store.get_value(tree_iter,0)
      if name == 'labels': #root label
        le_query = ('#^<*')
      else:
        le_query = ('#<"%s"' % name)
      for node in self.lfs.query(le_query):
        if 'name' in node:
          parent2=self.tree_view.tree_store.append(tree_iter, (node['name'],))
          parent3=self.tree_view.tree_store.append(parent2, ('.',))
      # Remove last iter
      if child != None:
        self.tree_view.tree_store.remove(child)

    if tree_iter != None:
      refresh_tree_path(self.tree_view,self.tree_view.tree_store.get_path(tree_iter),"")
    else:
      if not self.tree_view.tree_store.get_iter_first():
        parent=self.tree_view.tree_store.append(None, ('labels',))
        self.tree_view.tree_store.append(parent, ('.',))
        path=Gtk.TreePath("0")
        self.tree_view.expand_row(path,False)
      self.tree_view.map_expanded_rows(refresh_tree_path,None)

  def refresh_location_bar(self,path=None):
    if path == None: path = self.current_path
    if len(path) == 0:
      path = ['ALL','LABELS']
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
    le_query = '~*'
    if len(self.current_path) >0:
      le_query = '~[<"%s"]' % ('" & <"'.join(self.current_path))
    for node in self.lfs.query(le_query):
      pixbuf = self.icon_view.render_icon(Gtk.STOCK_FILE, Gtk.IconSize.DIALOG, None)
      icon=Gio.content_type_get_icon(Gio.content_type_guess(node['uri'],None)[0])
      icon_info=Gtk.IconTheme.get_default().lookup_by_gicon(icon,48,Gtk.IconLookupFlags.FORCE_SIZE|Gtk.IconLookupFlags.GENERIC_FALLBACK)
      if icon_info:
        pixbuf = icon_info.load_icon()
      name=xml.sax.saxutils.escape(node['name'])
      uri=xml.sax.saxutils.escape(node['uri'])
    
      self.icon_view.list_store.append([pixbuf,name,uri,0])


  # event operations on lfs-model and view-model
  def on_tree_view_selection_change(self,tree_selection):
    (model, pathlist) = tree_selection.get_selected_rows()
    self.current_path=[]
    tree_iter=None
    for path in pathlist :
      tree_iter = model.get_iter(path)
      name = model.get_value(tree_iter,0)
      if name != 'labels':
        self.current_path.insert(0,name)
      parent = model.iter_parent(tree_iter)
      while parent != None:
        parent_name = model.get_value(parent,0)
        if parent_name != 'labels':
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
        self.lfs.delete_node(selected_name)
        parent = model.iter_parent(tree_iter)
        self.refresh_tree_view(parent)
        while parent != None:
          parent_name = model.get_value(parent,0)
          if parent_name != 'labels':
            self.lfs.remove_label_from_node(parent_name,selected_name)
            self.refresh_tree_view(parent)
          parent = model.iter_parent(parent)
    
  def on_new_label_entry_activate(self,entry):
    new_label_entry_text = self.new_label_entry.get_text()
    if new_label_entry_text != "":
      self.lfs.create_label(new_label_entry_text)
      for label in self.current_path:
        self.lfs.add_label_to_node(label,new_label_entry_text)

  def on_new_file_entry_activate(self,entry):
    new_file_entry_text = self.new_file_entry.get_text()
    if new_file_entry_text != "":
      self.lfs.create_file(new_file_entry_text)
      for label in self.current_path:
        self.lfs.add_label_to_node(label,new_file_entry_text)

  def on_icon_view_drag_data_received(self, widget, drag_context, x, y, data, info, time):
    for uri in data.get_uris():
      uri_path = urllib.url2pathname(urlparse.urlparse(uri)[2])
      print uri_path
      basename = os.path.basename(uri_path)
      if os.path.isfile(uri_path):
        self.lfs.create_file(basename,uri)
        if len(self.current_path)>0:
          lfs_query = '+["%s"],["%s"]' % ('" | "'.join(self.current_path),basename)
          self.lfs.execute(lfs_query)
      elif os.path.isdir(uri_path):
        #Make sure directories in path already exist as labels, creating them
        for i in range(len(self.current_path)):
          self.lfs.create_label(self.current_path[i])
          #le_query = '+["%s"],["%s"]' % (path[i-1],path[i])
          self.lfs.execute('+["%s"],["%s"]' % ('" | "'.join(self.current_path[:i]),self.current_path[i]))
        #Create a label with the name of the last directory in path, and attach to de path
        uri_path_list=pathlist(uri_path)
        last_dir_in_uri=uri_path_list[-1]
        self.lfs.create_label(last_dir_in_uri)
        self.lfs.execute('+["%s"],["%s"]' % ('" | "'.join(self.current_path),last_dir_in_uri))

        for root,directory,files in os.walk(uri_path):
          relative_path = root.replace(uri_path,"")
          relative_path_list = pathlist(relative_path)
          relative_path_list.insert(0,last_dir_in_uri)
          for i in range(len(relative_path_list)):
            self.lfs.create_label(relative_path_list[i])
            if i > 0:
              lfs_query = '+["%s"],["%s"]' % (relative_path_list[i-1],relative_path_list[i])
              self.lfs.execute(lfs_query)
          for file in files:
            self.lfs.create_file(file,"file://%s/%s" % (root,file))
            lfs_query = '+["%s"],["%s"]' % ('" | "'.join(relative_path_list),file)
            self.lfs.execute(lfs_query)
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
        self.lfs.delete_node(selected_name)
      if any_selected: self.refresh_icon_view()
  
