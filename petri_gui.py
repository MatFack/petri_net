#!/usr/bin/python
# -*- coding: utf-8 -*-


# DONE: Commands history
# DONE: Move command
# DONE: Create command
# DONE: Delete command
# DONE: Copy - puts selected into Buffer - this gonna be tough
# DONE: Make coordinates in buffer relative,
# DONE: Cut - creates Delete command, puts selected into Buffer
# DONE: Paste - creates Create command, puts there objects from Buffer
# Test test test

# DONE: Tabs
# TODO: Put properties somewhere, (menu - analysis - tabbed window)
# DONE: Create menu (save, open, exit, export)

# TODO: Probably need unified frame for displaying graphs and petri nets.
# TODO: Think about where graph and properties will be

# TODO: split code into modules, but this isn't so urgent

# So, the user looks at the graph and clicks one vertex, and the nclicks another vertex.   
# First: analysis! Do it somehow, but it has to be
# Second: shortest path from one set of vertices to another set of vertices
# Third: ability to select all dead states
# Probably, ability to select by some criteria


import time
from objects_canvas.strategy import Strategy
from objects_canvas.move_strategy import MoveAndSelectStrategy
import traceback
import json
from petri import petri, reachability_graph
import wx
import wx.aui
import wx.grid
import wx.lib.buttons
import itertools
import petrigui.add_object_strategy
import petrigui.petri_objects
import petrigui.petri_panel
import petri.net_properties as net_properties
import numpy as np
import stategraph.graph_frame
import stategraph
from petri.net_properties import Tristate

    
class SimulateStrategy(Strategy):
    def __init__(self, panel):
        super(SimulateStrategy, self).__init__(panel=panel)
        self.allow_undo_redo = False
        
    def on_left_down(self, event):
        super(SimulateStrategy, self).on_left_down(event)
        obj = self.panel.get_object_at(self.mouse_x, self.mouse_y)
        if isinstance(obj, petri.Transition):
            if obj.is_enabled:
                obj.fire()
                self.panel.Refresh()
                self.panel.on_petri_changed()
                #print self.panel.petri.get_state()

class Buffer(object):
    def __init__(self):
        self.places = None
        self.transitions = None
    
    def set_content(self, places, transitions):
        self.places = places
        self.transitions = transitions
        
    def reset_content(self):
        self.places = self.transitions = None
        
    def get_content(self):
        return self.places, self.transitions
    
    def is_empty(self):
        return self.places is None and self.transitions is None

class ImportExportFormat(object):
    @classmethod
    def get_formats(self):
        return [('All files', '*.*')]
    
    @classmethod
    def get_wildcard(self):
        return '|'.join('%s (%s)|%s'%(label, wc, wc) for (label, wc) in self.get_formats())
    
    @classmethod
    def export_net(cls, petri):
        raise NotImplementedError
    
    @classmethod
    def import_net(cls, s):
        raise NotImplementedError
    
    _persistent = False
    
    @classmethod
    @property
    def persistent(cls):
        """ True if petri net can be stored in this format without (major) loss. False if it's just an export/import format """
        return cls._persistent

class TxtFormat(ImportExportFormat):
    name = 'TXT file'
    description = 'TXT file'
    @classmethod
    def get_formats(self):
        return [('TXT files', '*.txt')] + super(TxtFormat, self).get_formats()
    
    @classmethod
    def export_net(cls, petri):
        return petri.to_string()
    
    @classmethod
    def import_net(cls, s):
        net =  petrigui.petri_objects.GUIPetriNet.from_string(s)
        net.automatic_layout()
        return net
    
class JSONFormat(ImportExportFormat):
    name = 'JSON file'
    description = 'JSON file'
    _persistent = True
    @classmethod
    def get_formats(self):
        return [('JSON files', '*.json')] + super(JSONFormat, self).get_formats()
    
    @classmethod
    def export_net(cls, petri):
        return json.dumps(petri.to_json_struct())
    
    @classmethod
    def import_net(cls, s):
        return petrigui.petri_objects.GUIPetriNet.from_json_struct(json.loads(s))
  
# TODO: Well, probably we will have to create some unified interface to all those properties.
# And also, 
        
class GUIProperty(object):
    def __init__(self, field, properties, **kwargs):
        self.field = field
        self.properties = properties
        self.parent = None
        
        self.proportion = 0
        
    def init_ui(self, parent):
        self.element = self.create_element(parent)
        self.parent = parent
        return self.element
    
    def create_element(self, parent):
        raise NotImplementedError
        
    def get_value(self):
        return getattr(self.properties, self.field)
        
    def update(self):
        #setattr(self.properties, self.field, None)
        value = self.get_value()
        self.show_to_ui(value)
        
    def show_to_ui(self, value):
        raise NotImplementedError()
    
                
