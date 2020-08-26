# Copyright (C) 2017-2020 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard, Andres Goens


import timeit
import hydra
import random
import numpy as np
import os

from pykpn.mapper.utils import SimulationManager, Statistics
from pykpn.mapper.random import RandomMapper
from pykpn.util import logging, plot
from pykpn.slx.mapping import export_slx_mapping
from pykpn.representations.representations import RepresentationType

log = logging.getLogger(__name__)

#TODO: Skip this cause representation object is needed?

class RandomWalkMapper(object):
    """Generates a full mapping via a random walk

    This class is used to generate a mapping for a given
    platform and KPN application, via a random walk through
    the mapping space.
    It produces multiple random mappings and simulates each mapping in
    order to find the 'best' mapping. As outlined below, the script expects
    multiple configuration parameters to be available.
    **Hydra Parameters**:
        * **jobs:** the number of parallel jobs
        * **num_operations:** the total number of mappings to be generated
    """

    def __init__(self, kpn, platform, config, num_iterations, progress, export_all, plot_distribution, visualize,
                 show_plots, radius, random_seed, record_statistics, parallel, dump_cache, chunk_size, jobs):
        """Generates a random mapping for a given platform and KPN application.
        Args:
           cfg(~omegaconf.dictconfig.DictConfig): the hydra configuration object
        """
        self.full_mapper = True
        self.kpn = kpn
        self.platform = platform
        self.random_mapper = RandomMapper(self.kpn, self.platform, random_seed=None)
        self.statistics = Statistics(log, len(self.kpn.processes()), record_statistics)
        self.out_dir = config['outdir']

        self.num_iterations = num_iterations
        self.export_all = export_all
        self.plot_distribution = plot_distribution
        self.show_plots = show_plots
        self.visualize = visualize
        self.dump_cache = dump_cache
        self.seed = random_seed
        if self.seed == 'None':
            self.seed = None
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)

        rep_type_str = config['representation']
        if rep_type_str not in dir(RepresentationType):
            log.exception("Representation " + rep_type_str + " not recognized. Available: " + ", ".join(
                dir(RepresentationType)))
            raise RuntimeError('Unrecognized representation.')
        else:
            representation_type = RepresentationType[rep_type_str]
            log.info(f"initializing representation ({rep_type_str})")
            self.rep_type = representation_type

            representation = (representation_type.getClassType())(self.kpn, self.platform, config)

        self.representation = representation

        self.simulation_manager = SimulationManager(representation, config)

    def generate_mapping(self):
        """ Generates a mapping via a random walk
        """
        start = timeit.default_timer()
        # Create a list of 'simulations'. These are later executed by multiple
        # worker processes.
        mappings = []

        for i in range(0, self.num_iterations):
            mapping = self.random_mapper.generate_mapping()
            mappings.append(mapping)
        tup = list(map(self.representation.toRepresentation, mappings))
        exec_times = self.simulation_manager.simulate(tup)
        best_result_idx = exec_times.index(min(exec_times))
        best_result = mappings[best_result_idx]
        stop = timeit.default_timer()
        log.info('Tried %d random mappings in %0.1fs' %
                 (len(exec_times), stop - start))
        # export all mappings if requested
        idx = 1

        if self.export_all:
            for mapping in mappings:
                mapping_name = 'rnd_%08d.mapping' % idx
                #FIXME: We assume an slx output here, this should be configured
                export_slx_mapping(mapping, os.path.join(self.out_dir, mapping_name))
                idx += 1

        # plot result distribution
        if self.plot_distribution:
            import matplotlib.pyplot as plt
            # exec time in milliseconds
            plt.hist(exec_times, bins=int(self.num_iterations / 20), density=True)
            plt.yscale('log', nonposy='clip')
            plt.title("Mapping Distribution")
            plt.xlabel("Execution Time [ms]")
            plt.ylabel("Probability")

            if self.show_plots:
                plt.show()

            plt.savefig("distribution.pdf")

        # visualize searched space
        if self.visualize:

            plot.visualize_mapping_space(mappings,
                                         exec_times,
                                         representation_type=self.rep_type,
                                         show_plot=self.show_plots, )

        self.simulation_manager.statistics.to_file()
        if self.dump_cache:
            self.simulation_manager.dump('mapping_cache.csv')

        return best_result
