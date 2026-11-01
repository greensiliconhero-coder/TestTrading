import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from context_features import candle_features, event_masks
from context_models import fees, simulate, candidate_signals


class ContextV3Tests(unittest.TestCase):
    def test_future_candles_cannot_change_inputs(self):
        close = np.linspace(100,103,375)
        data = pd.DataFrame({'open':close,'close':close,'high':close+1,'low':close-1,'volume':np.ones(375)*10000})
        before = candle_features(data,615)
        data.loc[61:,['open','close','high','low','volume']] *= 20
        self.assertEqual(before,candle_features(data,615))

    def test_fees_reconcile_entry_exit_and_date_changes(self):
        for day in ['2021-02-01','2023-05-01','2024-05-01','2024-11-01']:
            self.assertAlmostEqual(fees(10000,10100,day),fees(10000,0,day)+fees(0,10100,day))
        self.assertGreater(fees(10000,10000,'2021-02-01'),fees(10000,10000,'2024-11-01'))

    def config(self):
        return {'initial_capital':10000,'position_budget':10000,'maximum_positions':5,
                'slippage_bps_per_side':2,'entry_delay_bars':2,'exit_delay_bars':32,'participation_fraction':.01}

    def signals(self):
        return pd.DataFrame([{'symbol':'X','day':'2023-01-02','signal_minute':615,'score':.01,
            'entry_open':100,'exit_open':102,'entry_volume':100000,'exit_volume':100000}])

    def test_cash_and_whole_shares_and_fee_accounting(self):
        stats,daily,trades = simulate(self.signals(),['2023-01-02'],self.config())
        self.assertEqual(trades.quantity.iloc[0],99)
        self.assertAlmostEqual(stats['final_equity'],10000+trades.net_pnl.sum())
        self.assertGreater(stats['total_fees'],0)

    def test_bad_exit_capacity_is_recorded_not_removed(self):
        signals = self.signals();signals['exit_volume']=1
        stats,_,_ = simulate(signals,['2023-01-02'],self.config())
        self.assertEqual(stats['trades'],1)
        self.assertEqual(stats['exit_capacity_failures'],1)

    def test_cash_baseline_and_overlapping_batches(self):
        signals = self.signals()
        stats,_,_ = simulate(signals.iloc[:0],['2023-01-02'],self.config())
        self.assertEqual(stats['net_total_return'],0)
        bad = pd.concat([signals,signals.assign(signal_minute=620)])
        with self.assertRaises(ValueError):simulate(bad,['2023-01-02'],self.config())


if __name__=='__main__':
    unittest.main()
