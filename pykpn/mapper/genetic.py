# Copyright (C) 2019 TU Dresden
# All Rights Reserved
#
# Authors: Andrés Goens

import deap
import random
import numpy as np
import pickle
import hydra

from pykpn.util import logging
from pykpn.representations.representations import RepresentationType
from pykpn.mapper.utils import SimulationManager
from pykpn.mapper.random import RandomPartialMapper

from deap import creator, tools, base, algorithms

log = logging.getLogger(__name__)

#TODO: Skip this cause representation object is needed?

class GeneticMapper(object):
    """Generates a full mapping by using genetic algorithms.
    """
    def __init__(self, kpn, platform, config, pop_size, num_gens, cxpb, mutpb, tournsize, mupluslambda, initials,
                 radius, random_seed, crossover_rate, record_statistics, dump_cache, chunk_size, progress, parallel, jobs):
        """Generates a partial mapping for a given platform and KPN application.

        :param kpn: a KPN graph
        :type kpn: KpnGraph
        :param platform: a platform
        :type platform: Platform
        :param config: the hyrda configuration
        :type fullGererator: OmniConf
        """
        random.seed(random_seed)
        np.random.seed(random_seed)
        self.full_mapper = True # flag indicating the mapper type
        self.kpn = kpn
        self.platform = platform
        self.config = config

        self.random_mapper = RandomPartialMapper(self.kpn, self.platform, seed=None)
        self.crossover_rate = crossover_rate
        self.tournsize = tournsize
        self.pop_size = pop_size
        self.initials = initials
        self.radius = radius
        self.num_gens = num_gens
        self.cxpb = cxpb
        self.mutb = mutpb
        self.dump_cache = dump_cache
        self.mupluslambda = mupluslambda

        if self.crossover_rate > len(self.kpn.processes()):
            log.error("Crossover rate cannot be higher than number of processes in application")
            raise RuntimeError("Invalid crossover rate")

        rep_type_str = config['representation']

        if rep_type_str not in dir(RepresentationType):
            log.exception("Representation " + rep_type_str + " not recognized. Available: " + ", ".join(
                dir(RepresentationType)))
            raise RuntimeError('Unrecognized representation.')
        else:
            representation_type = RepresentationType[rep_type_str]
            log.info(f"initializing representation ({rep_type_str})")

            representation = (representation_type.getClassType())(self.kpn, self.platform, self.config)

        self.representation = representation


        self.simulation_manager = SimulationManager(self.representation, config)

        if 'FitnessMin' not in deap.creator.__dict__:
            deap.creator.create("FitnessMin", deap.base.Fitness, weights=(-1.0,))

        if 'Individual' not in deap.creator.__dict__:
            deap.creator.create("Individual", list, fitness=deap.creator.FitnessMin)

        toolbox = deap.base.Toolbox()
        toolbox.register("attribute", random.random)
        toolbox.register("mapping", self.random_mapping)
        toolbox.register("individual", deap.tools.initIterate, deap.creator.Individual, toolbox.mapping)
        toolbox.register("population", deap.tools.initRepeat, list, toolbox.individual)
        toolbox.register("mate", self.mapping_crossover)
        toolbox.register("mutate", self.mapping_mutation)
        toolbox.register("evaluate", self.evaluate_mapping)
        toolbox.register("select", deap.tools.selTournament, tournsize=self.tournsize)

        self.evolutionary_toolbox = toolbox
        self.hof = deap.tools.HallOfFame(1)
        stats = deap.tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)
        self.evolutionary_stats = stats

        if self.initials:
            self.population = toolbox.population(n=self.pop_size)
        else:
            log.error("Initials not supported yet")
            raise RuntimeError('GeneticMapper: Initials not supported')
            #toolbox.register("individual_guess", self.initIndividual, creator.Individual)
            #toolbox.register("population_guess", self.initPopulation, list, toolbox.individual_guess, initials,pop_size)
            #population = toolbox.population_guess()

    def evaluate_mapping(self, mapping):
        #wrapper to make it into a 1-tuple because DEAP needs that
        return self.simulation_manager.simulate([list(mapping)])[0],

    def random_mapping(self):
        mapping = self.random_mapper.generate_mapping()
        as_rep = self.representation.toRepresentation(mapping)
        return list(as_rep)

    def mapping_crossover(self, m1, m2):
        return self.representation._crossover(m1, m2, self.crossover_rate)

    def mapping_mutation(self,mapping):
        #m_obj = self.representation.fromRepresentation(list((mapping)))
        radius = self.radius
        while(1):
            new_mappings = self.representation._uniformFromBall(mapping,radius,20)
            for m in new_mappings:
                if list(m) != list(mapping):
                    for i in range(len(mapping)):
                        #we do this since mapping is a DEAP Individual data structure
                        mapping[i] = m[i]
                    return mapping,
            radius *= 1.1
            if radius > 10000 * self.radius:
                log.error("Could not mutate mapping")
                raise RuntimeError("Could not mutate mapping")


    def run_genetic_algorithm(self):
        toolbox = self.evolutionary_toolbox
        stats = self.evolutionary_stats
        hof = self.hof
        pop_size = self.pop_size
        num_gens = self.num_gens
        cxpb = self.cxpb
        mutpb = self.mutb

        population = self.population

        if self.mupluslambda:
            population, logbook = deap.algorithms.eaMuPlusLambda(population, toolbox, mu=pop_size, lambda_=3*pop_size,
                                                                 cxpb=cxpb, mutpb=mutpb, ngen=num_gens, stats=stats,
                                                                 halloffame=hof, verbose=False)
            log.info(logbook.stream)
        else:
            population, logbook = deap.algorithms.eaMuCommaLambda(population, toolbox, mu=pop_size, lambda_=3*pop_size,
                                                                  cxpb=cxpb, mutpb=mutpb, ngen=num_gens, stats=stats,
                                                                  halloffame=hof, verbose=False)
            log.info(logbook.stream)

        return population, logbook, hof

    def generate_mapping(self):
        """ Generates a full mapping using a genetic algorithm
        """
        _, logbook, hof = self.run_genetic_algorithm()
        mapping = hof[0]
        self.simulation_manager.statistics.log_statistics()
        with open('evolutionary_logbook.pickle', 'wb') as f:
            pickle.dump(logbook, f)
        result = self.representation.fromRepresentation(np.array(mapping))
        self.simulation_manager.statistics.to_file()
        if self.dump_cache:
            self.simulation_manager.dump('mapping_cache.csv')
        self.cleanup()
        return result

    def cleanup(self):
        print("cleaning up")
        toolbox = self.evolutionary_toolbox
        toolbox.unregister("attribute")
        toolbox.unregister("mapping")
        toolbox.unregister("individual")
        toolbox.unregister("population")
        toolbox.unregister("mate")
        toolbox.unregister("mutate")
        toolbox.unregister("evaluate")
        toolbox.unregister("select")
        stats = self.evolutionary_stats
        self.evolutionary_stats = None
        del stats
        del deap.creator.FitnessMin
        del deap.creator.Individual
