import json
import sys
import unittest


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


class TestMain(unittest.TestCase):
    """Test the main functionality of the DeDuplicationDict class."""

    def test_init(self):
        """ Test the initialization of the DeDuplicationDict class with data from a JSON file."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        self.assertEqual(len(ac_dict), len(data))

    def test_value_dict_consistency(self):
        """Test the consistency of the value_dict attribute in the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        to_visit = [ac_dict]
        while len(to_visit) > 0:
            current = to_visit.pop()
            self.assertEqual(isinstance(current, DeDuplicationDict), True)
            self.assertEqual(ac_dict.value_dict, current.value_dict)

            for v in current.key_dict.values():
                if isinstance(v, DeDuplicationDict):
                    to_visit.append(v)
                elif isinstance(v, str):
                    self.assertIn(v, current.value_dict)
                else:
                    raise TypeError(f'WTF? {type(v)}')

    def test_getitem(self):
        """Test the __getitem__ method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        to_visit = [(ac_dict, data)]
        while to_visit:
            ac_dict, data = to_visit.pop()
            for k, v in data.items():
                if isinstance(v, dict):
                    self.assertIsInstance(ac_dict[k], DeDuplicationDict)
                    to_visit.append((ac_dict[k], v))
                else:
                    self.assertEqual(ac_dict[k], v)

    def test_getitem_keyerror(self):
        """Test the KeyError raised by the __getitem__ method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        with self.assertRaises(KeyError):
            _ = ac_dict['nonexistent_key']

    def test_setitem(self):
        """Test the __setitem__ method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict()
        to_visit = [(ac_dict, data)]
        while to_visit:
            ac_dict, data = to_visit.pop()
            for k, v in data.items():
                if isinstance(v, dict):
                    ac_dict[k] = DeDuplicationDict()
                    to_visit.append((ac_dict[k], v))
                else:
                    ac_dict[k] = v

        json_auto_cache_dict = json.dumps(ac_dict.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.assertEqual(json_auto_cache_dict, json_data)

    def test_double_setitem(self):
        """Test the __setitem__ method of the DeDuplicationDict class when setting the same item twice."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict()
        to_visit = [(ac_dict, data)]
        while to_visit:
            ac_dict, data = to_visit.pop()
            for k, v in data.items():
                if isinstance(v, dict):
                    ac_dict[k] = DeDuplicationDict()
                    to_visit.append((ac_dict[k], v))
                else:
                    ac_dict[k] = v
                    ac_dict[k] = v

        json_auto_cache_dict = json.dumps(ac_dict.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.assertEqual(json_auto_cache_dict, json_data)

    def test_detach(self):
        """Test the detach method of the DeDuplicationDict class."""

        # noinspection PyPackageRequirements
        import deepdiff

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict1 = DeDuplicationDict(**data)
        ac_dict2 = ac_dict1.detach()
        diff = deepdiff.DeepDiff(ac_dict1, ac_dict2)
        self.assertEqual(ac_dict1, ac_dict2)
        self.assertNotEqual(id(ac_dict1), id(ac_dict2))
        self.assertEqual(len(diff), 0)

    def test_delitem(self):
        """Test the __delitem__ method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        to_visit = [(ac_dict, data)]
        while to_visit:
            ac_dict, data = to_visit.pop()
            for k, v in list(data.items()):
                self.assertEqual(ac_dict.all_hashes_in_use(), set(ac_dict.value_dict.keys()))

                if isinstance(v, dict):
                    to_visit.append((ac_dict[k], v))
                    del ac_dict[k]
                    del data[k]
                    self.assertNotIn(k, ac_dict)
                    self.assertNotIn(k, data)
                    json_auto_cache_dict = json.dumps(ac_dict.to_dict(), sort_keys=True)
                    json_data = json.dumps(data, sort_keys=True)
                    self.assertEqual(json_auto_cache_dict, json_data)
                else:
                    del ac_dict[k]
                    del data[k]

                self.assertEqual(ac_dict.all_hashes_in_use(), set(ac_dict.value_dict.keys()))

        self.assertEqual(len(ac_dict), 0)

    def test_delitem_keyerror(self):
        """Test the KeyError raised by the __delitem__ method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        with self.assertRaises(KeyError):
            del ac_dict['nonexistent_key']

    def test_len(self):
        """Test the __len__ method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        to_visit = [(ac_dict, data)]
        while to_visit:
            ac_dict, data = to_visit.pop()
            self.assertEqual(len(ac_dict), len(data))

            for k, v in data.items():
                if not isinstance(v, dict):
                    continue

                to_visit.append((ac_dict[k], v))

    def test_iter(self):
        """Test the __iter__ method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        to_visit = [(ac_dict, data)]
        while to_visit:
            ac_dict, data = to_visit.pop()
            self.assertEqual(set(ac_dict), set(data))

            for k, v in data.items():
                if not isinstance(v, dict):
                    continue

                to_visit.append((ac_dict[k], v))

    def test_repr(self):
        """Test the __repr__ method of the DeDuplicationDict class."""

        ac_dict = DeDuplicationDict()
        self.assertIn('DeDuplicationDict', repr(ac_dict))

    def test_contains(self):
        """Test the __contains__ method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        to_visit = [(ac_dict, data)]
        while to_visit:
            ac_dict, data = to_visit.pop()
            for k, v in data.items():
                self.assertIn(k, ac_dict)

                if not isinstance(v, dict):
                    continue

                to_visit.append((ac_dict[k], v))

    def test_to_dict(self):
        """Test the to_dict method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        json_auto_cache_dict = json.dumps(ac_dict.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.assertEqual(json_auto_cache_dict, json_data)

    def test_from_dict(self):
        """Test the from_dict method of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict.from_dict(data)
        json_auto_cache_dict = json.dumps(ac_dict.to_dict(), sort_keys=True)
        json_data = json.dumps(data, sort_keys=True)
        self.assertEqual(json_auto_cache_dict, json_data)

    def test_size_compression(self):
        """Test the size compression of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        size_auto_cache_dict = get_size(ac_dict)
        size_data = get_size(data)
        print(f'size_auto_cache_dict / size_data: {size_auto_cache_dict / size_data}')
        self.assertLessEqual(size_auto_cache_dict, size_data)

    def test_json_size_compression(self):
        """Test the json size compression of the DeDuplicationDict class."""

        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict = DeDuplicationDict(**data)
        size_auto_cache_json = len(json.dumps(ac_dict.to_json_save_dict()))
        size_json = len(json.dumps(data))
        print(f'size_auto_cache_json / size_json: {size_auto_cache_json / size_json}')
        self.assertLessEqual(size_auto_cache_json, size_json)

    def test_cache_dict(self):
        """Test the cache_dict method of the DeDuplicationDict class."""

        # noinspection PyPackageRequirements
        import deepdiff
        with open('test.json', 'r') as f:
            data = json.load(f)

        ac_dict1 = DeDuplicationDict(**data)
        ac_dict2 = DeDuplicationDict.from_json_save_dict(ac_dict1.to_json_save_dict())
        diff = deepdiff.DeepDiff(ac_dict1, ac_dict2)
        self.assertNotEqual(id(ac_dict1), id(ac_dict2))
        self.assertEqual(len(diff), 0)


if __name__ == '__main__':
    unittest.main()
