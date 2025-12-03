'''Unit tests for configuration loading and merging'''

import unittest
from core.config.merged import MergedConfiguration

class TestMergedConfiguration(unittest.TestCase):
    def setUp(self):
        self.config = MergedConfiguration()

    def test_load_source(self):
        """Test that a configuration source can be loaded."""
        success = self.config.load_source('settings', 'config/settings.yaml')
        self.assertTrue(success)

    def test_merge_configurations(self):
        """Test that configurations are merged correctly."""
        merged = self.config.merge()
        self.assertIn('models', merged)
        self.assertIn('rag', merged)
        self.assertIn('policies', merged)