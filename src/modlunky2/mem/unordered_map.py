from dataclasses import dataclass
from struct import pack, unpack, calcsize
from typing import ClassVar, TYPE_CHECKING

import fnvhash

if TYPE_CHECKING:
    from . import Spel2Process


@dataclass
class UnorderedMapMeta:
    SIZE: ClassVar[int] = 64

    # Terminal address for Node linked list
    end: int
    size: int
    buckets_ptr: int
    mask: int
    bucket_size: int

    @classmethod
    def from_offset(cls, proc, offset):
        data = proc.read_memory(offset, cls.SIZE)

        end = unpack("<Q", data[8 : 8 + 8])[0]
        size = unpack("<Q", data[16 : 16 + 8])[0]
        buckets_ptr = unpack("P", data[24 : 24 + 8])[0]
        mask = unpack("<Q", data[48 : 48 + 8])[0]
        bucket_size = unpack("<Q", data[56 : 56 + 8])[0]

        return cls(end, size, buckets_ptr, mask, bucket_size)


@dataclass
class Bucket:
    SIZE: ClassVar[int] = 16
    first: int
    last: int

    @classmethod
    def from_offset(cls, proc, offset):
        data = proc.read_memory(offset, cls.SIZE)

        first = unpack("P", data[0 : 0 + 8])[0]
        last = unpack("P", data[8 : 8 + 8])[0]
        return cls(first, last)


@dataclass
class Node:

    SIZE: ClassVar[int] = 32

    next: int
    prev: int
    key: int
    value: int

    @classmethod
    def from_offset(cls, proc, offset, key_char, value_char) -> "Node":
        key_size = calcsize(key_char)
        value_size = calcsize(value_char)
        data = proc.read_memory(offset, cls.SIZE)
        if data is None:
            return None

        next_ = unpack("P", data[0 : 0 + 8])[0]
        prev = unpack("P", data[8 : 8 + 8])[0]
        key = unpack(key_char, data[16 : 16 + key_size])[0]
        # key + 8 regardless of keysize because of padding
        value = unpack(value_char, data[24 : 24 + value_size])[0]

        return Node(next_, prev, key, value)


class UnorderedMap:
    KEY_CHAR = "<Q"
    VALUE_CHAR = "P"

    def __init__(self, proc, offset):
        self._proc: "Spel2Process" = proc
        self._offset = offset

    def _get_meta(self) -> UnorderedMapMeta:
        return UnorderedMapMeta.from_offset(self._proc, self._offset)

    def get_node(self, offset):
        return Node.from_offset(self._proc, offset, self.KEY_CHAR, self.VALUE_CHAR)

    def get(self, key, meta: UnorderedMapMeta = None):
        if meta is None:
            meta = self._get_meta()

        bucket = self.get_bucket(key, meta)

        # Empty bucket
        if bucket.first == meta.end:
            return None

        next_ = bucket.first
        while True:
            node = self.get_node(next_)
            if node is None:
                return None

            # Found key!
            if node.key == key:
                return node.value

            # We've searched the final bucket. give up...
            if next_ == bucket.last:
                return None

            next_ = node.next

    def get_bucket(self, key, meta: UnorderedMapMeta = None) -> Bucket:
        if meta is None:
            meta = self._get_meta()
        idx = self._get_bucket_idx(key, meta)
        offset = meta.buckets_ptr + (idx * Bucket.SIZE)
        return Bucket.from_offset(self._proc, offset)

    def _hash_key(self, key) -> int:
        bytes_ = pack(self.KEY_CHAR, key)
        return fnvhash.fnv1a_64(bytes_)

    def _get_bucket_idx(self, key, meta: UnorderedMapMeta = None) -> int:
        if meta is None:
            meta = self._get_meta()
        return self._hash_key(key) & meta.mask
