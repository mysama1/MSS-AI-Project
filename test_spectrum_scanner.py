import unittest
from spectrum_scanner import SpectrumScanner, FieldType

class TestSpectrumScanner(unittest.TestCase):
    def setUp(self):
        self.scanner = SpectrumScanner()
    
    def test_tasks_initialized(self):
        self.assertEqual(len(self.scanner.tasks), 20)
    
    def test_all_fields_covered(self):
        fields = set(t.field for t in self.scanner.tasks.values())
        self.assertEqual(len(fields), 10)
    
    def test_submit_result(self):
        result = self.scanner.submit_result('T-001', 85, 80.0)
        self.assertEqual(result.task_id, 'T-001')
        self.assertEqual(result.field, FieldType.LOGIC)
        self.assertTrue(result.completed)
        self.assertGreater(result.t_estimate, 0)
    
    def test_high_score_t_mapping(self):
        result = self.scanner.submit_result('T-001', 90, 60.0)
        self.assertGreaterEqual(result.t_estimate, 0.7)
    
    def test_low_score_t_mapping(self):
        result = self.scanner.submit_result('T-001', 20, 60.0)
        self.assertLess(result.t_estimate, 0.2)
    
    def test_spectrum_generation(self):
        self.scanner.submit_result('T-001', 85, 80.0)
        self.scanner.submit_result('T-002', 75, 90.0)
        spectrum = self.scanner.generate_spectrum()
        self.assertIn('logic', spectrum)
        self.assertIsNotNone(spectrum['logic']['t_value'])
    
    def test_empty_spectrum(self):
        spectrum = self.scanner.generate_spectrum()
        self.assertEqual(spectrum, {})
    
    def test_overall_profile(self):
        self.scanner.submit_result('T-001', 85, 80.0)
        self.scanner.submit_result('T-003', 90, 70.0)
        profile = self.scanner.get_overall_profile()
        self.assertIn('overall_t', profile)
        self.assertIn('dominant_fields', profile)
        self.assertIn('weak_fields', profile)
    
    def test_profile_classification(self):
        # Balanced high
        self.scanner.submit_result('T-001', 90, 60)
        self.scanner.submit_result('T-003', 88, 60)
        profile = self.scanner.get_overall_profile()
        self.assertIn(profile['profile_type'], 
                     ['balanced_k4', 'specialized_k4', 'transitional'])
    
    def test_report_generation(self):
        self.scanner.submit_result('T-001', 85, 80.0)
        report = self.scanner.export_report()
        self.assertIn('Meaning Field Spectrum Report', report)
        self.assertIn('Overall Profile', report)
    
    def test_invalid_task(self):
        with self.assertRaises(ValueError):
            self.scanner.submit_result('INVALID', 50, 60.0)

if __name__ == '__main__':
    unittest.main()
