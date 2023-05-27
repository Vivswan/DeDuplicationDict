from __future__ import annotations

import copy
import pickle
import sys
from collections.abc import MutableMapping
from hashlib import sha256
from typing import Iterator, TypeVar, Union, Dict, Any

if sys.version_info[:2] >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata  # pragma: no cover

__package__ = 'autocachedict'
__author__ = 'Vivswan Shah (vivswanshah@pitt.edu)'

try:
    __version__ = metadata.version(__package__)
except metadata.PackageNotFoundError:
    __version__ = '0.0.0'

if sys.version_info < (3, 7, 0):
    import warnings

    warnings.warn(
        'The installed Python version reached its end-of-life. '
        'Please upgrade to a newer Python version for receiving '
        'further gdshelpers updates.', Warning)

T = TypeVar('T')  # Any type.
KT = TypeVar('KT')  # Key type.
VT = TypeVar('VT')  # Value type.
T_co = TypeVar('T_co', covariant=True)  # Any type covariant containers.
V_co = TypeVar('V_co', covariant=True)  # Any type covariant containers.
VT_co = TypeVar('VT_co', covariant=True)  # Value type covariant containers.


class AutoCacheDict(MutableMapping):
    hash_length = 8

    def __init__(self, *args, _value_dict: dict = None, **kwargs):
        self.key_dict: Dict[str, Union[str, AutoCacheDict]] = {}
        self.value_dict: Dict[str, Any] = {} if _value_dict is None else _value_dict
        self.auto_clean_up = True

        for k, v in dict(*args, **kwargs).items():
            self[k] = v

    def _set_value_dict(self, value_dict: dict) -> None:
        value_dict.update(self.value_dict)
        self.value_dict = value_dict
        for k, v in self.key_dict.items():
            if isinstance(v, str):
                continue

            v._set_value_dict(value_dict)

    def __setitem__(self, key: KT, value: VT) -> None:
        if key in self.key_dict:
            del self[key]

        if isinstance(value, dict):
            self.key_dict[key] = AutoCacheDict(value, _value_dict=self.value_dict)
        elif isinstance(value, AutoCacheDict):
            self.key_dict[key] = value
            value._set_value_dict(self.value_dict)
        else:
            hash_id = sha256(pickle.dumps(value)).hexdigest()[:self.hash_length]
            self.key_dict[key] = hash_id
            self.value_dict[hash_id] = value

    def __getitem__(self, key: KT) -> VT_co:
        if key not in self.key_dict:
            raise KeyError(key)

        v = self.key_dict[key]
        if isinstance(v, (AutoCacheDict, self.__class__)):
            return v

        if isinstance(v, str):
            return self.value_dict[v]

        raise TypeError(f"WTF? {type(v)}")

    def all_hashes_in_use(self) -> set:
        all_hashes_in_use = set()
        for v in self.key_dict.values():
            if isinstance(v, str):
                all_hashes_in_use.add(v)
            else:
                all_hashes_in_use.update(v.all_hashes_in_use())
        return all_hashes_in_use

    def clean_up(self) -> None:
        all_hashes_in_use = self.all_hashes_in_use()
        all_hashes = set(self.value_dict.keys())
        not_in_use = all_hashes - all_hashes_in_use
        for hash_id in not_in_use:
            del self.value_dict[hash_id]

    def detach(self) -> AutoCacheDict:
        return self.from_cache_dict(self.to_cache_dict())

    def _del_detach(self) -> None:
        self._set_value_dict({})
        self.clean_up()

        for k, v in self.value_dict.items():
            self.value_dict[k] = copy.deepcopy(v)

    def __delitem__(self, key: KT) -> None:
        if key not in self.key_dict:
            raise KeyError(key)

        v = self.key_dict[key]
        del self.key_dict[key]
        if isinstance(v, (AutoCacheDict, self.__class__)):
            v._del_detach()

        if self.auto_clean_up:
            self.clean_up()

    def __len__(self) -> int:
        return len(self.key_dict)

    def __iter__(self) -> Iterator[T_co]:
        return iter(self.key_dict)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} [{len(self.key_dict)}:{len(self.value_dict)}]"

    def to_dict(self) -> dict:
        return {k: v.to_dict() if isinstance(v, AutoCacheDict) else v for k, v in self.items()}

    @classmethod
    def from_dict(cls, d: dict) -> AutoCacheDict:
        return cls(**d)

    def _get_key_dict(self) -> dict:
        return {k: v._get_key_dict() if isinstance(v, AutoCacheDict) else v for k, v in self.key_dict.items()}

    def to_cache_dict(self) -> dict:
        return {
            'key_dict': self._get_key_dict(),
            'value_dict': self.value_dict
        }

    @classmethod
    def from_cache_dict(cls, d: dict, _v: dict = None) -> AutoCacheDict:
        if _v is None:
            return cls.from_cache_dict(d['key_dict'], _v=d['value_dict'])

        new_dict = cls()
        new_dict.key_dict = {}
        new_dict.value_dict = _v

        for k, v in d.items():
            if isinstance(v, dict):
                new_dict.key_dict[k] = cls.from_cache_dict(v, _v=_v)
            else:
                new_dict.key_dict[k] = v

        return new_dict
