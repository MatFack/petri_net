


import wx
import wx.aui
import wx.grid
import wx.lib.scrolledpanel
from objects_canvas.move_strategy import MoveAndSelectStrategy
from graph_panel import GraphPanel
import petri.reachability_graph
import petri.dfa_analysis
import traceback

class GraphAndAnalysisPanel(wx.SplitterWindow):
    def __init__(self, parent, petri_panel=None, **kwargs):
        super(GraphAndAnalysisPanel, self).__init__(parent, **kwargs)
        self.SetSize((500,600))
        upper_panel = wx.Panel(self)
        self.rg = None
        self.strategy =  MoveAndSelectStrategy(self.panel_getter)
        self.graph_panel = GraphPanel(upper_panel, frame=self)
        self.generate_button = wx.Button(upper_panel, id=wx.ID_ANY, label="Generate reachability graph")
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.graph_panel, proportion=1, flag=wx.ALL | wx.EXPAND, border=2)
        sizer.Add(self.generate_button)
        self.current_state_textbox = wx.TextCtrl(upper_panel)
        self.current_state_textbox.SetEditable(False)
        sizer.Add(wx.StaticText(upper_panel, label='Selected state:'), flag=wx.ALL, border=2)
        sizer.Add(self.current_state_textbox, flag=wx.ALL | wx.EXPAND, border=2)
        
        upper_panel.SetSizer(sizer)
        
        self.tabs = wx.aui.AuiNotebook(self)
        
        analysis_panel = wx.lib.scrolledpanel.ScrolledPanel(self.tabs)
        analysis_sizer = wx.BoxSizer(wx.VERTICAL)
        
        ### Analysis
        
        # From
        from_sizer = wx.BoxSizer(wx.HORIZONTAL)
        from_sizer.Add(wx.StaticText(analysis_panel, label='From state'), flag=wx.CENTER | wx.ALL, border=5)
        self.from_text = wx.TextCtrl(analysis_panel)
        from_sizer.Add(self.from_text, flag=wx.ALL|wx.EXPAND, proportion=1)
        self.from_add_button = wx.Button(analysis_panel, id=wx.ID_ANY, label='Set selected')
        self.from_add_button.Disable()
        from_clear_button = wx.Button(analysis_panel, id=wx.ID_ANY, label='Clear')
        from_clear_button.Bind(wx.EVT_BUTTON, lambda event:self.from_text.SetValue(''))
        from_sizer.Add(self.from_add_button)
        from_sizer.Add(from_clear_button)
        analysis_sizer.Add(from_sizer, flag=wx.EXPAND|wx.ALL, border=2)
        # To
        to_sizer = wx.BoxSizer(wx.HORIZONTAL)
        to_sizer.Add(wx.StaticText(analysis_panel, label='To states'), flag=wx.CENTER | wx.ALL, border=5)
        self.to_text = wx.TextCtrl(analysis_panel)
        to_sizer.Add(self.to_text, flag=wx.ALL|wx.EXPAND, proportion=1)
        self.to_add_button = wx.Button(analysis_panel, id=wx.ID_ANY, label='Add selected')
        self.to_add_button.Disable()
        to_clear_button = wx.Button(analysis_panel, id=wx.ID_ANY, label='Clear')
        to_clear_button.Bind(wx.EVT_BUTTON, lambda event:self.to_text.SetValue(''))
        to_sizer.Add(self.to_add_button)
        to_sizer.Add(to_clear_button)
        analysis_sizer.Add(to_sizer, flag=wx.EXPAND)
        # Analyze button
        self.analyze_btn = wx.Button(analysis_panel, id=wx.ID_ANY, label="Analyze")
        self.analyze_btn.Disable()
        analysis_sizer.Add(self.analyze_btn)
        # Result
        self.analyze_result = wx.TextCtrl(analysis_panel, size=(-1,70), style=wx.TE_MULTILINE)
        analysis_sizer.Add(self.analyze_result, flag=wx.EXPAND|wx.ALL, border=2, proportion=1)
        
        analysis_panel.SetSizerAndFit(analysis_sizer)
        
        self.tabs.AddPage(analysis_panel, caption='Analysis')
        
                
        properties_panel = wx.lib.scrolledpanel.ScrolledPanel(self.tabs)
        properties_sizer = wx.BoxSizer(wx.VERTICAL)     
        # Bounded value        
        bounded_value_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.bounded_value = wx.TextCtrl(properties_panel)   
        self.bounded_value.SetEditable(False)
        
        bounded_value_sizer.Add(wx.StaticText(properties_panel, label='Bounded:'), flag=wx.CENTER)
        bounded_value_sizer.Add(self.bounded_value, flag=wx.EXPAND|wx.ALL, border=3, proportion=1)
        
        properties_sizer.Add(bounded_value_sizer, flag=wx.EXPAND)
        # Deadlocks value
        deadlocks_value_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.deadlocks_value = wx.TextCtrl(properties_panel)   
        self.deadlocks_value.SetEditable(False)
        
        deadlocks_value_sizer.Add(wx.StaticText(properties_panel, label='Deadlock states:'), flag=wx.CENTER)
        deadlocks_value_sizer.Add(self.deadlocks_value, flag=wx.EXPAND|wx.ALL, border=3, proportion=1)
        select_deadlocks_button = wx.Button(properties_panel, label='Select deadlock states')
        deadlocks_value_sizer.Add(select_deadlocks_button)
        select_deadlocks_button.Bind(wx.EVT_BUTTON, self.OnSelectDeadlocks)
        
        properties_sizer.Add(deadlocks_value_sizer, flag=wx.EXPAND)
        # Place limits
        self.place_limits_grid = wx.grid.Grid(properties_panel)
        properties_sizer.Add(wx.StaticText(properties_panel, label='Place limits:'))
        properties_sizer.Add(self.place_limits_grid, flag=wx.EXPAND, proportion=1)
        self.place_limits_grid.CreateGrid(0, 3)
        self.place_limits_grid.SetColLabelValue(0, 'Place')
        self.place_limits_grid.SetColLabelValue(1, 'Lower bound')
        self.place_limits_grid.SetColLabelValue(2, 'Upper bound')
        # Different space properties
        properties_sizer.Add(wx.StaticText(properties_panel, label='Expression to be check for every state (e.g. p1!=0):'))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.check_expression = wx.TextCtrl(properties_panel)
        self.check_expression_result = wx.TextCtrl(properties_panel)
        self.check_expression_result.SetEditable(False)
        sizer.Add(self.check_expression, flag=wx.EXPAND, proportion=1)
        self.check_button = wx.Button(properties_panel, label='Check expression')
        self.check_button.Disable()
        sizer.Add(self.check_button)
        properties_sizer.Add(sizer, flag=wx.EXPAND)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(properties_panel, label='States which didn\'t fit: '))
        sizer.Add(self.check_expression_result, flag=wx.EXPAND, proportion=1)
        self.select_unfit_states_button = wx.Button(properties_panel, label='Select unfit states')
        sizer.Add(self.select_unfit_states_button)
        #sizer = wx.BoxSizer(wx.HORIZONTAL)
        # end 
        
        properties_sizer.Add(sizer, flag=wx.EXPAND)
        properties_panel.SetSizerAndFit(properties_sizer)
        
        self.tabs.AddPage(properties_panel, caption='Properties')        
        #
        
        
        
        #sizer.Add(self.tabs, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.SplitHorizontally(upper_panel, self.tabs)
        self.SetMinimumPaneSize(20)
        #self.SetSizer(sizer)
        
        self.petri_panel = petri_panel
        self.setup_bindings()
        self.sash_position = 300
        
        
    def setup_bindings(self):
        # Buttons bindings
        self.generate_button.Bind(wx.EVT_BUTTON, self.OnGenerateGraph)
        self.from_add_button.Bind(wx.EVT_BUTTON, self.OnFromAdd)
        self.to_add_button.Bind(wx.EVT_BUTTON, self.OnToAdd)
        self.analyze_btn.Bind(wx.EVT_BUTTON, self.OnAnalyze)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSashChanged)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        
        self.check_button.Bind(wx.EVT_BUTTON, self.OnCheck)
        self.select_unfit_states_button.Bind(wx.EVT_BUTTON, lambda event: self.select_states(self.check_expression_result.GetValue()))
        
    def OnCheck(self, event):
        expr = self.check_expression.GetValue()
        try:
            code = compile(expr, 'checked_string', 'eval')
        except:
            wx.MessageBox('Error while compiling expression:\n' + traceback.format_exc())
            return
        unfit_states = []
        place_names = [place.unique_id for place in self.petri_panel.petri.get_sorted_places()]
        for state, name in self.rg.names.iteritems():
            namespace = dict(zip(place_names, state))
            namespace['_places'] = namespace
            try:
                result = eval(code, {}, namespace)
            except:
                wx.MessageBox('Error while executing expression:\n'+ traceback.format_exc())
                break
            finally:
                namespace['_places'] = None #just in case
            if not result:
                unfit_states.append(name)
        else:
            result = ','.join(unfit_states)
            self.check_expression_result.SetValue(result)
        
    def select_states(self, value):
        self.graph_panel.select_states(state for state in value.split(',') if state)
        
    def OnSelectDeadlocks(self, event):
        self.select_states(self.deadlocks_value.GetValue())
          
        
    def OnSashChanged(self, event):
        self.sash_position = self.GetSashPosition()
    
    def OnSize(self, event):
        self.SetSashPosition(self.sash_position)
                
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
        value = '(' + ', '.join(str(c) for c in marking) + ')'
        self.current_state_textbox.SetValue(value)
        self.petri_panel.set_temporary_state(marking)
        
    def OnAnalyze(self, event):
        names = self.rg.names
        reverse_names = {v:k for k,v in names.iteritems()}
        fr_name = self.from_text.GetValue().strip()
        fr_state = reverse_names.get(fr_name, None)
        if fr_state is None:
            wx.MessageBox('Unknown state: %s'%fr_name)
            return
        to = self.to_text.GetValue().strip()
        to_states = []
        for to_name in to.split(','):
            to_state = reverse_names.get(to_name, None)
            if to_state is None:
                wx.MessageBox('Unknown state: %s'%to_name)
                return
            to_states.append(to_state)
        result = petri.dfa_analysis.make_regex(fr_state, to_states, self.rg.explored)
        print fr_state, to_states, self.rg.explored
        if len(result)<50000:
            self.analyze_result.SetValue(result)
            return
        wx.MessageBox('The resulting string is too large, please select a file to save it')
        dlg = wx.FileDialog(self, message='Save result as...', wildcard='Text file|*.txt|All files|*',style=wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            try:
                with open(path, 'wb') as f:
                    f.write(result)
            except Exception, ex:
                wx.MessageBox("Failed to save to file: "+traceback.format_exc())
            else:
                self.analyze_result.SetValue("Saved %d bytes to %s"%(len(result),path))
                    
        
    def OnGenerateGraph(self, event):
        net = self.petri_panel.petri
        self.rg = petri.reachability_graph.ReachabilityGraph(net)
        if not net.get_state():
            wx.MessageBox('Petri net is empty!')
            return
        self.rg.explore(net.get_state())
        places = net.get_sorted_places()
        self.update_place_limits(places, self.rg.place_limits)
        self.graph_panel.set_graph(self.rg.explored, self.rg.names)
        self.bounded_value.SetValue(str(self.rg.bounded))
        self.check_button.Enable()
        self.deadlocks_value.SetValue(','.join(self.rg.dead_states))
        if not self.rg.bounded:
            self.analyze_btn.Disable()
            return
        self.analyze_btn.Enable()
        self.from_add_button.Enable()
        self.to_add_button.Enable()
        
    def update_place_limits(self, places, place_limits):
        num_rows = self.place_limits_grid.GetNumberRows()
        if num_rows:
            self.place_limits_grid.DeleteRows(numRows=num_rows)
        self.place_limits_grid.AppendRows(len(places))
        for i, (place, (min_val, max_val)) in enumerate(zip(places, place_limits)):
            self.place_limits_grid.SetCellValue(i, 0, place.unique_id)
            self.place_limits_grid.SetCellValue(i, 1, str(min_val))
            self.place_limits_grid.SetCellValue(i, 2, str(max_val))
            

    def panel_getter(self):
        return self.graph_panel
    
    def on_command_append(self):
        pass
    
class GraphFrame(wx.Frame):
    def __init__(self, parent, petri_panel=None, **kwargs):
        super(GraphFrame, self).__init__(parent, **kwargs)
        self.panel = GraphAndAnalysisPanel(self, petri_panel)
        

if __name__ == '__main__':
    from util.wx_app import app
    import wx.lib.inspection
    wx.lib.inspection.InspectionTool().Show()
    frame = GraphFrame(None, title='Reachability graph', size=(500,500))
    frame.Show(True)
    app.MainLoop()
