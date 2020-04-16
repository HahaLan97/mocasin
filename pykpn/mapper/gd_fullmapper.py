# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Andres Goens

from pykpn.util import logging
from pykpn.representations.representations import RepresentationType
from pykpn.mapper.rand_partialmapper import RandomPartialMapper
from pykpn.simulate.application import RuntimeKpnApplication
from pykpn.simulate.system import RuntimeSystem
from pykpn.mapper.utils import Statistics, MappingCache
import deap
from deap import creator,tools,base,algorithms
import random
import numpy as np
import timeit
import simpy
import hydra

log = logging.getLogger(__name__)

class GradientDescentFullMapper(object):
    """Generates a full mapping by using a gradient descent on the mapping space.
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
        self.num_PEs = len(platform.processors())
        self.config = config
        self.random_mapper = RandomPartialMapper(self.kpn,self.platform,config,seed=None)
        self.gd_iterations = config['gd_iterations']
        self.stepsize = config['stepsize']
        self.statistics = Statistics(log, len(self.kpn.processes()), config['record_statistics'])
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
        self.mapping_cache = MappingCache(representation,config)

    def generate_mapping(self):
        """ Generates a full mapping using gradient descent
        """
        mapping_obj = self.random_mapper.generate_mapping()
        mapping = self.representation.toRepresentation(mapping_obj)

        dim = len(mapping)
        cur_exec_time = self.mapping_cache.evaluate_mapping(mapping)
        best_mapping = mapping
        best_exec_time = cur_exec_time

        for _ in range(self.gd_iterations):
            grad = np.zeros(dim)

            for i in range(dim):
                evec = np.zeros(dim)
                if mapping[i] == 0:
                    evec[i] = 1.
                    exec_time = self.mapping_cache.evaluate_mapping(mapping+evec)
                    if exec_time < best_exec_time:
                        best_exec_time = exec_time
                        best_mapping = mapping + evec
                    gr = exec_time - cur_exec_time
                    grad[i] = max(gr,0) #can go below 0 here
                elif mapping[i] == self.num_PEs - 1:
                    evec[i] = -1.
                    exec_time = self.mapping_cache.evaluate_mapping(mapping+evec)
                    if exec_time < best_exec_time:
                        best_exec_time = exec_time
                        best_mapping = mapping + evec
                    gr = cur_exec_time - exec_time# because of the -h in the denominator of the difference quotient
                    grad[i] = min(gr,0) #can't go above self.num_PEs-1 here

                else:
                    evec[i] = 1.
                    exec_time = self.mapping_cache.evaluate_mapping(mapping+evec)
                    if exec_time < best_exec_time:
                        best_exec_time = exec_time
                        best_mapping = mapping+evec
                    diff_plus = exec_time - cur_exec_time
                    evec[i] = -1.
                    exec_time = self.mapping_cache.evaluate_mapping(mapping+evec)
                    if exec_time < best_exec_time:
                        best_exec_time = exec_time
                        best_mapping = mapping+evec
                    diff_minus = cur_exec_time - exec_time # because of the -h in the denominator of the difference quotient
                    grad[i] = (diff_plus + diff_minus)/2

            if np.allclose(grad,np.zeros(dim)): #found local minimum
                break
            mapping = mapping + (self.stepsize / best_exec_time) * (-grad)
            mapping = self.representation.approximate(np.array(mapping))

            cur_exec_time = self.mapping_cache.evaluate_mapping(mapping)

            if cur_exec_time < best_exec_time:
                best_exec_time = cur_exec_time
                best_mapping = mapping

        best_mapping = np.array(self.representation.approximate(np.array(best_mapping)))
        self.statistics.log_statistics()
        self.statistics.to_file()

        return self.representation.fromRepresentation(best_mapping)



