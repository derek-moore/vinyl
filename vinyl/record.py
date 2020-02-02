from collections import OrderedDict
import logging
from vinyl.fields import BaseField


log = logging.getLogger('vinyl')


class RecordMetaclass(type):
    def __new__(mcs, class_name, bases, dct):
        base_fields = OrderedDict()
        for base in bases:
            if hasattr(base, '_fields'):
                base_fields.update(base._fields)
        fields = OrderedDict()
        fields.update(base_fields)
        unordered = [(name.lower(), value) for name, value in dct.items() if isinstance(value, BaseField)]
        for item in sorted(unordered, key=lambda x: x[1].created_order):
            fields.__setitem__(*item)

        special = dict((name, value) for name, value in dct.items() if not isinstance(value, BaseField))

        obj = super(RecordMetaclass, mcs).__new__(mcs, class_name, bases, special)
        obj._fields = fields

        # set the field name on each field
        for item in fields.items():
            setattr(item[1], 'field_name', item[0])

        return obj


class Record(object, metaclass=RecordMetaclass):
    """
    A mutable record type. Write classes describing the data declaratively,
    but have all the ease-of-use that namedtuple provides. Except that the keys
    are case-insensitive, and the type is mutable (useful for converting formats).
    """

    def __init__(self, *args, **kw):
        super(Record, self).__init__()

        # make instance variables out of all the fields
        set_attr = super(Record, self).__setattr__
        for item in list(self._fields.values()):
            set_attr(item.field_name, item.value)

        self._load(*args, **kw)

    def _load(self, *args, **kw):
        """
        Instantiating this class is expensive. Use this method to load
        new data in to an existing instance.

        Note that it doesn't empty any existing values, so take
        care to set all the fields in this Record to a new value.
        """
        index = 0
        value = None
        try:
            for index, value in enumerate(args):
                self.__setitem__(index, value)
        except IndexError:
            log.error('{0}: IndexError setting index {1} with value: "{2}"'.format(
                self.__class__.__name__, index, value))
            raise

        for k, v in kw.items():
            if k.lower() not in self._fields:
                raise AttributeError('Unknown field {0}'.format(k))
            self.__setattr__(k, v)

    def _validate(self):
        for item in list(self._fields.values()):
            item.validate()

    def __len__(self):
        return len(self._fields)

    def __getitem__(self, index):
        key = list(self._fields.keys())[index]
        return self.__getattr__(key)

    def __setitem__(self, index, value):
        key = list(self._fields.keys())[index]
        return self.__setattr__(key, value)

    def __setattr__(self, key, value):
        key = key.lower()
        field = self._fields[key]
        return super(Record, self).__setattr__(key, field.to_record(value))

    def __getattr__(self, key):
        return super(Record, self).__getattribute__(key.lower())

    def __iter__(self):
        for name in self._fields.keys():
            yield getattr(self, name)

    def __repr__(self):
        return '{0}({1})'.format(
            self.__class__.__name__,
            ', '.join(["{0}={1}".format(x, getattr(self, x)) for x in list(self._fields.keys())]),
        )

    def __delattr__(self, name):
        raise NotImplementedError('Cannot delete attributes')
