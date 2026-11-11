import copy
import unittest
from ii_screen import screen


def synthetic_payload():
    dry_days = ['2026-05-01', '2026-05-02', '2026-05-03']
    storm_day = '2026-05-04'
    records = []
    for day in dry_days:
        records.extend({'day':day, 'hour_utc':h, 'flow_m3h':10.0, 'rain_mm':0.0} for h in range(24))
    for h in range(24):
        records.append({'day':storm_day, 'hour_utc':h, 'flow_m3h':14.0 if 6 <= h < 10 else 10.0,
                        'rain_mm':5.0 if 6 <= h < 10 else 0.0})
    return {'dataset_type':'SYNTHETIC_DEMONSTRATION', 'clock_basis':'UTC', 'interval_minutes':60,
            'meter_id':'SYNTH-METER-001', 'assumed_flow_error_m3h':0.2,
            'dry_days':dry_days,'storm_day':storm_day,'records':records}


class TestIIScreen(unittest.TestCase):
    def test_results_and_units(self):
        out=screen(synthetic_payload())
        self.assertEqual(out['storm_rain_mm'], 20.0)
        self.assertEqual(out['storm_observed_volume_m3'], 256.0)
        self.assertEqual(out['matched_dry_weather_volume_m3'], 240.0)
        self.assertEqual(out['positive_difference_screen_m3'],16.0)
        self.assertEqual(out['meter_error_only_range_m3'],[14.4,25.6])
        self.assertEqual(out['regulatory_compliance'],'NOT_ASSESSED')
        self.assertEqual(out['site_field_measurement_claim'],'NONE')

    def test_missing_hour_fails_closed(self):
        p=synthetic_payload();p['records'].pop()
        with self.assertRaises(ValueError):screen(p)

    def test_duplicate_hour_fails_closed(self):
        p=synthetic_payload();p['records'].append(copy.deepcopy(p['records'][-1]))
        with self.assertRaises(ValueError):screen(p)

    def test_non_synthetic_label_rejected(self):
        p=synthetic_payload();p['dataset_type']='MEASURED'
        with self.assertRaises(ValueError):screen(p)

    def test_rainy_dry_day_rejected(self):
        p=synthetic_payload();p['records'][0]['rain_mm']=0.1
        with self.assertRaises(ValueError):screen(p)

    def test_clock_boundary_rejected(self):
        p=synthetic_payload();p['clock_basis']='local'
        with self.assertRaises(ValueError):screen(p)

    def test_missing_or_bad_flow_rejected(self):
        for v in (None,-1.0,float('nan')):
            p=synthetic_payload();p['records'][0]['flow_m3h']=v
            with self.assertRaises(ValueError):screen(p)

    def test_unproven_meter_id_rejected(self):
        p=synthetic_payload();p['meter_id']='Ashville-WWTP-meter-1'
        with self.assertRaises(ValueError):screen(p)

    def test_no_rain_rejected(self):
        p=synthetic_payload()
        for row in p['records']:
            row['rain_mm']=0
        with self.assertRaises(ValueError):screen(p)

    def test_minimum_baseline_days(self):
        p=synthetic_payload();p['dry_days']=p['dry_days'][:2]
        with self.assertRaises(ValueError):screen(p)

    def test_negative_uncertainty_rejected(self):
        p=synthetic_payload();p['assumed_flow_error_m3h']=-0.1
        with self.assertRaises(ValueError):screen(p)


if __name__=='__main__':unittest.main()
