import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from no_min_trades import select_quote,select_portfolio


class NoMinimumTests(unittest.TestCase):
    def test_one_profitable_observation_can_qualify(self):
        row={'trades':1,'mean_net_bps':2.,'execution_zero_volume':0}
        self.assertEqual(select_quote([row]),row)

    def test_negative_and_zero_observations_do_not_show_profit(self):
        self.assertIsNone(select_quote([{'trades':0,'mean_net_bps':None,'execution_zero_volume':0},
            {'trades':11,'mean_net_bps':-1.,'execution_zero_volume':0}]))

    def test_only_sample_gate_changes(self):
        rows={'rare':{'trades':11,'net_total_return':.01,'exit_capacity_failures':0},
              'invalid':{'trades':400,'net_total_return':.5,'exit_capacity_failures':1}}
        self.assertIsNone(select_portfolio(rows,200))
        self.assertEqual(select_portfolio(rows),'rare')


if __name__=='__main__':unittest.main()