class LabeledProperty(GUIProperty):
    def __init__(self, field, properties, label, **kwargs):
        super(LabeledProperty, self).__init__(field, properties, **kwargs)
        self.label = label+': '

        
    def create_element(self, parent):
        result = wx.BoxSizer(wx.HORIZONTAL)
        label_elem = wx.StaticText(parent, label=self.label)
        labeled_value_elem = self.create_element_for_label(parent)
        result.Add(label_elem, flag=wx.CENTER)
        result.Add(labeled_value_elem, flag=wx.CENTER, proportion=1)
        return result
    
    def create_element_for_label(self, parent):
        raise NotImplementedError()
        
        
class ValueProperty(LabeledProperty):
    def create_element_for_label(self, parent):
        self.__value_elem = wx.TextCtrl(parent)
        self.__value_elem.SetEditable(False)
        return self.__value_elem
    
    def value_to_string(self, value):
        if isinstance(value, Tristate):
            value = value.value
            if value is None:
                return 'Unknown'
        return str(value)
    
    def show_to_ui(self, value):
        self.__value_elem.SetValue(self.value_to_string(value))
        
class ValueListProperty(ValueProperty):
    def value_to_string(self, value):
        return ', '.join(value)

        
class MatrixProperty(LabeledProperty):
    def __init__(self, field, properties, label, row_label_getter, col_label_getter, row_dclick_handler=None, col_dclick_handler=None, **kwargs):
        super(MatrixProperty, self).__init__(field, properties, label, **kwargs)
        self.row_label_getter = row_label_getter
        self.col_label_getter = col_label_getter
        self.row_dclick_handler = row_dclick_handler
        self.col_dclick_handler = col_dclick_handler
        self.proportion = 1
        
    def create_element(self, parent):
        result = wx.BoxSizer(wx.VERTICAL)
        label_elem = wx.StaticText(parent, label=self.label)
        self.__labeled_value_elem = self.create_element_for_label(parent)
        result.Add(label_elem, flag=wx.LEFT)
        result.Add(self.__labeled_value_elem, flag=wx.EXPAND, proportion=1)
        return result

    def create_element_for_label(self, parent):
        self.__grid = wx.grid.Grid(parent)
        self.__grid.EnableDragColSize(True)
        self.__grid.EnableDragRowSize(True)
        self.__grid.EnableEditing(False)
        self.__grid.CreateGrid(0,0)
        self.__grid.Bind(wx.grid.EVT_GRID_LABEL_LEFT_DCLICK, self.OnCellDClicked)
        return self.__grid
    
    def OnCellDClicked(self, event):
        row,col = event.GetRow(), event.GetCol()
        if col==-1:
            self.OnRowDClicked(event)
        elif row==-1:
            self.OnColDClicked(event)
            
    def OnRowDClicked(self, event):
        if self.row_dclick_handler is not None:
            self.row_dclick_handler(event)
    
    def OnColDClicked(self, event):
        if self.col_dclick_handler is not None:
            self.col_dclick_handler()
    
    def to_list_matrix(self, value):
        if isinstance(value, dict):
            value = value.items()
        return value
    
    def get_grid(self):
        return self.__grid
    
    def show_to_ui(self, value):
        matrix = self.to_list_matrix(value)
        r = len(matrix)
        try:
            c = len(matrix[0])
        except IndexError:
            c = 0
        rows, cols = self.__grid.GetNumberRows(), self.__grid.GetNumberCols()
        diff_r = r-rows
        diff_c = c-cols
        if diff_r>0:
            self.__grid.AppendRows(diff_r)
        elif diff_r<0:
            self.__grid.DeleteRows(pos=0, numRows=abs(diff_r))
        if diff_c>0:
            self.__grid.AppendCols(diff_c)
        elif diff_c<0:
            self.__grid.DeleteCols(pos=0, numCols=abs(diff_c))
        for i, name in zip(xrange(c), self.col_label_getter()):
            self.__grid.SetColLabelValue(i, str(name))
        for i,name in zip(xrange(r), self.row_label_getter()):
            self.__grid.SetRowLabelValue(i, str(name))
        for i in xrange(r):
            for j in xrange(c):
                val = matrix[i][j]
                self.__grid.SetCellValue(i, j, str(val))
                self.__grid.SetCellBackgroundColour(i, j, wx.WHITE)
        #self.__grid.SetRowLabelSize(wx.grid.GRID_AUTOSIZE)
        #self.__grid.SetColLabelSize(wx.grid.GRID_AUTOSIZE)

    
