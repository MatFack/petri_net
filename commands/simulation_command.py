


from collections import deque
from command import Command


class SimulationCommand(Command):
    def __init__(self, panel, transition):
        super(SimulationCommand, self).__init__()
        self.panel = panel
        self.transition = transition
        
    def __str__(self):
        return 'Fire %s'%self.transition.unique_id
        
    def execute(self):
        self.transition.fire()
        self.panel.Refresh()
            
    def unexecute(self):
        self.transition.unfire()
        self.panel.Refresh()