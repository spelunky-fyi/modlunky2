import logging
import json


from .constants import NOT_PRESENT

logger = logging.getLogger("modlunky2")


class Field:
    DEFAULT_VALUE = None
    NAME = NOT_PRESENT
    PERSIST_DEFAULT = False

    def __init__(self, initial_value=NOT_PRESENT):
        if self.NAME is NOT_PRESENT:
            raise NotImplementedError("NAME attribute missing...")

        self._value = (
            self.get_default_value() if initial_value is NOT_PRESENT else initial_value
        )
        self._dirty = False

    @classmethod
    def get_default_value(cls):
        """Gets the default value when instantiating a field.

        This is also used for determining whether to serialize a field.
        """
        return cls.DEFAULT_VALUE

    def __call__(self, value=None):
        self._value = value
        self._dirty = True

    def get(self):
        return self._value

    @classmethod
    def from_data(cls, data):
        return cls(data.get(cls.NAME, NOT_PRESENT))

    def to_data(self, data):
        default = self.get_default_value()
        if default == self._value and not self.PERSIST_DEFAULT:
            return
        data[self.NAME] = self._value

    def clean(self):
        self._dirty = False


class ConfigObj:
    

class ColorKey(Field):
    DEFAULT_VALUE = "#ff00ff"
    NAME = "color-key"

