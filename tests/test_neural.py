import sys
from pathlib import Path
import tempfile
import unittest
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from neural_v2 import window_features,SequenceCNN,save_torch


class NeuralTests(unittest.TestCase):
    def test_future_candles_cannot_change_window(self):
        data=np.tile([100.,102.,99.,101.,1000.],(100,1))
        before=window_features(data[:60])
        data[60:]*=2
        np.testing.assert_array_equal(before,window_features(data[:60]))

    def test_scale_invariance_and_invalid_window(self):
        data=np.tile([100.,102.,99.,101.,1000.],(60,1))
        scaled=data.copy(); scaled[:,:4]*=2; scaled[:,4]*=3
        np.testing.assert_allclose(window_features(data),window_features(scaled),atol=1e-7)
        with self.assertRaises(ValueError): window_features(data[:59])
        data[0,0]=0
        with self.assertRaises(ValueError): window_features(data)

    def test_checkpoint_reloads_same_predictions(self):
        root=Path(__file__).resolve().parents[1]/'work/test-temp'; root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            torch.manual_seed(1)
            model=SequenceCNN().eval(); sample=torch.randn(3,5,60)
            with torch.no_grad(): before=model(sample)
            path=Path(folder)/'weights.pt'; save_torch(path,model.state_dict())
            restored=SequenceCNN().eval()
            restored.load_state_dict(torch.load(path,map_location='cpu',weights_only=True))
            with torch.no_grad(): after=restored(sample)
            torch.testing.assert_close(before,after,rtol=0,atol=0)


if __name__=='__main__': unittest.main()
