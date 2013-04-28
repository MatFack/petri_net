

from collections import deque
from command import Command


class MoveCommand(Command):
    def __init__(self, panel):
        super(MoveCommand, self).__init__()
        self.panel = panel
        self.objects = deque()
        
    def __str__(self):
        return 'Move %d object'%len(self.objects)
        
    def add_object(self, obj):
        self.objects.append([obj, obj.get_position(), None])
        
    def record_move(self):
        self.does_nothing = True
        for lst in self.objects:
            lst[-1] = lst[0].get_position()
            if lst[1] != lst[2]:
                self.does_nothing = False

    def execute(self):
        for obj, pos_before, pos_after in self.objects:
            obj.set_position(*pos_after)
        self.panel.update_bounds()
            
    def unexecute(self):
        for obj, pos_before, pos_after in self.objects:
            obj.set_position(*pos_before)
        self.panel.update_bounds()