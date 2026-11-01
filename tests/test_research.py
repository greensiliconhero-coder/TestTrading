import sys
from pathlib import Path
import unittest
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from research_v1 import session_samples, FEATURES


class ResearchTests(unittest.TestCase):
    def sample(self):
        x=np.arange(375,dtype=float)+100
        return pd.DataFrame({'open':x,'high':x+2,'low':x-1,'close':x+1,'volume':100})

    def test_future_prices_do_not_change_past_features(self):
        data=self.sample()
        before=session_samples(data,'TEST','2023-01-02')[0]
        data.loc[31:,'close'] *= 1.1
        after=session_samples(data,'TEST','2023-01-02')[0]
        self.assertEqual([before[k] for k in FEATURES],[after[k] for k in FEATURES])
        self.assertNotEqual(before['future_return'],after['future_return'])

    def test_entry_after_signal_and_exit_no_overnight(self):
        rows=session_samples(self.sample(),'TEST','2023-01-02')
        self.assertAlmostEqual(rows[0]['future_return'],161/131-1)
        self.assertEqual(len(rows),11)
        self.assertLess(rows[-1]['signal_minute']+30,930)

    def test_incomplete_session_rejected(self):
        self.assertEqual(session_samples(self.sample().iloc[:-1],'TEST','2023-01-02'),[])


if __name__=='__main__': unittest.main()
