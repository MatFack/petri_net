


import wx
from objects_canvas.move_strategy import MoveAndSelectStrategy
from graph_panel import GraphPanel
import petri.reachability_graph
import petri.dfa_analysis

class GraphFrame(wx.Frame):
    def __init__(self, parent, petri_panel=None, **kwargs):
        super(GraphFrame, self).__init__(parent, **kwargs)
        self.SetSize((500,600))
        self.rg = None
        self.strategy =  MoveAndSelectStrategy(self.panel_getter)
        self.graph_panel = GraphPanel(self, frame=self)
        self.generate_button = wx.Button(self, id=wx.ID_ANY, label="Generate reachability graph")
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.graph_panel, proportion=1, flag=wx.ALL | wx.EXPAND, border=2)
        sizer.Add(self.generate_button)
        # From
        from_sizer = wx.BoxSizer(wx.HORIZONTAL)
        from_sizer.Add(wx.StaticText(self, label='From state'), flag=wx.CENTER | wx.ALL, border=5)
        self.from_text = wx.TextCtrl(self)
        from_sizer.Add(self.from_text, flag=wx.ALL|wx.EXPAND, proportion=1)
        self.from_add_button = wx.Button(self, id=wx.ID_ANY, label='Set selected')
        self.from_add_button.Disable()
        from_clear_button = wx.Button(self, id=wx.ID_ANY, label='Clear')
        from_clear_button.Bind(wx.EVT_BUTTON, lambda event:self.from_text.SetValue(''))
        from_sizer.Add(self.from_add_button)
        from_sizer.Add(from_clear_button)

        sizer.Add(from_sizer, flag=wx.EXPAND|wx.ALL, border=2)
        # To
        to_sizer = wx.BoxSizer(wx.HORIZONTAL)
        to_sizer.Add(wx.StaticText(self, label='To states'), flag=wx.CENTER | wx.ALL, border=5)
        self.to_text = wx.TextCtrl(self)
        to_sizer.Add(self.to_text, flag=wx.ALL|wx.EXPAND, proportion=1)
        self.to_add_button = wx.Button(self, id=wx.ID_ANY, label='Add selected')
        self.to_add_button.Disable()
        to_clear_button = wx.Button(self, id=wx.ID_ANY, label='Clear')
        to_clear_button.Bind(wx.EVT_BUTTON, lambda event:self.to_text.SetValue(''))
        to_sizer.Add(self.to_add_button)
        to_sizer.Add(to_clear_button)
        sizer.Add(to_sizer, flag=wx.EXPAND)
        # Analyze button
        self.analyze_btn = wx.Button(self, id=wx.ID_ANY, label="Analyze")
        self.analyze_btn.Disable()
        sizer.Add(self.analyze_btn)
        # Result
        self.analyze_result = wx.TextCtrl(self, size=(-1,70), style=wx.TE_MULTILINE)
        sizer.Add(self.analyze_result, flag=wx.EXPAND|wx.ALL, border=2)
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
        self.from_add_button.Bind(wx.EVT_BUTTON, self.OnFromAdd)
        self.to_add_button.Bind(wx.EVT_BUTTON, self.OnToAdd)
        self.analyze_btn.Bind(wx.EVT_BUTTON, self.OnAnalyze)
        
    def OnFromAdd(self, event):
        selection = self.graph_panel.get_selection()
        if len(selection)==1:
            for obj in selection:
                self.from_text.SetValue(obj.unique_id)
    
    def OnToAdd(self, event):
        names_set = set(self.to_text.GetValue().strip().split(','))
        selection = self.graph_panel.get_selection()
        for obj in selection:
            names_set.add(obj.unique_id)
        self.to_text.SetValue(','.join(name for name in names_set if name))
        
    def set_temporary_state(self, marking):
        self.petri_panel.set_temporary_state(marking)
        
    def OnAnalyze(self, event):
        names = self.rg.names
        reverse_names = {v:k for k,v in names.iteritems()}
        fr = self.from_text.GetValue().strip()
        fr_state = reverse_names.get(fr, None)
        if fr is None:
            wx.MessageBox('Unknown state: %s'%fr)
            return
        to = self.to_text.GetValue().strip()
        to_states = []
        for to_name in to.split(','):
            to_state = reverse_names.get(to_name, None)
            if to_state is None:
                wx.MessageBox('Unknown state: %s'%to_state)
                return
            to_states.append(to_state)
        result = petri.dfa_analysis.make_regex(fr_state, to_states, self.rg.explored)
        print fr_state, to_states, self.rg.explored
        self.analyze_result.SetValue(result)
        
        
        
        
    def OnGenerateGraph(self, event):
        net = self.petri_panel.petri
        self.rg = petri.reachability_graph.ReachabilityGraph(net)
        if not net.get_state():
            wx.MessageBox('Petri net is empty!')
            return
        self.rg.explore(net.get_state())
        self.graph_panel.set_graph(self.rg.explored, self.rg.names)
        self.analyze_btn.Enable()
        self.from_add_button.Enable()
        self.to_add_button.Enable()

        
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