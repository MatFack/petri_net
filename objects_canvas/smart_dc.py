

import wx


class SmartDC(wx.BufferedPaintDC):
    def __init__(self, window, *args, **kwargs):
        self.panel = window
        super(SmartDC, self).__init__(window, *args, **kwargs)
    
    def _update_font_size(self):
        font = self.GetFont()
        new_size = max(6.0, 10*self.panel.zoom)
        font.SetPointSize(new_size)
        self.SetFont(font)
    
    def GetTextExtent(self, text):
        self._update_font_size()
        return super(SmartDC, self).GetTextExtent(text)
    
    def DrawRectangle(self, x, y, width, height):
        lx, ly = x+width, y+height
        x,y = self.panel.canvas_to_screen_coordinates((x,y))
        lx, ly = self.panel.canvas_to_screen_coordinates((lx, ly))
        return super(SmartDC, self).DrawRectangle(x, y, lx-x, ly-y)   
    
    def DrawRectangleOnScreen(self, x, y, width, height):
        return super(SmartDC, self).DrawRectangle(x, y, width, height)   
    
    def DrawLine(self, x1, y1, x2, y2):
        x1, y1 = self.panel.canvas_to_screen_coordinates((x1, y1))
        x2, y2 = self.panel.canvas_to_screen_coordinates((x2, y2))
        return super(SmartDC, self).DrawLine(x1, y1, x2, y2)
    
    def DrawCircle(self, x, y, radius):
        x, y = self.panel.canvas_to_screen_coordinates((x, y))
        radius *= self.panel.zoom
        return super(SmartDC, self).DrawCircle(x, y, radius)
    
    def DrawText(self, text, x, y):
        self._update_font_size()
        x, y = self.panel.canvas_to_screen_coordinates((x, y))
        return super(SmartDC, self).DrawText(text, x, y)