def set_row_color(grid, row, color):
    columns = grid.GetNumberCols()
    for c in xrange(columns):
        grid.SetCellBackgroundColour(row, c, color)
                
class TrapsMatrixProperty(MatrixProperty):
    def show_to_ui(self, value):
        super(TrapsMatrixProperty, self).show_to_ui(value)
        grid = self.get_grid()
        for i, trap in enumerate(value):
            if trap.is_marked_trap:
                set_row_color(grid, i, wx.GREEN)
                
class DeadlocksMatrixProperty(MatrixProperty):
    def show_to_ui(self, value):
        super(DeadlocksMatrixProperty, self).show_to_ui(value)
        grid = self.get_grid()
        for i, deadlock in enumerate(value):
            if deadlock.has_marked_trap:
                set_row_color(grid, i, wx.GREEN)
            elif deadlock.has_trap:
                set_row_color(grid, i, wx.Colour(128,128,0))

import wx.lib.scrolledpanel
class PropertiesTabPanelMixin(object):
    def __init__(self, parent, petri_panel, properties, properties_lst, **kwargs):
        scrolled = kwargs.pop('scrolled', False)
        super(PropertiesTabPanelMixin, self).__init__(parent, **kwargs)
        self.petri_panel = petri_panel
        self.properties = properties
        self.properties_lst = properties_lst
        sizer = wx.BoxSizer(wx.VERTICAL)
        update_button = wx.Button(self, id=wx.ID_ANY, label="Update properties")
        update_button.Bind(wx.EVT_BUTTON, self.OnUpdate)
        sizer.Add(update_button)
        if scrolled:
            additional_sizer = wx.BoxSizer(wx.VERTICAL)
        else:
            additional_sizer = sizer
        for prop in self.properties_lst:
            element = prop.init_ui(self)
            additional_sizer.Add(element, flag=wx.EXPAND | wx.ALL, proportion=prop.proportion, border=3)
        if scrolled:
            sizer.Add(additional_sizer, flag=wx.EXPAND)
        self.SetSizer(sizer)
        try:
            self.SetupScrolling()
        except:
            pass
        
    def OnUpdate(self, event):
        self.update_properties()
        
    def update_properties(self):
        #print "HERE ME CALLING"
        #print traceback.print_stack()
        self.properties._reset(self.petri_panel.petri)
        for prop in self.properties_lst:
            prop.update()
        #self.Layout()
        #self.Fit()
        self.Refresh()
        
class ScrolledPropertiesTabPanel(PropertiesTabPanelMixin, wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, *args, **kwargs):
        kwargs['scrolled'] = True
        super(ScrolledPropertiesTabPanel, self).__init__(*args, **kwargs)

class UsualPropertiesTabPanel(PropertiesTabPanelMixin, wx.Panel):
    pass
   
