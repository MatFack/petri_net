
import collections
from command import Command

class CreateDeleteObjectCommand(Command):
    """
    Create command does not create anything, it just removes and deletes dependencies, leaving objects in memory
    """
    def __init__(self, panel, obj=None, move_strategy=None, to_delete=False):
        super(CreateDeleteObjectCommand, self).__init__()
        self.to_delete = to_delete
        self.move_strategy = move_strategy
        self.panel = panel
        self.objects = collections.deque()
        if obj is not None:
            self.add_object(obj)
        
    def add_object(self, obj):
        self.objects.append([obj, obj.is_selected])
        
    def execute(self):
        if self.to_delete:
            self._unexecute()
        else:
            self._execute()
        
    def unexecute(self):
        if self.to_delete:
            self._execute()
        else:
            self._unexecute()
        
    def _execute(self):
        for obj, is_selected in self.objects:
            obj.restore()
            if self.move_strategy is not None and is_selected:
                self.move_strategy.add_to_selection(obj)
        for obj, is_selected in self.objects:
            obj.post_restore()
        
    def _unexecute(self):
        for obj, _ in self.objects:
            obj.prepare_to_delete()
        for obj, _ in self.objects:
            obj.delete()
        