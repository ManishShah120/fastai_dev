#AUTOGENERATED! DO NOT EDIT! File to edit: dev/95_synth_learner.ipynb (unless otherwise specified).

__all__ = ['synth_data', 'RegModel', 'synth_learner']

#Cell 0
from ..torch_basics import *
from ..test import *
from ..layers import *
from ..data.pipeline import *
from ..data.source import *
from ..data.core import *
from ..optimizer import *
from ..learner import *
from torch.utils.data import TensorDataset

#Cell 3
from torch.utils.data import TensorDataset

def synth_data(a=2, b=3, bs=16, n_train=10, n_valid=2, cuda=False):
    def get_data(n):
        x = torch.randn(bs*n, 1)
        return TensorDataset(x, a*x + b + 0.1*torch.randn(bs*n, 1))
    train_ds = get_data(n_train)
    valid_ds = get_data(n_valid)
    tfms = Cuda() if cuda else None
    train_dl = TfmdDL(train_ds, bs=bs, shuffle=True, after_batch=tfms)
    valid_dl = TfmdDL(valid_ds, bs=bs, after_batch=tfms)
    return DataBunch(train_dl, valid_dl)

#Cell 4
class RegModel(Module):
    def __init__(self): self.a,self.b = nn.Parameter(torch.randn(1)),nn.Parameter(torch.randn(1))
    def forward(self, x): return x*self.a + self.b

#Cell 5
def synth_learner(n_trn=10, n_val=2, cuda=False, **kwargs):
    return Learner(RegModel(), synth_data(n_train=n_trn,n_valid=n_val, cuda=cuda), MSELossFlat(),
                   opt_func=partial(SGD, mom=0.9), **kwargs)