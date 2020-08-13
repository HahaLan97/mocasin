# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Andrés Goens

import random
import numpy as np

from pykpn.util import logging
from pykpn.representations.representations import RepresentationType
from pykpn.mapper.random import RandomPartialMapper
from pykpn.mapper.utils import SimulationManager
from pykpn.mapper.utils import Statistics


log = logging.getLogger(__name__)


class SimulatedAnnealingMapper(object):
    """Generates a full mapping by using a simulated annealing algorithm from:
    Orsila, H., Kangas, T., Salminen, E., Hämäläinen, T. D., & Hännikäinen, M. (2007).
    Automated memory-aware application distribution for multi-processor system-on-chips.
    Journal of Systems Architecture, 53(11), 795-815.e.
    """
    def __init__(self, kpn,platform,config):
        """Generates a full mapping for a given platform and KPN application.

        :param kpn: a KPN graph
        :type kpn: KpnGraph
        :param platform: a platform
        :type platform: Platform
        :param config: the hyrda configuration
        :type config: OmniConf
        """
        random.seed(config['random_seed'])
        np.random.seed(config['random_seed'])
        self.full_mapper = True # flag indicating the mapper type
        self.kpn = kpn
        self.platform = platform
        self.config = config
        self.random_mapper = RandomPartialMapper(self.kpn,self.platform,config,seed=None)
        self.initial_temperature = config['initial_temperature']
        self.final_temperature = config['final_temperature']
        self.max_rejections = len(self.kpn.processes()) * (len(self.platform.processors()) - 1) #R_max = L
        self.p = config['temperature_proportionality_constant']
        if not (self.p < 1 and self.p > 0):
            log.error(f"Temperature proportionality constant {self.p} not suitable, "
                      f"it should be close to, but smaller than 1 (algorithm probably won't terminate).")


        rep_type_str = config['representation']

        if rep_type_str not in dir(RepresentationType):
            log.exception("Representation " + rep_type_str + " not recognized. Available: " + ", ".join(
                dir(RepresentationType)))
            raise RuntimeError('Unrecognized representation.')
        else:
            representation_type = RepresentationType[rep_type_str]
            log.info(f"initializing representation ({rep_type_str})")

            representation = (representation_type.getClassType())(self.kpn, self.platform,self.config)

        self.representation = representation
        self.simulation_manager = SimulationManager(representation, config)

    def temperature_cooling(self,temperature,iter):
        return self.initial_temperature*self.p**np.floor(iter/self.max_rejections)

    def query_accept(self,time,temperature):
        normalized_probability = 1 / (np.exp(time/(0.5*temperature*self.initial_cost)))
        return normalized_probability

    def move(self,mapping,temperature):
        radius = self.config['radius']
        while(1):
            new_mappings = self.representation._uniformFromBall(mapping,radius,20)
            for m in new_mappings:
                if list(m) != list(mapping):
                    return m
            radius *= 1.1
            if radius > 10000 * self.config['radius']:
                log.error("Could not mutate mapping")
                raise RuntimeError("Could not mutate mapping")


    def generate_mapping(self):
        """ Generates a full mapping using simulated anealing
        """
        mapping_obj = self.random_mapper.generate_mapping()
        mapping = self.representation.toRepresentation(mapping_obj)

        last_mapping = mapping
        last_exec_time = self.simulation_manager.simulate([mapping])[0]
        self.initial_cost = last_exec_time
        best_mapping = mapping
        best_exec_time = last_exec_time
        rejections = 0

        iter = 0
        temperature = self.initial_temperature
        while rejections < self.max_rejections:
            temperature = self.temperature_cooling(temperature,iter)
            log.info(f"Current temperature {temperature}")
            mapping = self.move(last_mapping,temperature)
            cur_exec_time = self.simulation_manager.simulate([mapping])[0]
            faster = cur_exec_time < last_exec_time
            if not faster and cur_exec_time != last_exec_time:
                prob = self.query_accept(cur_exec_time - last_exec_time, temperature)
                rand = random.random()
                accept_randomly = prob > rand
            else:
                accept_randomly = False #don't accept if no movement.
            if faster or accept_randomly:
                #accept
                if cur_exec_time < best_exec_time:
                    best_exec_time = cur_exec_time
                    best_mapping = mapping
                last_mapping = mapping
                last_exec_time = cur_exec_time
                rejections = 0
            else:
                #reject
                if temperature <= self.final_temperature:
                    rejections += 1
            iter += 1
        self.simulation_manager.statistics.log_statistics()
        self.simulation_manager.statistics.to_file()
        if self.config['dump_cache']:
            self.simulation_manager.dump('mapping_cache.csv')

        return self.representation.fromRepresentation(best_mapping)