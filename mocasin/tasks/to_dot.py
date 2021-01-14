# Copyright (C) 2019 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard

import hydra


@hydra.main(config_path='../conf', config_name='kpn_to_dot')
def kpn_to_dot(cfg):
    """Generate a dot graph from a KPN

    This simple task produces a dot graph that visualizes a given KPN. It
    expects two hydra parameters to be available.

    Args:
        cfg(~omegaconf.dictconfig.DictConfig): the hydra configuration object

    **Hydra Parameters**:
        * **kpn:** the input kpn graph. The task expects a configuration dict
          that can be instantiated to a :class:`~mocasin.common.kpn.KpnGraph`
          object.
        * **dot:** the output file
    """
    kpn = hydra.utils.instantiate(cfg['kpn'])
    kpn.to_pydot().write_raw(cfg['output_file'])


@hydra.main(config_path='../conf', config_name='platform_to_dot.yaml')
def platform_to_dot(cfg):
    """Generate a dot graph from a Platform

    This simple task produces a dot graph that visualizes a given Platform. It
    expects two hydra parameters to be available.

    Args:
        cfg(~omegaconf.dictconfig.DictConfig): the hydra configuration object

    **Hydra Parameters**:
        * **platform:** the input platform. The task expects a configuration
          dict that can be instantiated to a
          :class:`~mocasin.common.platform.Platform` object.
        * **dot:** the output file
    """
    platform = hydra.utils.instantiate(cfg['platform'])
    platform.to_pydot().write_raw(cfg['output_file'])


@hydra.main(config_path='../conf', config_name='mapping_to_dot.yaml')
def mapping_to_dot(cfg):
    """Generate a dot graph representing the mapping of a KPN application to a
    platform

    This task expects four hydra parameters to be available.

    **Hydra Parameters**:
        * **kpn:** the input kpn graph. The task expects a configuration dict
          that can be instantiated to a :class:`~mocasin.common.kpn.KpnGraph`
          object.
        * **platform:** the input platform. The task expects a configuration
          dict that can be instantiated to a
          :class:`~mocasin.common.platform.Platform` object.
        * **mapping:** the input mapping. The task expects a configuration dict
          that can be instantiated to a :class:`~mocasin.common.mapping.Mapping`
          object.
        * **dot:** the output file
    """
    kpn = hydra.utils.instantiate(cfg['kpn'])
    platform = hydra.utils.instantiate(cfg['platform'])
    trace = hydra.utils.instantiate(cfg['trace'])
    representation = hydra.utils.instantiate(cfg['representation'],kpn,platform)
    mapping = hydra.utils.instantiate(cfg['mapper'], kpn, platform,
                                      trace, representation).generate_mapping()

    mapping.to_pydot().write_raw(cfg['output_file'])