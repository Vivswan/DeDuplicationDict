from __future__ import annotations

import copy
import pickle
import sys
from collections.abc import MutableMapping
from hashlib import sha256
from typing import Iterator, TypeVar, Union, Dict, Any

__all__ = ['__package__', '__author__', '__version__', 'DeDuplicationDict']

if sys.version_info[:2] >= (3, 8):
    from importlib import metadata
else:
    import importlib_metadata as metadata  # pragma: no cover

__package__ = 'deduplicationdict'
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

KT = TypeVar('KT')  # Key type.
VT = TypeVar('VT')  # Value type.
T_co = TypeVar('T_co', covariant=True)  # Any type covariant containers.
VT_co = TypeVar('VT_co', covariant=True)  # Value type covariant containers.


class DeDuplicationDict(MutableMapping):
    """A dictionary that de-duplicates values.

    A dictionary-like class that deduplicates values by storing them in a separate dictionary and replacing
    them with their corresponding hash values. This class is particularly useful for large dictionaries with
    repetitive entries, as it can save memory by storing values only once and substituting recurring values
    with their hash representations.

    This class supports nested structures by automatically converting nested dictionaries into
    DeDuplicationDict instances. It also provides various conversion methods to convert between regular
    dictionaries and DeDuplicationDict instances.

    Attributes:
        hash_length (int): The length of the hash value used for deduplication.
        auto_clean_up (bool): Whether to automatically clean up unused hash values when deleting items.
    """

    hash_length: int = 8
    auto_clean_up: bool = True

    def __init__(self, *args, _value_dict: dict = None, **kwargs):
        """Initialize a DeDuplicationDict instance.

        Args:
            *args: Positional arguments passed to the dict constructor.
            _value_dict (dict, optional): An existing value dictionary to use for deduplication.
            **kwargs: Keyword arguments passed to the dict constructor.
        """

        self.key_dict: Dict[str, Union[str, DeDuplicationDict]] = {}
        self.value_dict: Dict[str, Any] = {} if _value_dict is None else _value_dict

        for k, v in dict(*args, **kwargs).items():
            self[k] = v

    def _set_value_dict(self, value_dict: dict) -> None:
        """Update the value dictionary and propagate the changes to nested DeDuplicationDict instances.

        Args:
            value_dict (dict): The new value dictionary to use for deduplication.
        """

        value_dict.update(self.value_dict)
        self.value_dict = value_dict
        for v in self.key_dict.values():
            if isinstance(v, str):
                continue

            v._set_value_dict(value_dict)

    def __setitem__(self, key: KT, value: VT) -> None:
        """Set the value for the given key, deduplicating the value if necessary.

        Args:
            key (KT): The key to set the value for.
            value (VT): The value to set for the given key.
        """

        if key in self.key_dict:
            del self[key]

        if isinstance(value, dict):
            self.key_dict[key] = DeDuplicationDict(value, _value_dict=self.value_dict)
        elif isinstance(value, DeDuplicationDict):
            self.key_dict[key] = value
            value._set_value_dict(self.value_dict)
        else:
            hash_id = sha256(pickle.dumps(value)).hexdigest()[:self.hash_length]
            self.key_dict[key] = hash_id
            self.value_dict[hash_id] = value

    def __getitem__(self, key: KT) -> VT_co:
        """Get the value for the given key.

        Args:
            key (KT): The key to get the value for.

        Returns:
            VT_co: The value for the given key.

        Raises:
            KeyError: If the key is not found in the dictionary.
            TypeError: If the value type is not supported.
        """

        if key not in self.key_dict:
            raise KeyError(key)

        v = self.key_dict[key]
        if isinstance(v, (DeDuplicationDict, self.__class__)):
            return v

        if isinstance(v, str):
            return self.value_dict[v]

        raise TypeError(f'WTF? {type(v)}')

    def all_hashes_in_use(self) -> set:
        """Get all hash values currently in use.

        Returns:
            set: A set of all hash values in use.
        """

        all_hashes_in_use = set()
        for v in self.key_dict.values():
            if isinstance(v, str):
                all_hashes_in_use.add(v)
            else:
                all_hashes_in_use.update(v.all_hashes_in_use())
        return all_hashes_in_use

    def clean_up(self) -> None:
        """Remove unused hash values from the value dictionary."""

        all_hashes_in_use = self.all_hashes_in_use()
        all_hashes = set(self.value_dict.keys())
        not_in_use = all_hashes - all_hashes_in_use
        for hash_id in not_in_use:
            del self.value_dict[hash_id]

    def detach(self) -> DeDuplicationDict:
        """Detach the DeDuplicationDict instance from its value dictionary, creating a standalone instance.

        Returns:
            DeDuplicationDict: A new DeDuplicationDict instance with its own value dictionary.
        """

        return self.from_json_save_dict(self.to_json_save_dict())

    def _del_detach(self) -> None:
        """Detach the DeDuplicationDict instance from its value dictionary and clean up unused hash values."""

        self._set_value_dict({})
        self.clean_up()

        for k, v in self.value_dict.items():
            self.value_dict[k] = copy.deepcopy(v)

    def __delitem__(self, key: KT) -> None:
        """Delete the item with the given key.

        Args:
            key (KT): The key of the item to delete.

        Raises:
            KeyError: If the key is not found in the dictionary.
        """

        if key not in self.key_dict:
            raise KeyError(key)

        v = self.key_dict[key]
        del self.key_dict[key]
        if isinstance(v, (DeDuplicationDict, self.__class__)):
            v._del_detach()

        if self.auto_clean_up:
            self.clean_up()

    def __len__(self) -> int:
        """Get the number of items in the dictionary.

        Returns:
            int: The number of items in the dictionary.
        """

        return len(self.key_dict)

    def __iter__(self) -> Iterator[T_co]:
        """Get an iterator over the keys in the dictionary.

        Returns:
            Iterator[T_co]: An iterator over the keys in the dictionary.
        """

        return iter(self.key_dict)

    def __repr__(self) -> str:
        """Get a string representation of the DeDuplicationDict instance.

        Returns:
            str: A string representation of the DeDuplicationDict instance.
        """

        return f'{self.__class__.__name__} [{len(self.key_dict)}:{len(self.value_dict)}]'

    def to_dict(self) -> dict:
        """Convert the DeDuplicationDict instance to a regular dictionary.

        Returns:
            dict: A regular dictionary with the same key-value pairs as the DeDuplicationDict instance.
        """

        return {k: v.to_dict() if isinstance(v, DeDuplicationDict) else v for k, v in self.items()}

    @classmethod
    def from_dict(cls, d: dict) -> DeDuplicationDict:
        """Create a DeDuplicationDict instance from a regular dictionary.

        Args:
            d (dict): The dictionary to create the DeDuplicationDict instance from.

        Returns:
            DeDuplicationDict: A new DeDuplicationDict instance with the same key-value pairs as the given dictionary.
        """

        return cls(**d)

    def _get_key_dict(self) -> dict:
        """Get the key dictionary of the DeDuplicationDict instance in a normal dictionary format.

        Returns:
            dict: The key dictionary of the DeDuplicationDict instance.
        """

        return {k: v._get_key_dict() if isinstance(v, DeDuplicationDict) else v for k, v in self.key_dict.items()}

    def to_json_save_dict(self) -> dict:
        """Convert the DeDuplicationDict instance to a dictionary that can be saved to a JSON file.

        Returns:
            dict: A dictionary that can be saved to a JSON file.
        """

        return {
            'key_dict': self._get_key_dict(),
            'value_dict': self.value_dict
        }

    @classmethod
    def from_json_save_dict(cls, d: dict, _v: dict = None) -> DeDuplicationDict:
        """Create a DeDuplicationDict instance from a dictionary that was saved to a JSON file.

        Args:
            d (dict): The dictionary that was saved to a JSON file.
            _v (dict, optional): The value dictionary to use. Defaults to None.

        Returns:
            DeDuplicationDict: A new DeDuplicationDict instance with the same key-value pairs as the given dictionary.
        """

        if _v is None:
            return cls.from_json_save_dict(d['key_dict'], _v=d['value_dict'])

        new_dict = cls()
        new_dict.key_dict = {}
        new_dict.value_dict = _v

        for k, v in d.items():
            if isinstance(v, dict):
                new_dict.key_dict[k] = cls.from_json_save_dict(v, _v=_v)
            else:
                new_dict.key_dict[k] = v

        return new_dict