class PropertiesPanel(wx.Panel):
    def __init__(self, parent, petri_panel, **kwargs):
        super(PropertiesPanel, self).__init__(parent, **kwargs)
        self.petri_panel = petri_panel
        self.properties = net_properties.PetriProperties(self.petri_panel.petri)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.tabs = wx.aui.AuiNotebook(self)
        self.tabs.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, lambda event:event.Veto()) # Forbid closing
        sizer.Add(self.tabs, flag=wx.EXPAND, proportion=1)
        self.SetSizer(sizer)
        transition_lambda = lambda petri_panel=self.petri_panel:(transition.unique_id for transition in
                                                                    petri_panel.petri.get_sorted_transitions())
        place_lambda = lambda petri_panel=self.petri_panel:(place.unique_id for place in 
                                                                    petri_panel.petri.get_sorted_places())
        ordinal_lambda = lambda:itertools.count(1)
        
        empty_lambda = lambda:itertools.cycle([''])
        clsf_properties = [('State machine', 'state_machine'),
                           ('Marked graph','marked_graph'),
                           ('Free choice net','free_choice'),
                           ('Extended free choice net','extended_free_choice'),
                           ('Simple','simple'),
                           ('Asymmetric','asymmetric')]
        clsf_properties = [ValueProperty(field, self.properties, label=label) for label,field in clsf_properties]
        #classification_properties
        self.tabs.AddPage(ScrolledPropertiesTabPanel(self, self.petri_panel, self.properties, clsf_properties), caption="Classification")
        # incidence matrix
        im_property = MatrixProperty('incidence_matrix', self.properties, label='Incidence matrix',
                                      row_label_getter=place_lambda, col_label_getter=transition_lambda)
        #liveness = ValueProperty('liveness', self.properties, label='Liveness')
        
        incidence_properties = [im_property]
        self.tabs.AddPage(UsualPropertiesTabPanel(self, self.petri_panel, self.properties, incidence_properties), caption="Incidence matrix")
        # t-invariants
        t_invariants_prop = MatrixProperty('t_invariants', self.properties, label='T invariants',
                                           row_label_getter=ordinal_lambda, col_label_getter=transition_lambda,
                                           row_dclick_handler=self.transition_selector)
                
        uncovered_by_t = ValueListProperty('t_uncovered', self.properties, label='Transitions not covered by T invariants')
                
        consistency = ValueProperty('consistency', self.properties, label='Consistency')

        A_rank = ValueProperty('A_rank', self.properties, label='Incidence matrix rank')
        
        Ax_ineq_prop = MatrixProperty('Ax_ineq_sol', self.properties, label='Ax>0 inequation solutions:',
                                           row_label_getter=ordinal_lambda, col_label_getter=transition_lambda,
                                           row_dclick_handler=self.transition_selector)
        
        repeatable = ValueProperty('repeatable', self.properties, label='Repeatable')
        
        regulated = ValueProperty('regulated', self.properties, label='Regulated')
                        
        t_inv_properties = [t_invariants_prop, uncovered_by_t, consistency, A_rank, Ax_ineq_prop, repeatable, regulated]

        self.tabs.AddPage(UsualPropertiesTabPanel(self, self.petri_panel, self.properties, t_inv_properties), caption='T invariants')
        # s-invariants
        s_invariants_prop = MatrixProperty('s_invariants', self.properties, label='S invariants',
                                           row_label_getter=ordinal_lambda, col_label_getter=place_lambda)

        uncovered_by_s = ValueListProperty('s_uncovered', self.properties, label='Places not covered by S invariants')


        place_limits = MatrixProperty('place_limits', self.properties, label='Token limits',
                                           row_label_getter=empty_lambda, col_label_getter=lambda:['Place', 'Limit'])


        s_inv_properties = [s_invariants_prop, uncovered_by_s, place_limits]
        
        self.tabs.AddPage(UsualPropertiesTabPanel(self, self.petri_panel, self.properties, s_inv_properties), caption='S invariants')
        # deadlocks and traps
        deadlocks_prop = DeadlocksMatrixProperty('deadlocks', self.properties, label='Deadlocks (green deadlocks have marked trap, olive have trap)',
                                           row_label_getter=ordinal_lambda, col_label_getter=place_lambda, 
                                           row_dclick_handler=self.place_selector)
        
        traps_prop = TrapsMatrixProperty('traps', self.properties, label='Traps (green are marked traps)',
                                           row_label_getter=ordinal_lambda, col_label_getter=place_lambda,
                                           row_dclick_handler=self.place_selector)

        dl_trap_properties = [deadlocks_prop, traps_prop]
        
        self.tabs.AddPage(UsualPropertiesTabPanel(self, self.petri_panel, self.properties, dl_trap_properties), caption='Deadlocks & traps')
        
        self.tabs.AddPage(stategraph.graph_frame.GraphAndAnalysisPanel(self, self.petri_panel), caption='Reachability graph')
        self.tabs.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnPageChanged)
        #self.update_properties()
        
    def OnPageChanged(self, event):
        self.Parent.OnPageChanged(self.tabs.GetSelection())
        
    def object_selector(self, event, objects):
        row = event.GetRow()
        grid = event.GetEventObject()
        cols = grid.GetNumberCols()
        result = {}
        for i,obj in enumerate(objects):
            val = grid.GetCellValue(row, i)
            if int(val):
                result[obj] = val
        self.petri_panel.highlight_objects(result)
        
    def transition_selector(self, event):
        self.object_selector(event, self.petri_panel.petri.get_sorted_transitions())
        
    def place_selector(self, event):
        self.object_selector(event, self.petri_panel.petri.get_sorted_places())

        
    def update_properties(self):
        page = self.tabs.GetPage(self.tabs.GetSelection())
        page.update_properties()
   
