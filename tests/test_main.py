import copy
import json
import sys
import unittest
from pathlib import Path

from deduplicationdict import DeDuplicationDict


def get_size(obj, seen=None):
    """
    Recursively finds the size of objects.

    Args:
        obj: The object to calculate the size of.
        seen (set, optional): A set of objects that have already been seen. Defaults to None.

    Returns:
        int: The size of the object in bytes.
    """

    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size


def get_json_test_data():
    with open(Path(__file__).parent.joinpath('test.json'), 'r', encoding="utf-8") as f:
        data = json.load(f)
    return data


class TestMain(unittest.TestCase):
    """Test the main functionality of the DeDuplicationDict class."""

    def test_init(self):
        """ Test the initialization of the DeDuplicationDict class with data from a JSON file."""

        data = get_json_test_data()

        dd_dict = DeDuplicationDict(**data)
        self.assertEqual(len(dd_dict), len(data))

    def test_value_dict_consistency(self, dd_dict=None):
        """Test the consistency of the value_dict attribute in the DeDuplicationDict class."""

        if dd_dict is None:
            data = get_json_test_data()
            dd_dict = DeDuplicationDict(**data)

        to_visit = [dd_dict]
        while len(to_visit) > 0:
            current = to_visit.pop()
            self.assertEqual(isinstance(current, DeDuplicationDict), True)
            self.assertEqual(dd_dict.value_dict, current.value_dict)
            self.assertEqual(id(dd_dict.value_dict), id(current.value_dict))

            for v in current.key_dict.values():
                if isinstance(v, DeDuplicationDict):
                    to_visit.append(v)
                elif isinstance(v, str):
                    self.assertIn(v, current.value_dict)
                else:
                    raise TypeError(f'WTF? {type(v)}')

    def test_getitem(self):
        """Test the __getitem__ method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        to_visit = [(dd_dict, data)]
        while to_visit:
            dd_dict, data = to_visit.pop()
            for k, v in data.items():
                if isinstance(v, dict):
                    self.assertIsInstance(dd_dict[k], DeDuplicationDict)
                    to_visit.append((dd_dict[k], v))
                else:
                    self.assertEqual(dd_dict[k], v)

    def test_getitem_keyerror(self):
        """Test the KeyError raised by the __getitem__ method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        with self.assertRaises(KeyError):
            _ = dd_dict['nonexistent_key']

    def test_setitem(self):
        """Test the __setitem__ method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict()
        to_visit = [(dd_dict, data)]
        while to_visit:
            dd_dict, data = to_visit.pop()
            for k, v in data.items():
                if isinstance(v, dict):
                    dd_dict[k] = DeDuplicationDict()
                    to_visit.append((dd_dict[k], v))
                else:
                    dd_dict[k] = v

        json_dd_dict = json.dumps(dd_dict.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.test_value_dict_consistency(dd_dict)
        self.assertEqual(json_dd_dict, json_data)

    def test_double_setitem(self):
        """Test the __setitem__ method of the DeDuplicationDict class when setting the same item twice."""

        # noinspection PyPackageRequirements
        import deepdiff

        data = get_json_test_data()
        dd_dict = DeDuplicationDict()
        dd_dict2 = DeDuplicationDict()
        to_visit = [(dd_dict, data)]
        while to_visit:
            dd_dict, data = to_visit.pop()
            for k, v in data.items():
                if isinstance(v, dict):
                    dd_dict[k] = DeDuplicationDict()
                    to_visit.append((dd_dict[k], v))
                else:
                    dd_dict[k] = v
                    dd_dict[k] = v

        dd_dict2.update(dd_dict)
        json_dd_dict = json.dumps(dd_dict.to_dict(), sort_keys=True)
        json_dd_dict2 = json.dumps(dd_dict2.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.test_value_dict_consistency(dd_dict)
        self.test_value_dict_consistency(dd_dict2)
        self.assertEqual(json_dd_dict, json_data)
        self.assertEqual(json_dd_dict2, json_data)
        diff = deepdiff.DeepDiff(dd_dict, dd_dict2)
        self.assertEqual(len(diff), 0)

    def test_setitem_dd_value(self):
        """Test the __setitem__ method of the DeDuplicationDict class when setting a DeDuplicationDict as value."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict()
        for i in data:
            if isinstance(data[i], dict):
                dd_dict[i] = DeDuplicationDict(data[i])
            else:
                dd_dict[i] = data[i]

        self.test_value_dict_consistency(dd_dict)
        json_dd_dict = json.dumps(dd_dict.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.assertEqual(json_dd_dict, json_data)

    def test_detach(self):
        """Test the detach method of the DeDuplicationDict class."""

        # noinspection PyPackageRequirements
        import deepdiff

        data = get_json_test_data()
        dd_dict1 = DeDuplicationDict(**data)
        dd_dict2 = dd_dict1.detach()
        diff = deepdiff.DeepDiff(dd_dict1, dd_dict2)
        self.assertEqual(dd_dict1, dd_dict2)
        self.assertNotEqual(id(dd_dict1), id(dd_dict2))
        self.assertEqual(len(diff), 0)

    def test_delitem(self):
        """Test the __delitem__ method of the DeDuplicationDict class."""

        # noinspection PyPackageRequirements
        import deepdiff

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        to_visit = [(dd_dict, data)]
        while to_visit:
            dd_dict, data = to_visit.pop()
            for k, v in list(data.items()):
                dd_data2 = DeDuplicationDict(**data)
                dd_data2["test"] = copy.deepcopy(dd_dict)
                dd_dict2 = dd_data2["test"].detach()
                self.assertEqual(len(deepdiff.DeepDiff(dd_dict, dd_dict2)), 0)
                self.assertEqual(dd_dict.all_hashes_in_use(), set(dd_dict.value_dict.keys()))
                self.assertEqual(dd_dict2.all_hashes_in_use(), set(dd_dict2.value_dict.keys()))

                if isinstance(v, dict):
                    to_visit.append((dd_dict[k], v))
                    del dd_dict[k]
                    del data[k]
                    self.assertNotIn(k, dd_dict)
                    self.assertNotIn(k, data)
                    json_dd_dict = json.dumps(dd_dict.to_dict(), sort_keys=True)
                    json_data = json.dumps(data, sort_keys=True)
                    self.assertEqual(json_dd_dict, json_data)
                else:
                    del dd_dict[k]
                    del data[k]

                self.assertEqual(dd_dict.all_hashes_in_use(), set(dd_dict.value_dict.keys()))

        self.assertEqual(len(dd_dict), 0)

    def test_delitem_keyerror(self):
        """Test the KeyError raised by the __delitem__ method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        with self.assertRaises(KeyError):
            del dd_dict['nonexistent_key']

    def test_len(self):
        """Test the __len__ method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        to_visit = [(dd_dict, data)]
        while to_visit:
            dd_dict, data = to_visit.pop()
            self.assertEqual(len(dd_dict), len(data))

            for k, v in data.items():
                if not isinstance(v, dict):
                    continue

                to_visit.append((dd_dict[k], v))

    def test_iter(self):
        """Test the __iter__ method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        to_visit = [(dd_dict, data)]
        while to_visit:
            dd_dict, data = to_visit.pop()
            self.assertEqual(set(dd_dict), set(data))

            for k, v in data.items():
                if not isinstance(v, dict):
                    continue

                to_visit.append((dd_dict[k], v))

    def test_repr(self):
        """Test the __repr__ method of the DeDuplicationDict class."""

        dd_dict = DeDuplicationDict()
        self.assertIn('DeDuplicationDict', repr(dd_dict))

    def test_contains(self):
        """Test the __contains__ method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        to_visit = [(dd_dict, data)]
        while to_visit:
            dd_dict, data = to_visit.pop()
            for k, v in data.items():
                self.assertIn(k, dd_dict)

                if not isinstance(v, dict):
                    continue

                to_visit.append((dd_dict[k], v))

    def test_to_dict(self):
        """Test the to_dict method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        json_dd_dict = json.dumps(dd_dict.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.assertEqual(json_dd_dict, json_data)

    def test_from_dict(self):
        """Test the from_dict method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict.from_dict(data)
        json_dd_dict = json.dumps(dd_dict.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.assertEqual(json_dd_dict, json_data)

    def test_get_key_dict(self):
        """Test the _get_key_dict method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        key_dict = dd_dict._get_key_dict()
        to_visit = [(data, key_dict)]
        while to_visit:
            data, key_dict = to_visit.pop()
            for k, v in data.items():
                self.assertIn(k, key_dict)

                if not isinstance(v, dict):
                    continue

                to_visit.append((v, key_dict[k]))

    def test_set_key_dict(self):
        """Test the _set_key_dict method of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        dd_dict2 = DeDuplicationDict()
        dd_dict2.value_dict = dd_dict.value_dict
        dd_dict2._set_key_dict(dd_dict._get_key_dict())

        json_data = json.dumps(data, sort_keys=True)
        json_dd_dict = json.dumps(dd_dict.to_dict(), sort_keys=True)
        json_dd_dict2 = json.dumps(dd_dict2.to_dict(), sort_keys=True)
        self.assertEqual(json_data, json_dd_dict)
        self.assertEqual(json_data, json_dd_dict2)

    def test_size_compression(self):
        """Test the size compression of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        size_dd_dict = get_size(dd_dict)
        size_data = get_size(data)
        print(f'size_dd_dict: {size_dd_dict / 1024 / 1024:0.3f} MB')
        print(f'size_data: {size_data / 1024 / 1024:0.3f} MB')
        print(f'size reduction: {size_data / size_dd_dict:0.3f}x')
        self.assertLessEqual(size_dd_dict, size_data)

    def test_json_size_compression(self):
        """Test the json size compression of the DeDuplicationDict class."""

        data = get_json_test_data()
        dd_dict = DeDuplicationDict(**data)
        size_dd_json = get_size(json.dumps(dd_dict.to_json_save_dict()))
        size_json = get_size(json.dumps(data))
        print(f'size_dd_json: {size_dd_json / 1024 / 1024:0.3f} MB')
        print(f'size_json: {size_json / 1024 / 1024:0.3f} MB')
        print(f'size reduction: {size_json / size_dd_json:0.3f}x')
        self.assertLessEqual(size_dd_json, size_json)

    def test_cache_dict(self):
        """Test the cache_dict method of the DeDuplicationDict class."""

        # noinspection PyPackageRequirements
        import deepdiff
        data = get_json_test_data()
        dd_dict1 = DeDuplicationDict(**data)
        dd_dict2 = DeDuplicationDict.from_json_save_dict(dd_dict1.to_json_save_dict())
        diff = deepdiff.DeepDiff(dd_dict1, dd_dict2)
        self.assertNotEqual(id(dd_dict1), id(dd_dict2))
        self.assertEqual(len(diff), 0)

    def test_deepcopy(self):
        """Test the deepcopy method of the DeDuplicationDict class."""

        # noinspection PyPackageRequirements
        import deepdiff
        data = get_json_test_data()
        dd_dict1 = DeDuplicationDict(**data)
        dd_dict2 = copy.deepcopy(dd_dict1)
        diff = deepdiff.DeepDiff(dd_dict1, dd_dict2)
        self.assertNotEqual(id(dd_dict1), id(dd_dict2))
        self.assertEqual(len(diff), 0)


if __name__ == '__main__':
    unittest.main()
