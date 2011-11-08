from gi.repository import Gtk, Gdk, GdkPixbuf

class QueryViewFrame(Gtk.Frame):
  def __init__(self):
    Gtk.Frame.__init__(self)
    self.get_style_context().add_class("query-view-frame")    
    self.set_shadow_type(Gtk.ShadowType.NONE)
    self.table = Gtk.Table(2,1,False)
    self.table.get_style_context().add_class("center-pane-table")
    self.add(self.table)

    self.location_bar = LocationBar()
    self.table.attach(self.location_bar,0,1,0,1,Gtk.AttachOptions.FILL,Gtk.AttachOptions.FILL)

    self.icon_view = IconView()
    self.win = Gtk.ScrolledWindow()
    self.win.add(self.icon_view)
    self.table.attach(self.win,0,1,1,2) #,Gtk.AttachOptions.EXPAND) #,Gtk.AttachOptions.FILL)

class IconView(Gtk.IconView):
  def __init__(self):
    self.list_store = Gtk.ListStore(GdkPixbuf.Pixbuf,str)
    Gtk.IconView.__init__(self,model=self.list_store)
    self.get_style_context().add_class("icon-view")    
 
    self.set_pixbuf_column(0)
    self.set_markup_column(1)
    self.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
    
    self.icon_theme=Gtk.IconTheme.get_default()
        
    dnd_list = Gtk.TargetEntry.new("text/uri-list", 0, 0)
    self.drag_dest_set(
      Gtk.DestDefaults.MOTION |
      Gtk.DestDefaults.HIGHLIGHT |
      Gtk.DestDefaults.DROP,
      [dnd_list],
      Gdk.DragAction.MOVE )
    self.drag_dest_add_uri_targets()

  def refresh(self,nodes):
    for node in nodes:
      pixbuf = self.render_icon(Gtk.STOCK_FILE, Gtk.IconSize.DIALOG, None)
      self.list_store.append([pixbuf,node['name'].replace("&","")])


class LocationBar(Gtk.Frame):
  def __init__(self):
    Gtk.Frame.__init__(self)
    self.get_style_context().add_class("location-bar")    
    self.set_shadow_type(Gtk.ShadowType.NONE)

    self.toolbar=Gtk.Toolbar()
    self.toolbar.set_style(Gtk.ToolbarStyle.TEXT)
    self.toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
    self.add(self.toolbar)

  def refresh(self,path):
    for child in self.toolbar.get_children():
      self.toolbar.remove(child)
    for node in path:
      ttb = Gtk.ToggleToolButton(label=node)
      ttb.get_style_context().add_class("location-button")
      ttb.set_active(1)
      self.toolbar.add(ttb)
    self.show_all()
   