class PetriAndProperties(wx.SplitterWindow):
    def __init__(self, parent, frame, clip_buffer, tab_splitter_position, **kwargs):
        super(PetriAndProperties, self).__init__(parent, **kwargs)
        self.frame = frame
        self.tab_splitter_position = tab_splitter_position
        self.petri_panel = petrigui.petri_panel.PetriPanel(self, frame=frame, clip_buffer=clip_buffer)
        self.properties_panel = PropertiesPanel(self, self.petri_panel)
        #self.SplitHorizontally(self.properties_panel, self.petri_panel, sashPosition=100)
        #self.Unsplit()
        self.SetMinimumPaneSize(self.properties_panel.tabs.GetTabCtrlHeight()*2)
        self.SplitVertically(self.properties_panel, self.petri_panel, sashPosition=100)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.first_sash_event = False
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.OnSashPosChanged)

        
    def update_splitter_position(self, pos):
        self.tab_splitter_position = pos
        self.SetSashPosition(self.tab_splitter_position)
        
    def OnSize(self, event):
        self.update_splitter_position(self.tab_splitter_position)
        event.Skip()
        
    def OnSashPosChanged(self, event):
        if not self.first_sash_event:
            self.first_sash_event = True
        else:
            self.tab_splitter_position = self.GetSashPosition()
            self.frame.set_tab_splitter_position(self.GetSashPosition())
        event.Skip()
        
    def OnPageChanged(self, page_number):
        self.frame.tab_page_number = page_number
        
    def set_tab_page_number(self, page_number):
        self.properties_panel.tabs.SetSelection(page_number)
                
    def update_properties(self):
        self.properties_panel.update_properties()

