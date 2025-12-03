'''Integration tests for service discovery and port management'''

import unittest
from unittest.mock import Mock

class TestServiceDiscovery(unittest.TestCase):
    def setUp(self):
        self.service_discovery = Mock()

    def test_port_assignment(self):
        """Test that ports are assigned correctly within their ranges."""
        # Simulate port assignment logic
        self.service_discovery.assign_port('gateway', '10010')
        self.service_discovery.assign_port('kernel', '10020')
        self.service_discovery.assign_port('rag', '10040')
        
        # Verify assignments
        self.assertEqual(self.service_discovery.get_port('gateway'), 10010)
        self.assertEqual(self.service_discovery.get_port('kernel'), 10020)
        self.assertEqual(self.service_discovery.get_port('rag'), 10040)