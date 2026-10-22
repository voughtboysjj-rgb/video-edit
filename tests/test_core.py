import json
from pathlib import Path
import tempfile
import unittest
from shorts_automation.cli import plan_for, validate, frame, audio, sha, probe

class CoreTests(unittest.TestCase):
    def test_valid_plan(self):
        self.assertEqual(validate(plan_for(1))['duration'],16)
    def test_rights_block(self):
        p=plan_for(1);p['rights']='unknown'
        with self.assertRaises(ValueError):validate(p)
    def test_variant_block(self):
        p=plan_for(1);p['variant']=3
        with self.assertRaises(ValueError):validate(p)
    def test_gap_block(self):
        p=plan_for(1);p['shots'][1]['start']=5
        with self.assertRaises(ValueError):validate(p)
    def test_bad_duration_block(self):
        p=plan_for(1);p['duration']=0
        with self.assertRaises(ValueError):validate(p)
    def test_resolution_block(self):
        p=plan_for(1);p['width']=720
        with self.assertRaises(ValueError):validate(p)
    def test_frames_deterministic(self):
        self.assertEqual(frame(7,1).tobytes(),frame(7,1).tobytes())
    def test_variants_differ(self):
        self.assertNotEqual(frame(7,1).tobytes(),frame(7,2).tobytes())
    def test_hash_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'x';p.write_bytes(b'one');a=sha(p);p.write_bytes(b'two');self.assertNotEqual(a,sha(p))
    def test_real_audio_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a.wav';audio(p,1);s=probe(p)['streams'][0]
            self.assertEqual(s['sample_rate'],'44100');self.assertEqual(s['channels'],2)

if __name__=='__main__':unittest.main()
