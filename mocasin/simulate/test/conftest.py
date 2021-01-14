# Copyright (C) 2017 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard


import simpy

import pytest
from mocasin.common.mapping import ChannelMappingInfo
from mocasin.simulate.application import RuntimeApplication
from mocasin.simulate.channel import RuntimeChannel
from mocasin.simulate.process import (RuntimeKpnProcess, RuntimeProcess,
                                    ProcessState)


@pytest.fixture
def env():
    return simpy.Environment()


@pytest.fixture
def system(env, mocker):
    m = mocker.Mock()
    m.env = env
    return m


@pytest.fixture(params=ProcessState.__members__)
def state(request):
    return request.param


@pytest.fixture
def app(system):
    return RuntimeApplication("test_app", system)


@pytest.fixture
def base_process(app):
    return RuntimeProcess('test_proc', app)


@pytest.fixture
def kpn_process(app, mocker):
    return RuntimeKpnProcess('test_proc', mocker.Mock(), app)


@pytest.fixture
def channel(app, mocker):
    info = ChannelMappingInfo(mocker.Mock(), 4)
    return RuntimeChannel('test_chan', info, 8, app)


@pytest.fixture
def processor(mocker):
    processor = mocker.Mock()
    processor.name = 'Test'
    processor.ticks = lambda x: x
    return processor


@pytest.fixture(params=['base', 'kpn'])
def process(request, base_process, kpn_process, mocker):
    if request.param == 'base':
        proc = base_process
    elif request.param == 'kpn':
        proc = kpn_process
    else:
        raise ValueError('Unexpected fixture parameter')

    proc.workload = mocker.Mock()
    return proc