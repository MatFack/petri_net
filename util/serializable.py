
from collections import defaultdict

class RequiredException(Exception):
    """
    Raised when class needs more parameters to deserialize (msg=param_name)
    """
    
class DoNotSerialize(Exception):
    """
    Raised when field isn't required to be serialized. Raised by '_to_json_struct' methods
    """

class MetaSerializable(type):
    TO_SUFFIX =   '_to_json_struct'
    FROM_SUFFIX = '_from_json_struct'
    JUST_SERIALIZE = '_to_serialize'
    SERIALIZATION_FIELD = '_serialization_fields'
    ADDITIONAL_FIELS_FIELD = 'TO_SERIALIZE'
    def __new__(self, cls_name, parents, dct):
        fields = defaultdict(lambda:{})
        for parent in parents:
            parent_fields = getattr(parent, MetaSerializable.SERIALIZATION_FIELD, {})
            fields.update(parent_fields)
        for field_name in dct:
            suf = None
            for suffix in [MetaSerializable.TO_SUFFIX, MetaSerializable.FROM_SUFFIX, MetaSerializable.JUST_SERIALIZE]:
                if field_name.endswith(suffix):
                    suf = suffix
                    break
            else:
                continue
            field = field_name.rsplit(suf)[0]
            fields[field][suf] = field_name
        to_serialize = dct.get(MetaSerializable.ADDITIONAL_FIELS_FIELD, [])
        for field_name in to_serialize:
            fields[field_name] = {}
        if not MetaSerializable.SERIALIZATION_FIELD in dct:
            dct[MetaSerializable.SERIALIZATION_FIELD] = {}
        dct.setdefault(MetaSerializable.SERIALIZATION_FIELD, {}).update(fields)
        return super(MetaSerializable, self).__new__(self, cls_name, parents, dct)
        
class Serializable(object):
    __metaclass__ = MetaSerializable
    
    def to_json_struct(self, **kwargs):
        obj = {}
        fields_dct = getattr(self, self.__metaclass__.SERIALIZATION_FIELD)
        for field, functions in fields_dct.iteritems():
            serializer_field = functions.get(self.__metaclass__.TO_SUFFIX)
            if serializer_field:
                serializer = getattr(self, serializer_field)
                try:
                    value = serializer(**kwargs)
                except DoNotSerialize:
                    continue
                else:
                    obj[field] = value
            else:
                obj[field] = getattr(self, field)
        return obj
    
    @classmethod
    def from_json_struct(cls, obj, constructor_args=None, **kwargs):
        fields_dct = getattr(cls, cls.__metaclass__.SERIALIZATION_FIELD)
        if constructor_args:
            result = cls(**constructor_args)
        else:
            result = cls()
        fields_values = {}
        iterated = True
        while iterated:
            iterated = False
            for field, functions in fields_dct.iteritems():
                if field in fields_values:
                    continue
                iterated = True
                obj_field_value = obj[field]
                deserializer_field = functions.get(cls.__metaclass__.FROM_SUFFIX)
                # If there is a function to deserialize value, call it, otherwise just assign the value. 
                if deserializer_field:
                    deserializer = getattr(result, deserializer_field)
                    try:
                        field_value = deserializer(obj_field_value, **kwargs)
                    except RequiredException:
                        continue
                else:
                    field_value = obj_field_value
                fields_values[field] = field_value
                setattr(result, field, field_value)
        return result
    
class Trans(Serializable):
    
    def __init__(self, x=1, s='FF'):
        self.x = x
        self.s = s
    
    def x_to_json_struct(self):
        return 1
    
    def x_from_json_struct(self, obj, **kwargs):
        return [obj]


if __name__ == '__main__':    
    t = Trans(1, 'ABA')
    
    j = t.to_json_struct()
    
    m = Trans.from_json_struct(j, {},a=2)
    
    print m.x
    print m.s
