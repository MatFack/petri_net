


import wx
from objects_canvas.move_strategy import MoveAndSelectStrategy
from graph_panel import GraphPanel
import petri.reachability_graph


class GraphFrame(wx.Frame):
    def __init__(self, parent, petri_panel=None, **kwargs):
        super(GraphFrame, self).__init__(parent, **kwargs)
        self.SetSize((500,600))
        self.strategy =  MoveAndSelectStrategy(self.panel_getter)
        self.graph_panel = GraphPanel(self, frame=self)
        self.generate_button = wx.Button(self, id=wx.ID_ANY, label="Generate reachability graph")
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.graph_panel, proportion=1, flag=wx.ALL | wx.EXPAND, border=2)
        sizer.Add(self.generate_button)
        self.SetSizer(sizer)
        self.petri_panel = petri_panel
        self.setup_menu()
        self.setup_bindings()
        
    def setup_menu(self):
        menubar = wx.MenuBar()
        editMenu = wx.Menu()
        self.undo_item = editMenu.Append(wx.ID_UNDO, '&Undo\tCtrl+Z', 'Undo last action')
        self.redo_item = editMenu.Append(wx.ID_REDO, '&Redo\tCtrl+Y', 'Redo last action')
        editMenu.AppendSeparator()
        self.select_all_item = editMenu.Append(wx.ID_SELECTALL, '&Select all\tCtrl+A', 'Select all elements')
        menubar.Append(editMenu, '&Edit')
        viewMenu = wx.Menu()
        self.zoom_in_item = viewMenu.Append(wx.NewId(), 'Zoom &in\tCtrl++', 'Zoom in')
        self.zoom_out_item = viewMenu.Append(wx.NewId(), 'Zoom &out\tCtrl+-', 'Zoom out')
        self.zoom_restore_item = viewMenu.Append(wx.NewId(), '&Zoom restore\tCtrl+R', 'Zoom restore')
        menubar.Append(viewMenu, '&View')
        self.SetMenuBar(menubar)
        
    def setup_bindings(self):
        # Menu bindings
        self.Bind(wx.EVT_MENU, self.OnUndo, self.undo_item)
        self.Bind(wx.EVT_MENU, self.OnRedo, self.redo_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnSelectAll, self.select_all_item)
        # View 
        self.Bind(wx.EVT_MENU, self.OnZoomIn, self.zoom_in_item)
        self.Bind(wx.EVT_MENU, self.OnZoomOut, self.zoom_out_item)
        self.Bind(wx.EVT_MENU, self.OnZoomRestore, self.zoom_restore_item)
        # Buttons bindings
        self.generate_button.Bind(wx.EVT_BUTTON, self.OnGenerateGraph)
        
    def OnGenerateGraph(self, event):
        net = self.petri_panel.petri
        rg = petri.reachability_graph.ReachabilityGraph(net)
        if not net.get_state():
            wx.MessageBox('Petri net is empty!')
            return
        rg.explore(net.get_state())
        self.graph_panel.set_graph(rg.explored, rg.names)

        
    def OnUndo(self, event):
        self.graph_panel.undo()
        
    def OnRedo(self, event):
        self.graph_panel.redo()
        
    def OnSelectAll(self, event):
        self.graph_panel.select_all()
        
    def OnZoomIn(self, event):
        self.graph_panel.zoom_in()
        
    def OnZoomOut(self, event):
        self.graph_panel.zoom_out()
        
    def OnZoomRestore(self, event):
        self.graph_panel.zoom_restore()

    def panel_getter(self):
        return self.graph_panel
    
    def on_command_append(self):
        pass

if __name__ == '__main__':
    from util.wx_app import app
    frame = GraphFrame(None, title='Reachability graph', size=(500,500))
    frame.Show(True)
    app.MainLoop()