# Copyright (C) 2019 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Andrés Goens, Robert Khasanov

from dataclasses import dataclass
import enum
import pickle
import random

import deap
from deap import algorithms, base, creator, tools  # noqa
import numpy as np

from mocasin.mapper import BaseMapper
from mocasin.mapper.pareto import filter_pareto_front
from mocasin.mapper.random import RandomPartialMapper
from mocasin.mapper.utils import SimulationManager, SimulationManagerConfig
from mocasin.util import logging


log = logging.getLogger(__name__)


class Objectives(enum.Flag):
    """Objective flags for multi-objective design-space exploration."""

    NONE = 0
    EXEC_TIME = enum.auto()
    RESOURCES = enum.auto()
    ENERGY = enum.auto()

    @classmethod
    def from_string_list(cls, objectives):
        """Initialize Objectives object from a list of strings"""
        flags = Objectives.NONE
        for obj in objectives:
            if obj == "exec_time":
                flags |= cls.EXEC_TIME
                continue
            if obj == "energy":
                flags |= cls.ENERGY
                continue
            if obj == "resources":
                flags |= cls.RESOURCES
                continue
            raise RuntimeError(f"Unexpected objective {obj}")
        return flags


@dataclass
class _GeneticMapperConfig:
    """Class for keeping genetic mapper settings."""

    initials: str
    objectives: Objectives
    pop_size: int
    num_gens: int
    mutpb: float
    cxpb: float
    tournsize: int
    mupluslambda: bool
    crossover_rate: int
    radius: float
    progress: bool


