# Copyright (C) 2017-2020 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Christian Menard, Andres Goens, Robert Khasanov

import random
import timeit

import numpy as np
import tqdm

from mocasin.mapper import BaseMapper
from mocasin.mapper.random import RandomMapper
from mocasin.mapper.utils import SimulationManager, SimulationManagerConfig
from mocasin.util import logging


log = logging.getLogger(__name__)


class RandomWalkMapper(BaseMapper):
    """Generates a full mapping via a random walk

    This class is used to generate a mapping for a given
    platform and dataflow application, via a random walk through
    the mapping space.
    It produces multiple random mappings and simulates each mapping in
    order to find the 'best' mapping. As outlined below, the script expects
    multiple configuration parameters to be available.
    """

    def __init__(
        self,
        platform,
        num_iterations=100,
        progress=False,
        radius=3.0,
        random_seed=42,
        record_statistics=False,
        parallel=False,
        dump_cache=False,
        chunk_size=10,
        jobs=1,
    ):
        """Generates a random mapping for a given platform and application.

        Args:
        :param platform: a platform
        :type platform: Platform
        :param random_seed: A random seed for the RNG
        :type random_seed: int
        :param record_statistics: Record statistics on mappings evaluated?
        :type record_statistics: bool
        :param num_iterations: Number of iterations (mappings) in random walk
        :type num_iterations: int
        :param rodius: Currently unused.
        :type radius: float
        :param dump_cache: Dump the mapping cache?
        :type dump_cache: bool
        :param chunk_size: Size of chunks for parallel simulation
        :type chunk_size: int
        :param progress: Display simulation progress visually?
        :type progress: bool
        :param parallel: Execute simulations in parallel?
        :type parallel: bool
        :param jobs: Number of jobs for parallel simulation
        :type jobs: int
        """
        super().__init__(platform, full_mapper=True)
        self.random_mapper = RandomMapper(
            self.platform,
            random_seed=None,
        )
        self.num_iterations = num_iterations
        self.dump_cache = dump_cache
        self.seed = random_seed
        self.progress = progress
        if self.seed == "None":
            self.seed = None
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)

        # save parameters to simulation manager
        simulation_config = SimulationManagerConfig(
            jobs=jobs,
            parallel=parallel,
            progress=progress,
            chunk_size=chunk_size,
        )
        self._simulation_manager = SimulationManager(
            self.platform, config=simulation_config
        )

        self._record_statistics = record_statistics

    def generate_mapping(
        self,
        graph,
        trace=None,
        representation=None,
        processors=None,
        partial_mapping=None,
    ):
        """Generate a mapping via a random walk.

        :param graph: a dataflow graph
        :type graph: DataflowGraph
        :param platform: a platform
        :type platform: Platform
        :param trace: a trace generator
        :type trace: TraceGenerator
        :param representation: a mapping representation object
        :type representation: MappingRepresentation
        """
        self._simulation_manager.reset_statistics()
        start = timeit.default_timer()
        # Create a list of 'simulations'. These are later executed by multiple
        # worker processes.
        mappings = []

        iterations_range = range(self.num_iterations)
        if self.progress:
            iterations_range = tqdm.tqdm(iterations_range)

        for i in iterations_range:
            mapping = self.random_mapper.generate_mapping(
                graph, trace=trace, representation=representation
            )
            mappings.append(mapping)

        if (
            hasattr(representation, "canonical_operations")
            and not representation.canonical_operations
        ):
            to_repr_func = representation.toRepresentationNoncanonical
        else:
            to_repr_func = representation.toRepresentation
        tup = list(map(to_repr_func, mappings))

        sim_results = self._simulation_manager.simulate(
            graph, trace, representation, tup
        )
        exec_times = [x.exec_time for x in sim_results]
        best_result_idx = exec_times.index(min(exec_times))
        best_result = mappings[best_result_idx]
        stop = timeit.default_timer()
        log.info(
            f"Tried {len(exec_times)} random mappings in {stop-start:.1f}s"
        )
        if self._record_statistics:
            self._simulation_manager.statistics.to_file()
        if self.dump_cache:
            self._simulation_manager.dump("mapping_cache.csv")

        return best_result
