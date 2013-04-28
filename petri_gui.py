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


# Well, and after paper shit, splitting into chunks and drawing only visible chunks. Later. Fuck paper shit.

from objects_canvas.strategy import Strategy
from objects_canvas.move_strategy import MoveAndSelectStrategy

import json
from petri import petri
import wx
import wx.aui
import wx.lib.buttons
import petrigui.add_object_strategy
import petrigui.petri_objects
import petrigui.petri_panel


    
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
                print self.panel.petri.get_state()

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


class Example(wx.Frame):
    def __init__(self, parent, title):
        super(Example, self).__init__(parent, title=title, 
            size=(500, 500))
        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.clip_buffer = Buffer()
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
        menubar.Append(viewMenu, '&View')
        layoutMenu = wx.Menu()
        self.automatic_layout_item = layoutMenu.Append(wx.NewId(), '&Automatic layout', 'Automatic layout of current net')
        menubar.Append(layoutMenu, '&Layout')
        #analysisMenu = wx.Menu()
        
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
        # Layout
        self.Bind(wx.EVT_MENU, self.OnKKLayout, self.automatic_layout_item)
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
        
    def OnZoomIn(self, event):
        self.petri_panel.zoom_in()
        
    def OnZoomOut(self, event):
        self.petri_panel.zoom_out()
        
    def OnZoomRestore(self, event):
        self.petri_panel.zoom_restore()
        
    def create_new_panel(self):
        return petrigui.petri_panel.PetriPanel(self.tabs, frame=self, clip_buffer=self.clip_buffer)
        
    def add_new_page(self):
        petri_panel = self.create_new_panel()
        title = petri_panel.GetName()
        self._unnamed_count += 1
        title = '%s %s'%(title, (str(self._unnamed_count) if self._unnamed_count else ''))
        petri_panel.SetName(title)
        self.tabs.AddPage(petri_panel, petri_panel.get_name(), select=True)
        self.update_menu()
                
    def panel_getter(self):
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
            panel.load_from_file(filepath, format=format)
        except Exception, e:
            self.DisplayError('Error while loading petri net:\n%s'%traceback.format_exc(), title='Error while opening file')
        else:
            self.tabs.AddPage(panel, panel.get_name(), select=True)
        
    def close_tab(self, pos):
        """ Returns false if user decided not to close the tab """
        tab = self.tabs.GetPage(pos)
        if not tab.has_unsaved_changes:
            return True
        dlg = wx.MessageDialog(self, message='There are unsaved changes in "%s". Save?'%tab.GetName(), style=wx.YES_NO|wx.CANCEL|wx.CENTER)
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
        
    def OnPageChanged(self, event):
        self.update_menu()
        self.petri_panel.SetFocus()
        
    def OnRedo(self, event):
        self.petri_panel.redo()
        self.update_menu()
        
    def quit(self):
        page_count = self.tabs.GetPageCount()
        for i in xrange(page_count):
            tab = self.tabs.GetPage(i)
            if not tab.has_unsaved_changes:
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
    