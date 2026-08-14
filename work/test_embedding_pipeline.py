import unittest

from embedding_pipeline import serialize_vector


class SerializeVectorTests(unittest.TestCase):
    def test_rejects_a_vector_with_the_wrong_dimension(self):
        with self.assertRaisesRegex(ValueError, "384"):
            serialize_vector([0.0] * 383)

    def test_emits_pgvector_compatible_text(self):
        vector = [0.0] * 384
        vector[0] = 0.125
        vector[-1] = -0.5

        serialized = serialize_vector(vector)

        self.assertTrue(serialized.startswith("[0.12500000,"))
        self.assertTrue(serialized.endswith(",-0.50000000]"))
        self.assertEqual(384, len(serialized[1:-1].split(",")))


if __name__ == "__main__":
    unittest.main()
