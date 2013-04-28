

import wxversion
wxversion.ensureMinimal('2.8')
import networkx as nx
import matplotlib

matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas

from matplotlib.backends.backend_wx import NavigationToolbar2Wx
from matplotlib import pyplot
from matplotlib.figure import Figure

import wx



class CanvasFrame(wx.Frame):

  def __init__(self):
    wx.Frame.__init__(self,None,-1,
                     'CanvasFrame',size=(550,350))

    self.SetBackgroundColour(wx.NamedColor("WHITE"))

    self.figure = Figure()
    self.axes = self.figure.add_subplot(111)

    self.canvas = FigureCanvas(self, -1, self.figure)
    print dir(self.canvas)
    self.sizer = wx.BoxSizer(wx.VERTICAL)
    self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
    self.SetSizer(self.sizer)
    self.Fit()
    G = nx.Graph()
    G.add_edge(1,3,weight = 5)
    G.add_edge(1,2,weight = 4)
    import random 
    for i in xrange(100):
        G.add_edge(random.randrange(100),random.randrange(100))  

    pos = nx.spring_layout(G)    
    nx.draw(G, pos)
    pyplot.show()
    #nx.draw_networkx(G, pos, ax=self.axes)
    #edge_labels=dict([((u,v,),d['weight'])
    #     for u,v,d in G.edges(data=True)])
    nx.draw_networkx_edge_labels(G,pos,edge_labels=edge_labels)
class App(wx.App):

  def OnInit(self):
    'Create the main window and insert the custom frame'
    frame = CanvasFrame()
    frame.Show(True)

    return True

app = App(0)
app.MainLoop()