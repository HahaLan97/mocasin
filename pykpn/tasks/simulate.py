# Copyright (C) 2019 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard

import hydra
import logging
import simpy
import timeit

from pykpn.simulate.application import RuntimeKpnApplication
from pykpn.simulate.system import RuntimeSystem

log = logging.getLogger(__name__)


@hydra.main(config_path='conf/simulate.yaml')
def simulate(cfg):
    """Simulate the execution of a KPN application mapped to a platform.

    This script expects a configuration file as the first positional argument.
    It constructs a system according to this configuration and simulates
    it. Finally, the script reports the simulated execution time.

    This task expects four hydra parameters to be available.

    Args:
        cfg(~omegaconf.dictconfig.DictConfig): the hydra configuration object

    **Hydra Parameters**:
        * **kpn:** the input kpn graph. The task expects a configuration dict
          that can be instantiated to a :class:`~pykpn.common.kpn.KpnGraph`
          object.
        * **platform:** the input platform. The task expects a configuration
          dict that can be instantiated to a
          :class:`~pykpn.common.platform.Platform` object.
        * **mapping:** the input mapping. The task expects a configuration dict
          that can be instantiated to a :class:`~pykpn.common.mapping.Mapping`
          object.
        * **trace:** the input trace. The task expects a configuration dict
          that can be instantiated to a
          :class:`~pykpn.common.trace.TraceGenerator` object.
    """

    platform = hydra.utils.instantiate(cfg['platform'])

    env = simpy.Environment()
    system = RuntimeSystem(platform, env)

    system._env.process(single_kpn_simulation(system, env, cfg))

    start = timeit.default_timer()
    system.simulate()
    stop = timeit.default_timer()

    exec_time = float(env.now) / 1000000000.0
    print('Total simulated time: ' + str(exec_time) + ' ms')
    print('Total simulation time: ' + str(stop - start) + ' s')

    system.trace_writer.write_trace(cfg['simulation_trace'])


def single_kpn_simulation(system, env, cfg):
    kpn = hydra.utils.instantiate(cfg['kpn'])
    mapper = hydra.utils.instantiate(cfg['mapper'], kpn, system.platform, cfg)
    mapping = mapper.generate_mapping()
    trace = hydra.utils.instantiate(cfg['trace'])
    app = RuntimeKpnApplication(name=kpn.name,
                                kpn_graph=kpn,
                                mapping=mapping,
                                trace_generator=trace,
                                system=system)
    yield app.run()
