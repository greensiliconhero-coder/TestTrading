import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from five_day_v5 import features

class CorrectedFeatureTests(unittest.TestCase):
    def test_future_price_changes_cannot_change_current_features(self):
        f=pd.DataFrame({'close':np.arange(100.,200.),'volume':np.arange(1000.,1100.)})
        idx=pd.Series(np.arange(200.,300.))
        before=features(f,idx).iloc[70].copy()
        f.loc[71:,'close']*=10;f.loc[71:,'volume']*=4;idx.loc[71:]*=3
        np.testing.assert_array_equal(before.to_numpy(),features(f,idx).iloc[70].to_numpy())

    def test_saved_cohort_and_boundary_purge(self):
        root=Path(__file__).resolve().parents[1]
        path=root/'data/raw_five_day_v9/samples.csv'
        if not path.exists():self.skipTest('Run artifact not available')
        new=pd.read_csv(path);old=pd.read_csv(root/'data/five_day_v5/samples_with_scores.csv')
        keys=['symbol','day','entry_day','exit_day','split']
        self.assertEqual(set(map(tuple,new[keys].to_numpy())),set(map(tuple,old[keys].to_numpy())))
        self.assertEqual(len(new),len(old))
        self.assertTrue((new.loc[new.split=='train','exit_day']<'2024-01-01').all())
        self.assertTrue((new.loc[new.split=='validation','exit_day']<'2025-01-01').all())
        np.testing.assert_allclose(new.future_return,new.exit_open/new.entry_open-1,atol=1e-14)

if __name__=='__main__':unittest.main()