class _GeneticMapperEngine:
    """This class performs the genetic algorithm.

    This class initializes DEAP components and runs directly the genetic
    algorithm. The objects of this class are created by GeneticMapper for each
    application/trace/platform combination.

    Args:
        platform (Platform): a platform
        graph (DataflowGraph): a dataflow graph
        trace (TraceGenerator): a trace generator
        representation (MappingRepresentation): a mapping representation object
        simulation_manager (SimulationManager): a simulation manager
        config (_GeneticMapperConfig): a genetic mapper configuration
    """

    def __init__(
        self, platform, graph, trace, representation, simulation_manager, config
    ):
        self.platform = platform
        self.graph = graph
        self.trace = trace
        self.representation = representation
        self.simulation_manager = simulation_manager
        self.config = config

        self.random_mapper = RandomPartialMapper(
            self.platform,
            resources_first=Objectives.RESOURCES in self.config.objectives,
        )
        if "FitnessMin" not in deap.creator.__dict__:
            num_params = 0
            if Objectives.EXEC_TIME in self.config.objectives:
                num_params += 1
            if Objectives.ENERGY in self.config.objectives:
                num_params += 1
            if Objectives.RESOURCES in self.config.objectives:
                num_params += len(self.platform.get_processor_types())
            # this will weigh a milisecond as equivalent to an additional core
            # todo: add a general parameter for controlling weights
            deap.creator.create(
                "FitnessMin", deap.base.Fitness, weights=num_params * (-1.0,)
            )

        if "Individual" not in deap.creator.__dict__:
            deap.creator.create(
                "Individual", list, fitness=deap.creator.FitnessMin
            )

        toolbox = deap.base.Toolbox()
        toolbox.register("attribute", random.random)
        toolbox.register("mapping", self._random_mapping)
        toolbox.register(
            "individual",
            deap.tools.initIterate,
            deap.creator.Individual,
            toolbox.mapping,
        )
        toolbox.register(
            "population", deap.tools.initRepeat, list, toolbox.individual
        )
        toolbox.register("mate", self._mapping_crossover)
        toolbox.register("mutate", self._mapping_mutation)
        toolbox.register("evaluate", self._evaluate_mapping)
        toolbox.register(
            "select", deap.tools.selTournament, tournsize=self.config.tournsize
        )
        self.evolutionary_toolbox = toolbox

        # todo: we could add symmetry comparison (or other similarity) here
        self.hof = deap.tools.ParetoFront()

        stats = deap.tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("std", np.std)
        stats.register("min", np.min)
        stats.register("max", np.max)
        self.evolutionary_stats = stats

        if self.config.initials == "random":
            self.population = toolbox.population(n=self.config.pop_size)
        else:
            log.error("Initials not supported yet")
            raise RuntimeError("GeneticMapper: Initials not supported")

        pass

    def _evaluate_mapping(self, mapping):
        result = []
        simres = self.simulation_manager.simulate(
            self.graph, self.trace, self.representation, [list(mapping)]
        )[0]
        if Objectives.EXEC_TIME in self.config.objectives:
            result.append(simres.exec_time)
        if Objectives.ENERGY in self.config.objectives:
            result.append(simres.dynamic_energy+simres.static_energy)
        if Objectives.RESOURCES in self.config.objectives:
            mapping_obj = self.representation.fromRepresentation(list(mapping))
            resource_dict = mapping_obj.to_resourceDict()
            for core_type in resource_dict:
                result.append(resource_dict[core_type])
        return tuple(result)

    def _random_mapping(self):
        mapping = self.random_mapper.generate_mapping(
            self.graph, trace=self.trace, representation=self.representation
        )
        if (
            hasattr(self.representation, "canonical_operations")
            and not self.representation.canonical_operations
        ):
            as_rep = self.representation.toRepresentationNoncanonical(mapping)
        else:
            as_rep = self.representation.toRepresentation(mapping)
        return list(as_rep)

    def _mapping_crossover(self, m1, m2):
        return self.representation._crossover(
            m1, m2, self.config.crossover_rate
        )

    def _mapping_mutation(self, mapping):
        # m_obj = self.representation.fromRepresentation(list((mapping)))
        radius = self.config.radius
        while 1:
            new_mappings = self.representation._uniformFromBall(
                mapping, radius, 20
            )
            for m in new_mappings:
                if list(m) != list(mapping):
                    for i in range(len(mapping)):
                        # we do this since mapping is a DEAP Individual data
                        # structure
                        mapping[i] = m[i]
                    return (mapping,)
            radius *= 1.1
            if radius > 10000 * self.config.radius:
                log.error("Could not mutate mapping")
                raise RuntimeError("Could not mutate mapping")

    def run(self):
        if self.config.crossover_rate > len(self.graph.processes()):
            log.error(
                "Crossover rate cannot be higher than number of processes "
                "in application"
            )
            raise RuntimeError("Invalid crossover rate")

        toolbox = self.evolutionary_toolbox
        stats = self.evolutionary_stats
        hof = self.hof
        pop_size = self.config.pop_size

        if self.config.mupluslambda:
            ea_algo = deap.algorithms.eaMuPlusLambda
        else:
            ea_algo = deap.algorithms.eaMuCommaLambda

        population, logbook = ea_algo(
            self.population,
            toolbox,
            mu=pop_size,
            lambda_=3 * pop_size,
            cxpb=self.config.cxpb,
            mutpb=self.config.mutpb,
            ngen=self.config.num_gens,
            stats=stats,
            halloffame=hof,
            verbose=self.config.progress,
        )
        log.info(logbook.stream)

        return population, logbook, hof

    def cleanup(self):
        log.info("cleaning up")
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


