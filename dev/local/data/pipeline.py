#AUTOGENERATED! DO NOT EDIT! File to edit: dev/02_data_pipeline_v2.ipynb (unless otherwise specified).

__all__ = ['get_func', 'show_title', 'Func', 'Sig', 'SelfFunc', 'Self', 'positional_annotations', 'Transform',
           'mk_func', 'mk_tfm', 'compose_tfms', 'Pipeline']

from ..imports import *
from ..test import *
from ..core import *
from ..notebook.showdoc import show_doc

def get_func(t, name, *args, **kwargs):
    "Get the `t.name` (potentially partial-ized with `args` and `kwargs`) or `noop` if not defined"
    f = getattr(t, name, noop)
    return f if not (args or kwargs) else partial(f, *args, **kwargs)

def show_title(o, ax=None, ctx=None):
    "Set title of `ax` to `o`, or print `o` if `ax` is `None`"
    ax = ifnone(ax,ctx)
    if ax is None: print(o)
    else: ax.set_title(o)

class Func():
    "Basic wrapper around a `name` with `args` and `kwargs` to call on a given type"
    def __init__(self, name, *args, **kwargs): self.name,self.args,self.kwargs = name,args,kwargs
    def __repr__(self): return f'sig: {self.name}({self.args}, {self.kwargs})'
    def _get(self, t): return get_func(t, self.name, *self.args, **self.kwargs)
    def __call__(self,t): return L(t).mapped(self._get) if is_listy(t) else self._get(t)

class _Sig():
    def __getattr__(self,k):
        def _inner(*args, **kwargs): return Func(k, *args, **kwargs)
        return _inner

Sig = _Sig()

class SelfFunc():
    "Search for `name` attribute and call it with `args` and `kwargs` on any object it's passed."
    def __init__(self, nm, *args, **kwargs): self.nm,self.args,self.kwargs = nm,args,kwargs
    def __repr__(self): return f'self: {self.nm}({self.args}, {self.kwargs})'
    def __call__(self, o):
        if not is_listy(o): return getattr(o,self.nm)(*self.args, **self.kwargs)
        else: return [getattr(o_,self.nm)(*self.args, **self.kwargs) for o_ in o]

class _SelfFunc():
    def __getattr__(self,k):
        def _inner(*args, **kwargs): return SelfFunc(k, *args, **kwargs)
        return _inner

Self = _SelfFunc()

def positional_annotations(f):
    "Get list of annotated types for all positional params, or None if no annotation"
    sig = inspect.signature(f)
    return [p.annotation if p.annotation != inspect._empty else None
            for p in sig.parameters.values() if p.default == inspect._empty and p.kind != inspect._VAR_KEYWORD]

def _filter_with_type(f, t):
    if is_listy(f):
        # Already defined list of functions of appropriate length
        assert len(f)==len(t)
        return f
    t_in = positional_annotations(f)
    if len(t_in) > 1:
        # Multiple positional params, so needs to match num types
        assert len(t_in)==len(t)
        return f
    t_in = t_in[0]  # there's only one positional param
    # We have one param, and multiple types, so we mask (noop) where types don't match
    return [f if t_ is None or t_in is None or issubclass(t_,t_in) else noop for t_ in t]

class Transform(PrePostInit):
    "A function that `encodes` if `filt` matches, and optionally `decodes`"
    order,filt = 0,None
    def __init__(self,encodes=None,decodes=None):
        self.encodes = getattr(self, 'encodes', noop) if encodes is None else encodes
        self.decodes = getattr(self, 'decodes', noop) if decodes is None else decodes

    def _apply(self, fs, x, filt):
        if self.filt is not None and self.filt!=filt: return x
        if is_listy(fs): return tuple(f(x_) for f,x_ in zip(fs,x))
        return fs(*L(x))

    def __call__(self, x, filt=None): return self._apply(self.encodes, x, filt)
    def decode  (self, x, filt=None): return self._apply(self.decodes, x, filt)
    def __getitem__(self, x): return self(x) # So it can be used as a `Dataset`

    def _filter_with_type(self, t):
        if is_listy(t): self.encodes = _filter_with_type(self.encodes, t)
        if is_listy(t): self.decodes = _filter_with_type(self.decodes, t)

add_docs(Transform,
         __call__="Call `self.encodes` unless `filt` is passed and it doesn't match `self.filt`",
         decode  ="Call `self.decodes` unless `filt` is passed and it doesn't match `self.filt`")

def mk_func(f, t):
    "Make `f` a function with type `t`"
    if isinstance(f,str ): f = Func(f)
    if isinstance(f,Func): f = f(t)
    return f

def mk_tfm(f,t):
    "Make `f` a transform with type `t`"
    if not is_listy(f): f = (f,None)
    return Transform(mk_func(f[0],t), mk_func(f[1],t))

def compose_tfms(x, tfms, func_nm='__call__', reverse=False, **kwargs):
    "Apply all `func_nm` attribute of `tfms` on `x`, naybe in `reverse` order"
    if reverse: tfms = reversed(tfms)
    for tfm in tfms: x = getattr(tfm,func_nm,noop)(x, **kwargs)
    return x

def _get_ret(func):
    "Get the return annotation of `func`"
    ann = getattr(func,'__annotations__', None)
    if not ann: return None
    return ann.get('return')

class Pipeline():
    "A pipeline of composed (for encode/decode) transforms, setup with types"
    def __init__(self, funcs=None): self.raw_fs = L(funcs)
    def __repr__(self): return f"Pipeline over {self.tfms}"

    def setup(self, t=None):
        self.fs,self.t_show = [],None
        if len(self.raw_fs) == 0: self.final_t = t
        else:
            for i,f in enumerate(self.raw_fs.sorted(key='order')):
                if not isinstance(f,Transform): f = mk_tfm(f, t)
                f._filter_with_type(t)
                self.fs.append(f)
                if hasattr(t, 'show') and self.t_show is None:
                    self.t_idx,self.t_show = i,t
                t = _get_ret(f.encodes) or t
            if hasattr(t, 'show') and self.t_show is None:
                self.t_idx,self.t_show = i+1,t
            self.final_t = t

    def __call__(self, o, **kwargs): return compose_tfms(o, self.fs)
    def decode  (self, i, **kwargs): return compose_tfms(i, self.fs, func_nm='decode', reverse=True)

    def show(self, o, ctx=None, **kwargs):
        if self.t_show is None: return self.decode(o)
        o = compose_tfms(o, self.fs[self.t_idx:], func_nm='decode', reverse=True)
        return self.t_show.show(o, ctx=ctx, **kwargs)
    #def __getitem__(self, x): return self(x)
    #def decode_at(self, idx): return self.decode(self[idx])
    #def show_at(self, idx): return self.show(self[idx])

add_docs(Pipeline,
         __call__="Compose `__call__` of all `tfms` on `o`",
         decode="Compose `decode` of all `tfms` on `i`",
         show="Show item `o`",
         setup="Go through the transforms in order and propagate the type starting with `t`")