# Copyright (C) 2019 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard

import hydra
import logging
import timeit


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

    simulation = hydra.utils.instantiate(cfg.simulation_type, cfg)

    log.info('Start the simulation')
    start = timeit.default_timer()
    simulation.run()
    stop = timeit.default_timer()
    log.info('Simulation done')

    exec_time = float(simulation.exec_time) / 1000000000.0
    print('Total simulated time: ' + str(exec_time) + ' ms')
    print('Total simulation time: ' + str(stop - start) + ' s')

    simulation.write_simulation_trace(cfg['simulation_trace'])