class GeneticMapper(BaseMapper):
    """Generates a full mapping by using genetic algorithms.

    Args:
        platform (Platform): A platform
        initials (str, optional): What initial population to use. Defaults to
            "random".
        objectives (:obj:`list` of :obj:`str`, optional): Optimization
            objectives. Defaults to ["exec_time"].
        pop_size (int, optional): Population size. Defaults to 10.
        num_gens (int, optional): Number of generations. Defaults to 5.
        mutpb (float, optional): Probability of mutation. Defaults to 0.5.
        cxpb (float, optional): Crossover probability. Defaults to 0.35.
        tournsize (int, optional): Size of tournament for selection.
            Defaults to 4.
        mupluslambda (bool, optional): Use mu+lambda algorithm?
            If False: mu,lambda. Defaults to True.
        crossover_rate (int, optional): The number of crossovers in the
            crossover operator. Defaults to 1.
        radius (float, optional): The radius for searching mutations.
            Defaults to 2.0.
        random_seed (int, optional): A random seed for the RNG. Defautls to 42.
        record_statistics (bool, optional): Record statistics on mappings
            evaluated? Defautls to False.
        dump_cache (bool, optional): Dump the mapping cache? Defaults to False.
        chunk_size (int, optional): Size of chunks for parallel simulation.
            Defaults to 10.
        progress (bool, optional): Display simulation progress visually?
            Defaults to False.
        parallel (bool, optional): Execute simulations in parallel?
            Defaults to True.
        jobs (int, optional): Number of jobs for parallel simulation.
            Defaults to 4.
    """

    def __init__(
        self,
        platform,
        initials="random",
        objectives=["exec_time"],
        pop_size=10,
        num_gens=5,
        mutpb=0.5,
        cxpb=0.35,
        tournsize=4,
        mupluslambda=True,
        crossover_rate=1,
        radius=2.0,
        random_seed=42,
        record_statistics=False,
        dump_cache=False,
        chunk_size=10,
        progress=False,
        parallel=True,
        jobs=4,
    ):
        super().__init__(platform, full_mapper=True)
        random.seed(random_seed)
        np.random.seed(random_seed)

        self._dump_cache = dump_cache

        objs = Objectives.from_string_list(objectives)

        if Objectives.ENERGY in objs:
            if not self.platform.has_power_model():
                log.warning(
                    "The platform does not have a power model, excluding "
                    "energy consumption from the objectives."
                )
                objs ^= Objectives.ENERGY

        if objs == Objectives.NONE:
            raise RuntimeError(
                "Trying to initalize genetic algorithm without objectives"
            )

        self._mapper_config = _GeneticMapperConfig(
            initials,
            objs,
            pop_size,
            num_gens,
            mutpb,
            cxpb,
            tournsize,
            mupluslambda,
            crossover_rate,
            radius,
            progress,
        )
        simulation_config = SimulationManagerConfig(
            jobs=jobs,
            parallel=parallel,
            progress=progress,
            chunk_size=chunk_size,
        )
        self._simulation_manager = SimulationManager(
            self.platform, simulation_config
        )
        self._record_statistics = record_statistics

    def _init_deap_engine(self):
        pass

    def generate_mapping(
        self,
        graph,
        trace=None,
        representation=None,
        processors=None,
        partial_mapping=None,
    ):
        """Generate a full mapping using a genetic algorithm.

        Args:
            graph (DataflowGraph): a dataflow graph
            trace (TraceGenerator, optional): a trace generator
            representation (MappingRepresentation, optional): a mapping
                representation object
            processors (:obj:`list` of :obj:`Processor`, optional): a list of
                processors to map to.
            partial_mapping (Mapping, optional): a partial mapping to complete

        Returns:
            Mapping: the generated mapping.
        """
        self._simulation_manager.reset_statistics()
        engine = _GeneticMapperEngine(
            self.platform,
            graph,
            trace,
            representation,
            self._simulation_manager,
            self._mapper_config,
        )

        _, logbook, hof = engine.run()
        mapping = hof[0]
        self._simulation_manager.statistics.log_statistics()
        with open("evolutionary_logbook.txt", "w") as f:
            f.write(str(logbook))
        result = representation.fromRepresentation(np.array(mapping))
        if self._record_statistics:
            self._simulation_manager.statistics.to_file()
        if self._dump_cache:
            self._simulation_manager.dump("mapping_cache.csv")
        engine.cleanup()
        return result

    def generate_pareto_front(
        self, graph, trace=None, representation=None, **kwargs
    ):
        """Generates a pareto front of (full) mappings using a genetic algorithm
        the input parameters determine the criteria with which the pareto
        front is going to be built.

        Args:
            graph (DataflowGraph): a dataflow graph
            trace (TraceGenerator, optional): a trace generator
            representation (MappingRepresentation, optional): a mapping
                representation object
            **kwargs: Arbitrary keyword arguments.

        Returns:
           :obj:`lst` of :obj:`Mapping`: the list of generated mappings
        """
        self._simulation_manager.reset_statistics()
        engine = _GeneticMapperEngine(
            self.platform,
            graph,
            trace,
            representation,
            self._simulation_manager,
            self._mapper_config,
        )

        _, logbook, hof = engine.run()

        results = []
        self._simulation_manager.statistics.log_statistics()
        with open("evolutionary_logbook.pickle", "wb") as f:
            pickle.dump(logbook, f)
        for mapping in hof:
            mapping_object = representation.fromRepresentation(
                np.array(mapping)
            )
            results.append(mapping_object)
        self._simulation_manager.simulate(graph, trace, representation, results)

        pareto = filter_pareto_front(results)
        if self._record_statistics:
            self._simulation_manager.statistics.to_file()
        if self._dump_cache:
            self._simulation_manager.dump("mapping_cache.csv")
        engine.cleanup()
        return pareto
