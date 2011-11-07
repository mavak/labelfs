from gi.repository import Gtk

import Globals

class SelectedNodesFrame(Gtk.Frame):
  def __init__(self):
    Gtk.Frame.__init__(self)
    self.set_shadow_type(Gtk.ShadowType.NONE)
    self.table = Gtk.Table(2,1,False)
    self.add(self.table)
    self.get_style_context().add_class("selected-node-frame")    

    self.selected_node_box = SelectedNodeBox()
    self.table.attach(self.selected_node_box,0,1,0,1,Gtk.AttachOptions.FILL,Gtk.AttachOptions.FILL)

class SelectedNodeBox(Gtk.Box):
  def __init__(self):
    Gtk.Box.__init__(self)
    self.get_style_context().add_class("selected-node-panel")    

    self.set_size_request(180,-1)
