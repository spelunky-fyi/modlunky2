# Per PEP 594, the chunk module is deprecated in Python 3.11.
# It must be replaced by Python 3.12's EoL (ETA Oct 2028)
from chunk import Chunk  # pylint: disable=deprecated-module


class RIFFChunk(Chunk):
    def __init__(self, f):
        super().__init__(f, align=True, bigendian=False)
        self.skip()
        self.end = self.tell() + self.offset
        self.seek(0)
        self.children = None
        self.type = None

    def populate_children(self):
        children = []
        while self.file.tell() < self.end:
            chunk = RIFFChunk(self.file)
            if chunk.getname() == b"LIST":
                chunk.type = chunk.read(4)
                chunk.populate_children()
            chunk.seek(0)
            chunk.skip()
            children.append(chunk)
        self.children = children

    def __repr__(self):
        return "<%s %r with %s children>" % (
            self.__class__.__name__,
            self.getname(),
            "no" if self.children is None else len(self.children),
        )


class RIFF(RIFFChunk):
    def __init__(self, f):
        super().__init__(f)

        assert self.getname() == b"RIFF"
        self.seek(0)
        self.type = self.read(4)
        self.populate_children()

    def save(self):
        pass
