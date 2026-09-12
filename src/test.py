import unittest
from lexer import classify_id

class TestClassifyId(unittest.TestCase):

    def test_class_name(self):
        for v in ['Person', 'Child', 'Church', 'University', 'Second_Baptist_Church']:
            self.assertEqual(classify_id(v), 'CLASS_NAME')

    def test_relation_name(self):
        for v in ['has', 'hasParent', 'has_parent', 'isPartOf', 'is_part_of']:
            self.assertEqual(classify_id(v), 'RELATION_NAME')

    def test_instance_name(self):
        for v in ['Planeta1', 'Planeta2', 'pizza03', 'pizza123']:
            self.assertEqual(classify_id(v), 'INSTANCE_NAME')

    def test_datatype_name(self):
        for v in ['CPFDataType', 'PhoneNumberDataType']:
            self.assertEqual(classify_id(v), 'DATATYPE_NAME')

    def test_ambiguity_datatype_over_class(self):
        # CPFDataType bate em CLASS_RE também; datatype deve vencer
        self.assertEqual(classify_id('CPFDataType'), 'DATATYPE_NAME')

    def test_ambiguity_instance_over_class(self):
        # Planeta1 bate em CLASS_RE se ignorasse dígito; instance deve vencer
        self.assertEqual(classify_id('Planeta1'), 'INSTANCE_NAME')

    def test_invalid_underscore_leading(self):
        self.assertIsNone(classify_id('_Person'))

    def test_invalid_underscore_trailing(self):
        self.assertIsNone(classify_id('Person_'))

    def test_invalid_double_underscore(self):
        self.assertIsNone(classify_id('has__parent'))

    def test_invalid_digit_in_middle(self):
        self.assertIsNone(classify_id('pizza1a'))

if __name__ == '__main__':
    unittest.main()