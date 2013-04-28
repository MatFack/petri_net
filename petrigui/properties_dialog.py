# -*- coding: utf-8 -*-

import wx
import collections
from commands.change_properties_command import ChangePropertiesCommand


class ElementPropertiesDialog(wx.Dialog):
    def __init__(self, parent, window_id, title, obj, fields):
        self.parent = parent
        self.fields = collections.OrderedDict()
        for field, value in fields:
            self.fields[field] = value
        self.obj = obj
        super(ElementPropertiesDialog, self).__init__(parent, window_id, title)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.result = {} #
        
        sb = wx.StaticBox(self, label=title)
        sbs = wx.StaticBoxSizer(sb, orient=wx.VERTICAL)
        self.InitUI(sbs)

        sizer.Add(sbs, border=5, proportion=1, flag=wx.ALL|wx.EXPAND)
        
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        okButton = wx.Button(self, wx.ID_OK, label='Ok')
        closeButton = wx.Button(self, wx.ID_CANCEL, label='Cancel')
        hbox2.Add(okButton)
        hbox2.Add(closeButton, flag=wx.LEFT, border=5)
        sizer.Add(hbox2, 
            flag=wx.ALIGN_CENTER|wx.TOP|wx.BOTTOM, border=10)
        
        okButton.Bind(wx.EVT_BUTTON, self.OnOk)
        closeButton.Bind(wx.EVT_BUTTON, self.OnCancel)
        
        
        self.SetSizer(sizer)
        self.Fit()
    
        
    def OnOk(self, event):
        if self.check_values():
            self.UpdateObjectValues()
            self.Destroy()
            self.SetReturnCode(wx.ID_CANCEL)
            
    OnTextEnter = OnOk
        
    def check_values(self):
        for field_name, (label, getter, setter) in self.fields.iteritems():
            control = self.field_controls[field_name]
            value = setter(control)
            self.result[field_name] = value
            if getattr(self.obj, field_name, None) == value:
                continue
            checker = getattr(self.obj, 'check_update_'+field_name, None)
            if checker:
                try:
                    checker(value)
                except Exception, e:
                    error = getattr(e,'message','')
                    error = '\n'+error if error else error
                    wx.MessageBox("Incorrect value for field %s.%s"%(field_name, error))
                    return False
        return True
        
    def UpdateObjectValues(self):
        command = ChangePropertiesCommand(self.parent, self.obj)
        for field, value in self.result.iteritems():
            command.update_field_value(field, getattr(self.obj, field, None), value)
        if not command.does_nothing:
            command.execute()
            self.parent.append_command(command)
        
    def OnCancel(self, event):
        self.Destroy()
        self.SetReturnCode(wx.ID_CANCEL)
        
    def InitUI(self, sizer):
        self.field_controls = {}
        for field_name, (label, getter, setter) in self.fields.iteritems():
            value = getattr(self.obj, field_name, '')
            self.result[field_name] = value
            hbox1 = wx.BoxSizer(wx.HORIZONTAL)
            hbox1.Add(wx.StaticText(self, label=label))
            control = getter(self, value)
            self.Bind(wx.EVT_TEXT_ENTER, self.OnTextEnter)
            hbox1.Add(control, flag=wx.LEFT, border=5, )
            self.field_controls[field_name] = control
            sizer.Add(hbox1)



def spin_control(parent, value, rng):
    control = wx.SpinCtrl(parent, style=wx.TE_PROCESS_ENTER)
    control.SetRange(*rng)
    control.SetValue(int(value))
    return control


def place_ranged(label, minimum=None, maximum=None):
    if minimum is None:
        minimum = -(1<<31)
    if maximum is None:
        maximum = 1<<31-1
    def control_maker(parent, value):
        return spin_control(parent, value, (minimum, maximum))
    def control_getter(control):
        return int(control.GetValue())
    return label, control_maker, control_getter
        

class DialogFields(object): 
    unique_id = ('Name', lambda parent,value:wx.TextCtrl(parent, value=value, style=wx.TE_PROCESS_ENTER), lambda control:str(control.GetValue()))