


class Command(object): # not just a command, but a command history itself
    """
       Command instance is always the first one
       None <- Command() -> MoveCommand() -> DeleteCommand() -> None
    """
    def __init__(self):
        super(Command, self).__init__()
        self.__prev = None
        self.__next = None
        self.does_nothing = False # sometimes movecommand doens't do anything, so we just won't add commands that don't do anything
        
    def __get_next(self):
        return self.__next
        
    def __set_next(self, next):
        self.__next = next
        
    next = property(fget=__get_next, fset=__set_next)
 
    def __get_prev(self):
        return self.__prev
        
    def __set_prev(self, prev):
        self.__prev = prev     
        
    prev = property(fget=__get_prev, fset=__set_prev)  
        
    def add_command(self, command):
        self.next = command
        self.next.prev = self
        return command
    
    def has_prev(self):
        return self.prev is not None
    
    def has_next(self):
        return self.next is not None
    
    def __str__(self):
        return '<Unnamed command>'

    def go_prev(self):
        if not self.has_prev():
            return self
        self.unexecute()
        return self.prev
    
    def go_next(self):
        if not self.has_next():
            return self
        self.next.execute()
        return self.next

    def execute(self):
        raise NotImplementedError()
    
    def unexecute(self):
        raise NotImplementedError()
