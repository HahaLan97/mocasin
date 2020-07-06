import pytest
import numpy as np
from pykpn.common.kpn import KpnGraph, KpnProcess
from pykpn.common.platform import Platform, Processor, Scheduler
from pykpn.common.mapping import Mapping
from scipy.linalg import sqrtm
from unittest.mock import Mock
from pykpn.design_centering.volume import *
import pykpn.design_centering.sample as sample

@pytest.fixture
def Q_not_rotated():
    return np.array(sqrtm(np.array([[3., 0.], [0., 1 / 3.]])))


@pytest.fixture
def Q():
    return np.array(
        sqrtm(np.array([[1.66666667, 1.33333333], [1.33333333, 1.66666667]])))  # same as above, rotated 45^\circ


@pytest.fixture
def num_procs():
    return 50


@pytest.fixture
def target_p():
    return 0.65


@pytest.fixture
def seed():
    return 42


@pytest.fixture
def mu():
    return [15, 13]


@pytest.fixture
def num_samples():
    return 200


@pytest.fixture
def num_iter():
    return 100


@pytest.fixture
def r():
    return 3


@pytest.fixture
def r_set():
    return 3


@pytest.fixture
def r_small():
    return 1


@pytest.fixture
def kpn():
    k = KpnGraph('a')
    k.add_process(KpnProcess('a'))
    k.add_process(KpnProcess('b'))
    return k


@pytest.fixture
def platform(num_procs):
    p = Platform('platform')
    procs = []
    for i in range(num_procs):
        proc = Processor(('processor' + str(i)), 'proctype', Mock())
        procs.append(proc)
        p.add_processor(proc)
    policies = [Mock()]
    sched = Scheduler('name', procs, policies)
    p.add_scheduler(sched)
    return p


@pytest.fixture
def point():
    return [1, 2]


@pytest.fixture
def center(kpn, platform, point):
    m = Mapping(kpn, platform)
    m.from_list(point)
    return m


@pytest.fixture
def center_mu(kpn, platform, mu):
    m = Mapping(kpn, platform)
    m.from_list(mu)
    return m


@pytest.fixture
def dim():
    return 2


@pytest.fixture
def lp_vol(center, point, kpn, platform, dim, conf):
    vol = LPVolume(center, dim, kpn, platform, conf)
    return vol


@pytest.fixture
def vol_mu(center_mu, kpn, platform, dim, conf):
    vol = LPVolume(center_mu, dim, kpn, platform, conf)
    return vol


@pytest.fixture
def s_set():
    result = sample.SampleSet()
    n = 5
    for i in range(n):
        s = sample.Sample(sample=[i, i])
        s.setFeasibility(True)
        result.add_sample(s)

        s = sample.Sample(sample=[-i, i])
        s.setFeasibility(False)
        result.add_sample(s)
    return result

@pytest.fixture
def oracle():
    return MockOracle

# custom class to be the mock for the oracle and simulation environment for DC
class MockOracle(object):
    @staticmethod
    def validate_set(samples):
        for s in samples:
            s.setFeasibility(True)
        return samples

#https://stackoverflow.com/questions/4984647/accessing-dict-keys-like-an-attribute
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


@pytest.fixture
def conf(num_samples):
    #center movement should probably work without aggressive movement (fix this in dc branch)
    return AttrDict({'adapt_samples' : num_samples,
    'max_step': 10,
    'max_samples' : 50,
    'max_step' : 10,
    'adaptable_center_weights' : False , 
    'radius' : 7,
    'representation' : 'SimpleVector',
    'channels' : False,
    'norm_p' : 2,
    'aggressive_center_movement' : True,
    'periodic_boundary_conditions' : False , 
    'distr' : 'uniform', 
    'record_samples' : False,
    'visualize_mappings' : False,
    'show_polynomials' : False,
    'deg_p_polynomial' : 2,
    'deg_s_polynomial' : 2,
    'step_width' : [0.9, 0.7, 0.6, 0.5, 0.1],
    'hitting_probability' : [0.4, 0.5, 0.5, 0.7, 0.9],
    'hitting_probability_threshold' : 0.7})
