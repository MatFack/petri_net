# -*- coding: utf-8 -*-

import wx

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