class Example(wx.Frame):
    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(1400, 800))
        
        self.splitter_orientation = wx.SPLIT_VERTICAL
        self.tab_page_number = 0
        self.clip_buffer = Buffer()
        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        formats = [TxtFormat,]
        menubar = wx.MenuBar()
        fileMenu = wx.Menu()
        new_page_item = fileMenu.Append(wx.ID_NEW, '&New\tCtrl+N', 'New Petri net')
        open_item = fileMenu.Append(wx.ID_OPEN, '&Open\tCtrl+O', 'Open petri net')
        self.close_item = fileMenu.Append(wx.ID_CLOSE, '&Close\tCtrl+W', 'Close current net')
        fileMenu.AppendSeparator()
        self.save_item = fileMenu.Append(wx.ID_SAVE, '&Save\tCtrl+S', 'Save petri net')
        self.save_as_item = fileMenu.Append(wx.ID_SAVEAS, 'S&ave as\tCtrl+Shift+S', 'Save petri net as')
        fileMenu.AppendSeparator()
        import_menu = wx.Menu()
        export_menu = wx.Menu()
        for format in formats:
            def import_handler(event):
                self.open(format)
            def export_handler(event):
                self.save_as(format)
            import_item = import_menu.Append(wx.NewId(), format.name, format.description)
            self.Bind(wx.EVT_MENU, import_handler, import_item)
            export_item = export_menu.Append(wx.NewId(), format.name, format.description)
            self.Bind(wx.EVT_MENU, export_handler, export_item)
        fileMenu.AppendMenu(wx.NewId(), '&Import from', import_menu)
        fileMenu.AppendMenu(wx.NewId(), '&Export to', export_menu)
        fileMenu.AppendSeparator()
        quit_item = fileMenu.Append(wx.ID_EXIT, '&Quit\tCtrl+Q', 'Quit application')
        menubar.Append(fileMenu, '&File')
        editMenu = wx.Menu()
        self.undo_item = editMenu.Append(wx.ID_UNDO, '&Undo\tCtrl+Z', 'Undo last action')
        self.redo_item = editMenu.Append(wx.ID_REDO, '&Redo\tCtrl+Y', 'Redo last action')
        editMenu.AppendSeparator()
        self.cut_item = editMenu.Append(wx.ID_CUT, '&Cut\tCtrl+X', 'Cut elements')
        self.copy_item = editMenu.Append(wx.ID_COPY, 'C&opy\tCtrl+C', 'Copy elements')
        self.paste_item = editMenu.Append(wx.ID_PASTE, '&Paste\tCtrl+V', 'Paste elements')
        self.delete_item = editMenu.Append(wx.ID_DELETE, '&Delete\tDelete', 'Delete elements')
        editMenu.AppendSeparator()
        self.select_all_item = editMenu.Append(wx.ID_SELECTALL, '&Select all\tCtrl+A', 'Select all elements')
        menubar.Append(editMenu, '&Edit')
        viewMenu = wx.Menu()
        self.zoom_in_item = viewMenu.Append(wx.NewId(), 'Zoom &in\tCtrl++', 'Zoom in')
        self.zoom_out_item = viewMenu.Append(wx.NewId(), 'Zoom &out\tCtrl+-', 'Zoom out')
        self.zoom_restore_item = viewMenu.Append(wx.NewId(), '&Zoom restore\tCtrl+R', 'Zoom restore')
        viewMenu.AppendSeparator()
        change_splitter_orientation = viewMenu.Append(wx.NewId(), 'Change splitter orientation', 'Change splitter orientation')
        menubar.Append(viewMenu, '&View')
        layoutMenu = wx.Menu()
        self.automatic_layout_item = layoutMenu.Append(wx.NewId(), '&Automatic layout', 'Automatic layout of current net')
        menubar.Append(layoutMenu, '&Layout')
        
        analysisMenu = wx.Menu()
        self.reachability_graph_item = analysisMenu.Append(wx.NewId(), '&Reachability graph', 'Generate reachability graph of current net')
        menubar.Append(analysisMenu, '&Analysis')
        
        self.CreateStatusBar()
        self.tab_splitter_position = 700
        self.SetMenuBar(menubar)
        # Menu bindings
        # File
        self.Bind(wx.EVT_MENU, self.OnNew, new_page_item)
        self.Bind(wx.EVT_MENU, self.OnOpen, open_item)
        self.Bind(wx.EVT_MENU, self.OnClose, self.close_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnSave, self.save_item)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, self.save_as_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnQuit, quit_item)
        # Edit
        self.Bind(wx.EVT_MENU, self.OnUndo, self.undo_item)
        self.Bind(wx.EVT_MENU, self.OnRedo, self.redo_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnCut, self.cut_item)
        self.Bind(wx.EVT_MENU, self.OnCopy, self.copy_item)
        self.Bind(wx.EVT_MENU, self.OnPaste, self.paste_item)
        self.Bind(wx.EVT_MENU, self.OnDelete, self.delete_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnSelectAll, self.select_all_item)
        # View 
        self.Bind(wx.EVT_MENU, self.OnZoomIn, self.zoom_in_item)
        self.Bind(wx.EVT_MENU, self.OnZoomOut, self.zoom_out_item)
        self.Bind(wx.EVT_MENU, self.OnZoomRestore, self.zoom_restore_item)
        # --- separator ---
        self.Bind(wx.EVT_MENU, self.OnChangeSplitterOrientation, change_splitter_orientation)
        # Layout
        self.Bind(wx.EVT_MENU, self.OnKKLayout, self.automatic_layout_item)
        # Analysis
        self.Bind(wx.EVT_MENU, self.OnReachabilityGraph, self.reachability_graph_item)
        
        # Bind close
        self.Bind(wx.EVT_CLOSE, self.OnQuit)
        # Button bitmaps
        bmp_mouse = wx.Bitmap("assets/icons/arrow.png", wx.BITMAP_TYPE_ANY)
        bmp_animate = wx.Bitmap("assets/icons/animate.png", wx.BITMAP_TYPE_ANY)
        bmp_newplace = wx.Bitmap("assets/icons/addplace.png", wx.BITMAP_TYPE_ANY)
        bmp_newtransition = wx.Bitmap("assets/icons/addtransition.png", wx.BITMAP_TYPE_ANY)
        bmp_newarc = wx.Bitmap("assets/icons/addarc.png", wx.BITMAP_TYPE_ANY)
        
        mouse_button = wx.lib.buttons.GenBitmapToggleButton(self, bitmap=bmp_mouse)
        
        self.buttons = [(mouse_button, MoveAndSelectStrategy(self.panel_getter)),
                         (wx.lib.buttons.GenBitmapToggleButton(self, bitmap=bmp_animate), SimulateStrategy(self.panel_getter)),
                         (wx.lib.buttons.GenBitmapToggleButton(self, bitmap=bmp_newplace), petrigui.add_object_strategy.AddPlaceStrategy(self.panel_getter)),
                         (wx.lib.buttons.GenBitmapToggleButton(self, bitmap=bmp_newtransition), petrigui.add_object_strategy.AddTransitionStrategy(self.panel_getter)),
                         (wx.lib.buttons.GenBitmapToggleButton(self, bitmap=bmp_newarc), petrigui.add_object_strategy.AddArcStrategy(self.panel_getter)),
                         ]
        
        for button,_ in self.buttons:
            buttons_sizer.Add(button)
            self.Bind(wx.EVT_BUTTON, self.on_toggle_button)
            
        self.buttons = dict(self.buttons)
        
        self.strategy = self.buttons[mouse_button]
            
        self.toggle_button(mouse_button)
            
        vert_sizer.Add(buttons_sizer)
        self.tabs = wx.aui.AuiNotebook(self)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnPageChanged, self.tabs)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnPageClose, self.tabs)
        self._unnamed_count = 0
        self.add_new_page()
        vert_sizer.Add(self.tabs, proportion=1, flag=wx.EXPAND|wx.TOP, border=1)
        self.SetSizer(vert_sizer)
        self.Centre() 
        self.Show()
        
    def OnReachabilityGraph(self, event):        
        from stategraph import graph_frame
        gf = graph_frame.GraphFrame(self, petri_panel=self.petri_panel, title='Reachability graph of %s'%self.petri_panel.GetName())
        gf.Show()
        
    def OnChangeSplitterOrientation(self, event):
        self.splitter_orientation = wx.SPLIT_HORIZONTAL if self.splitter_orientation == wx.SPLIT_VERTICAL \
                                        else wx.SPLIT_VERTICAL
        self.update_splitter_orientation()        
        
    def set_tab_splitter_position(self, position):
        self.tab_splitter_position = position
        
    def OnZoomIn(self, event):
        self.petri_panel.zoom_in()
        
    def OnZoomOut(self, event):
        self.petri_panel.zoom_out()
        
    def OnZoomRestore(self, event):
        self.petri_panel.zoom_restore()
        
    def create_new_panel(self):
        return PetriAndProperties(self.tabs, frame=self, clip_buffer=self.clip_buffer, tab_splitter_position=self.tab_splitter_position)
        #return petrigui.petri_panel.PetriPanel(self.tabs, frame=self, clip_buffer=self.clip_buffer)
        
    def on_state_changed(self):
        self.SetStatusText(str(self.petri_panel.petri.get_state()))
        
    def add_new_page(self):
        petri_panel = self.create_new_panel()
        title = petri_panel.GetName()
        self._unnamed_count += 1
        title = '%s %s'%(title, (str(self._unnamed_count) if self._unnamed_count else ''))
        petri_panel.SetName(title)
        self.tabs.AddPage(petri_panel, petri_panel.petri_panel.get_name(), select=True)
        self.update_menu()
                
    def panel_getter(self):
        return self.current_tab.petri_panel
    
    @property
    def current_tab(self):
        return self.tabs.GetPage(self.tabs.Selection)
    
    petri_panel = property(panel_getter)
        
    def toggle_button(self, button_on):
        button_on.SetValue(True)
        for button in self.buttons:
            if button!=button_on:
                button.SetValue(False)
                
    def on_toggle_button(self, event):
        button_on = event.GetEventObject()
        if not button_on.GetValue(): #can't untoggle 
            button_on.SetValue(True)
            return
        for button in self.buttons:
            if button != button_on:
                button.SetValue(False)
        self.strategy.on_switched_strategy()
        self.strategy = self.buttons[button_on]
        self.update_menu()
        self.petri_panel.SetFocus()
        
    def OnKKLayout(self, event):
        petri = self.petri_panel.petri
        new_petri = petri.__class__.from_json_struct(petri.to_json_struct())
        new_petri.remove_arc_points()
        new_petri.automatic_layout()
        self.add_new_page()
        self.petri_panel.petri = new_petri
        self.petri_panel.update_bounds()
        self.petri_panel.Refresh()
        
    def OnUndo(self, event):
        self.petri_panel.undo()
        self.update_menu()
        
    def OnCut(self, event):
        self.petri_panel.cut()
        self.update_menu()
    
    def OnCopy(self, event):
        self.petri_panel.copy()
        self.update_menu()
    
    def OnPaste(self, event):
        self.petri_panel.paste()
        self.update_menu()
    
    def OnDelete(self, event):
        self.petri_panel.delete()
    
    def OnNew(self, event):
        self.add_new_page()
        
    def OnSelectAll(self, event):
        self.petri_panel.select_all()
        
    def update_menu(self):
        self.refresh_undo_redo()
        if self.tabs.GetPageCount():
            tab_name = self.petri_panel.get_name()
            self.tabs.SetPageText(self.tabs.Selection, tab_name)
            
        
    def refresh_undo_redo(self):
        enable = True
        if self.tabs.GetPageCount()==0:
            enable = False
        self.redo_item.Enable(enable and self.petri_panel.can_redo())
        self.undo_item.Enable(enable and self.petri_panel.can_undo())
        self.paste_item.Enable(enable and not self.clip_buffer.is_empty() and self.petri_panel.can_paste())
        self.cut_item.Enable(enable and self.petri_panel.can_cut() )
        self.copy_item.Enable(enable and self.petri_panel.can_copy() )
        self.delete_item.Enable(enable and self.petri_panel.can_delete())
        self.select_all_item.Enable(enable and self.petri_panel.can_select())
        self.automatic_layout_item.Enable(enable)
        self.close_item.Enable(enable)
        self.save_as_item.Enable(enable)
        self.save_item.Enable(enable and (self.petri_panel.has_unsaved_changes or ( self.petri_panel.filepath is None)))
        
    def OnPageClose(self, event):
        if not self.close_tab(event.Selection):
            event.Veto()
        else:
            wx.CallAfter(self.update_menu)
        
    def OnOpen(self, event):
        self.open(JSONFormat)
        
    def open(self, format):
        dlg = wx.FileDialog(
            self, message="Open file", 
            defaultFile="", wildcard=format.get_wildcard(), style=wx.OPEN
            )
        if dlg.ShowModal() != wx.ID_OK:
            return
        filepath = dlg.GetPath()
        panel = self.create_new_panel()
        try:
            a = time.time()
            panel.petri_panel.load_from_file(filepath, format=format)
            print 'time to load',time.time()-a
        except Exception, e:
            self.DisplayError('Error while loading petri net:\n%s'%traceback.format_exc(), title='Error while opening file')
        else:
            #panel.update_properties()
            self.tabs.AddPage(panel, panel.petri_panel.get_name(), select=True)
        
    def close_tab(self, pos):
        """ Returns false if user decided not to close the tab """
        tab = self.tabs.GetPage(pos)
        if not tab.petri_panel.has_unsaved_changes:
            return True
        dlg = wx.MessageDialog(self, message='There are unsaved changes in "%s". Save?'%tab.petri_panel.GetName(), style=wx.YES_NO|wx.CANCEL|wx.CENTER)
        result = dlg.ShowModal()
        if result == wx.ID_YES:
            tab.save()
        elif result == wx.ID_CANCEL:
            return False
        return True
        
    def OnClose(self, event):
        if self.close_tab(self.tabs.Selection):
            self.tabs.DeletePage(self.tabs.Selection)
        self.update_menu()
            
        
    def DisplayError(self, message, title='Error'):
        wx.MessageBox(message=message, caption=title, style=wx.ICON_ERROR)
        
    def save_as(self, format):
        try:
            self.petri_panel.save_as(format)
        except Exception, e:
            self.DisplayError('Error while saving petri net:\n%s'%traceback.format_exc(), title='Error while saving file')
        self.update_menu()
        
    def OnSave(self, event):
        try:
            self.petri_panel.save(JSONFormat)
        except Exception, e:
            self.DisplayError('Error while saving petri net:\n%s'%traceback.format_exc(), title='Error while saving file')
        self.update_menu()
        
    def OnSaveAs(self, event):
        self.save_as(JSONFormat)
        
    def on_command_append(self):
        self.update_menu()
        
    def OnPageChanged(self, event):
        self.update_menu()
        self.on_state_changed()
        self.petri_panel.SetFocus()
        self.update_splitter_orientation()
        self.current_tab.set_tab_page_number(self.tab_page_number)
        
    def update_splitter_orientation(self):
        tab = self.current_tab
        if tab.GetSplitMode() != self.splitter_orientation:
            tab.SetSplitMode(self.splitter_orientation)
            tab.SendSizeEvent()
        tab.update_splitter_position(self.tab_splitter_position)
        self.Refresh()
        
    def OnRedo(self, event):
        self.petri_panel.redo()
        self.update_menu()
        
    def quit(self):
        page_count = self.tabs.GetPageCount()
        for i in xrange(page_count):
            tab = self.tabs.GetPage(i)
            if not tab.petri_panel.has_unsaved_changes:
                continue
            self.tabs.Selection = i
            if not self.close_tab(i):
                return False
        return True
        
    def OnQuit(self, event):
        if self.quit():
            self.Destroy()
        


if __name__ == '__main__':
    Example(None, 'Petri net editor')
    from util import wx_app
    wx_app.app.MainLoop()
    