

from command import Command
import collections


class ChangePropertiesCommand(Command):
    def __init__(self, panel, obj):
        super(ChangePropertiesCommand, self).__init__()
        self.panel = panel
        self.obj = obj
        self.properties = collections.deque()
    
    def update_field_value(self, field, fr, to):
        if fr == to:
            return
        self.does_nothing = False
        self.properties.append((field, fr, to))
        
    def execute(self):
        self._change_properties()
        
    def unexecute(self):
        self._change_properties(backward=True)
            
    def _change_properties(self, backward=False):
        for field, fr, to in self.properties:
            if backward:
                fr, to = to, fr
            updater = getattr(self.obj, 'update_'+field, None)
            if updater is not None:
                updater(to)
            else:
                setattr(self.obj, field, to)   