from dataclasses import InitVar, dataclass
import dataclasses
import logging
from typing import ClassVar, Optional

from modlunky2.mem.entities import Entity
from modlunky2.mem.memrauder.model import (
    DataclassStruct,
    FieldPath,
    MemContext,
    MemType,
    PolyPointer,
    PolyPointerType,
)
from modlunky2.mem.memrauder.dsl import (
    dc_struct,
    struct_field,
    sc_uint32,
    sc_void_p,
    sc_uint64,
)

logger = logging.getLogger("modlunky2")


@dataclass(frozen=True)
class _RobinHoodTableMeta:
    mask: int = struct_field(0x0, sc_uint64)
    table_ptr: int = struct_field(0x8, sc_void_p)


@dataclass(frozen=True)
class _RobinHoodTableEntry:
    uid_plus1: int = struct_field(0x0, sc_uint32)
    # We intentionally don't use PolyPointer, to defer reading the Entity until
    # we know we have the right entry.
    entity_addr: int = struct_field(0x8, sc_void_p)

    SIZE: ClassVar[int] = 16


@dataclass(frozen=True)
class UidEntityMap:
    meta: _RobinHoodTableMeta
    table_entry_mem_type: MemType[_RobinHoodTableEntry]
    mem_ctx: MemContext

    empty_poly: PolyPointer[Entity] = dataclasses.field(init=False)

    def __post_init__(self):
        if self.meta.mask < 1:
            raise ValueError(f"invalid mask value {self.meta.mask}")

        empty_poly = PolyPointer.make_empty(self.mem_ctx)

        object.__setattr__(self, "empty_poly", empty_poly)

    def _get_table_entry(self, index: int) -> Optional[_RobinHoodTableEntry]:
        entry_size = _RobinHoodTableEntry.SIZE

        entry_addr = self.meta.table_ptr + index * entry_size
        entry_buf = self.mem_ctx.mem_reader.read(entry_addr, entry_size)
        if entry_buf is None:
            return None

        try:
            return self.table_entry_mem_type.from_bytes(entry_buf, self.mem_ctx)
        except Exception as err:
            raise ValueError(
                f"failed to get table index {index} at {entry_addr:x}"
            ) from err

    def _get_addr(self, uid):
        target_uid_plus1 = uid + 1

        cur_index = target_uid_plus1 & self.meta.mask
        while True:
            entry = self._get_table_entry(cur_index)
            if entry is None:
                # Reading the bytes for the entry failed.
                return 0

            if entry.uid_plus1 == target_uid_plus1:
                return entry.entity_addr

            if entry.uid_plus1 == 0:
                # We found an 'empty' entry before our target. It must not exist.
                return 0

            mask = self.meta.mask
            if (target_uid_plus1 & mask) > (entry.uid_plus1 & mask):
                # We've found an entry that, if the target existed, would be further away than our target.
                # The target must not exist.
                return 0

            cur_index = (cur_index + 1) & self.meta.mask
        # The above loop only terminates via return

    def check_lookup(self):
        checked_count = 0
        non_empty_count = 0
        requires_probe_count = 0
        mismatch_count = 0
        for index in range(0, self.meta.mask + 1):
            entry = self._get_table_entry(index)
            if entry is None:
                # Reading the bytes for the entry failed.
                continue
            checked_count += 1

            if entry.uid_plus1 == 0:
                continue
            non_empty_count += 1

            if entry.uid_plus1 == index:
                # _get_addr() isn't worth exercising
                continue
            requires_probe_count += 1

            get_addr_result = self._get_addr(entry.uid_plus1 - 1)
            if entry.entity_addr == get_addr_result:
                continue
            mismatch_count += 1
            logger.warning("Mismatch for index %d (uid %d). Expected %X, got %X")

        # Make status more prominent if we exercised non-trivial cases
        if requires_probe_count:
            logger.info(
                "Checked uid-entity mapping: Checked %d, Non-empty %d, Requires probe %d, Mismatch %d",
                checked_count,
                non_empty_count,
                requires_probe_count,
                mismatch_count,
            )

    def get(self, uid: int) -> PolyPointer[Entity]:
        if self.meta.table_ptr == 0:
            return self.empty_poly

        addr = self._get_addr(uid)
        if addr == 0:
            return self.empty_poly

        entity = self.mem_ctx.type_at_addr(Entity, addr)
        if entity is None:
            return self.empty_poly

        return PolyPointer(addr, entity, self.mem_ctx)


@dataclass(frozen=True)
class UidEntityMapType(MemType[UidEntityMap]):
    path: InitVar[FieldPath]
    py_type: InitVar[type]

    meta_mem_type: MemType[_RobinHoodTableMeta] = dataclasses.field(init=False)
    table_entry_mem_type: MemType[_RobinHoodTableEntry] = dataclasses.field(init=False)

    def __post_init__(self, path, py_type):
        if py_type is not UidEntityMap:
            raise ValueError(f"field {path} must be UnorderedMap, got {py_type}")

        meta_mem_type = DataclassStruct(path, _RobinHoodTableMeta)
        poly_entity_mem_type = PolyPointerType(path, PolyPointer[Entity], dc_struct)
        table_entry_mem_type = DataclassStruct(path, _RobinHoodTableEntry)

        object.__setattr__(self, "meta_mem_type", meta_mem_type)
        object.__setattr__(self, "poly_entity_mem_type", poly_entity_mem_type)
        object.__setattr__(self, "table_entry_mem_type", table_entry_mem_type)

    def field_size(self) -> int:
        return self.meta_mem_type.field_size()

    def element_size(self) -> int:
        return self.meta_mem_type.element_size()

    def from_bytes(self, buf: bytes, mem_ctx: MemContext) -> UidEntityMap:
        meta = self.meta_mem_type.from_bytes(buf, mem_ctx)
        try:
            return UidEntityMap(meta, self.table_entry_mem_type, mem_ctx)
        except Exception as err:
            raise ValueError("failed to construct map for field {self.path}") from err


def uid_entity_map(path: FieldPath, py_type: type):
    return UidEntityMapType(path, py_type)
