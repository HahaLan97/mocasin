import os
import timeit
import simpy
import traceback



import multiprocessing as mp
from pykpn.slx.config import SlxSimulationConfig
from pykpn.slx.kpn import SlxKpnGraph
from pykpn.slx.mapping import export_slx_mapping
from pykpn.slx.platform import SlxPlatform
from pykpn.slx.trace import SlxTraceReader
from pykpn import slx
from pykpn.simulate.application import RuntimeKpnApplication
from pykpn.simulate.system import RuntimeSystem
#from pykpn.mapper.random import RandomMapping
from pykpn.mapper.dc_mapgen import DC_MappingGenerator
from pykpn.mapper.rand_mapgen import RandomMappingGenerator
from pykpn.mapper.random import RandomMapping
from . import dc_sample
from . import dc_settings as conf

from sys import exit

class ApplicationContext(object):
    def __init__(self, name=None, kpn=None, mapping=None, trace_reader=None,
                 start_time=None):
        self.name = name
        self.kpn = kpn
        self.mapping = mapping
        self.trace_reader = trace_reader
        self.start_time = start_time


class SimulationContext(object):
    def __init__(self, platform=None, app_contexts=None):
        self.platform = platform
        if app_contexts is None:
            self.app_contexts = []
        else:
            self.app_contexts = app_contexts
        self.exec_time = None

class Oracle(object):
    def __init__(self, config=None):
        if conf.oracle == "TestSet":
             type(self).oracle = TestSet()
        elif conf.oracle == "TestTwoPrKPN":
             type(self).oracle = TestTwoPrKPN()
        elif conf.oracle == "simulation":
             type(self).oracle = Simulation(config)
        else:
             print("Error, unknown oracle:" + conf.oracle)
             exit(1)

    def validate(self, sample):
        """ check whether a single sample is feasible """
        res = type(self).oracle.is_feasible(sample.sample2tuple())

    def validate_set(self, samples):
        """ check whether a set of samples is feasible """
        # extra switch for evaluation of static sets vs. simulation
        res = []
        if conf.oracle != "simulation":
            for s in samples:
                res.append(type(self).oracle.is_feasible(s.sample2tuple()))
        else:
            res = type(self).oracle.is_feasible(samples)

        return res

class Simulation(object):
    """ simulation code """
    def __init__(self, config=None):
        type(self).sim_config = config

    def get_platform(self):
        conf = SlxSimulationConfig(self.sim_config)
        platform_name = os.path.splitext(os.path.basename(conf.platform_xml))[0]
        return  SlxPlatform(platform_name, conf.platform_xml, conf.slx_version)

    def get_kpns(self):
        conf = SlxSimulationConfig(type(self).sim_config)
        kpns = []
        for app_config in conf.applications:
            name = app_config.name
            kpns.append(SlxKpnGraph(name, app_config.cpn_xml, conf.slx_version))
        return kpns        

    def prepare_sim_contexts_for_samples(self, samples):
        """ Prepare simualtion/application context and mapping for a each element in `samples`. """
        # parse the config file

        config = SlxSimulationConfig(type(self).sim_config)

        #slx.set_version(config.slx_version)
        #create platform
        platform_name = os.path.splitext(os.path.basename(config.platform_xml))[0]
        platform = SlxPlatform(platform_name, config.platform_xml, config.slx_version)

        # Create a list of 'simulations'. 
        # These are later executed by multiple worker processes.
        simulation_contexts = []
        
        for i in range(0, len(samples)):
            # create a simulation context
            sim_context = SimulationContext(platform)
            
            # create the application contexts
            # assume there runs _one_ application only on the given platform
            assert len(config.applications) == 1
            app_config = config.applications[0]
            app_name = app_config.name
            kpn = SlxKpnGraph(app_name, app_config.cpn_xml, config.slx_version)
            app_context = ApplicationContext(app_name, kpn)
            app_context.start_time = app_config.start_at_tick
            
            # generate a mapping for the given sample
            print("using simcontext no.: {} {}".format(i,samples[i]))
            randMapGen = RandomMappingGenerator(kpn, platform)
            dcMapGen = DC_MappingGenerator(kpn, platform, randMapGen)
            #app_context.mapping = RandomMapping(kpn, platform)
            app_context.mapping = dcMapGen.generate_mapping(samples[i].sample2tuple())
            #app_context.mapping = randMapGen.generate_mapping(42, randMapGen.mapping)
            print("####### Mapping i={} toList: {}".format(i, app_context.mapping.to_list()))
            
            # create the trace reader
            app_context.trace_reader = SlxTraceReader.factory(
                app_config.trace_dir, '%s.' % (app_name), config.slx_version)
            
            sim_context.app_contexts.append(app_context)
            samples[i].setSimContext(sim_context)
            simulation_contexts.append(sim_context)
        return simulation_contexts

    def prepare_sim_context(self, platform, kpn, mapping):
        # parse the config file
        config = SlxSimulationConfig(type(self).sim_config)

        # create a simulation context
        sim_context = SimulationContext(platform)

        # create the application contexts (normally it is just one)
        app_config = config.applications[0]
        app_name = app_config.name
        app_context = ApplicationContext(app_name, kpn)
        app_context.start_time = app_config.start_at_tick
        app_context.mapping = mapping
            
        # create the trace reader
        app_context.trace_reader = SlxTraceReader.factory(
            app_config.trace_dir, '%s.' % (app_name), config.slx_version)
            
        sim_context.app_contexts.append(app_context)
        return sim_context

    def is_feasible(self, samples):
        """ Checks if a set of samples is feasible in context of a given timing threshold.
            
        Trigger the simulation on 4 for parallel jobs and process the resulting array 
        of simulation results according to the given threshold.
        """
        #prepare simulation
        results = []
        simulation_contexts = self.prepare_sim_contexts_for_samples(samples)
        
        # run the simulations and search for the best mapping
        # execute the simulations in parallel
        # TODO: this is somehow broken
        # pool = mp.Pool(processes=4)
        # results = list(pool.map(self.run_simulation, simulations, chunksize=4))
        # TODO read mapping from sim_contexts
        # this must be in simulation_contexts

        # results list of simulation contexts
        results = list(map(self.run_simulation, simulation_contexts))
        
        #find runtime from results
        exec_times = []
        for r in results:
            exec_times.append(float(r.exec_time / 1000000000.0))
        
        feasible = []
        for s in samples:
            if (s.getSimContext().exec_time / 1000000000.0 > conf.threshold):
                s.setFeasibility(False)
                feasible.append(False)
            else:
                s.setFeasibility(True)
                feasible.append(True)

        print("exec. Times: {} Feasible: {}".format(exec_times, feasible))
        # return smaples with the according sim context 
        return samples

    
    #do simulation requires sim_context,
    def run_simulation(self, sim_context):
        try:
            # Create simulation environment
            env = simpy.Environment()
    
            # create the applications
            applications = []
            mappings = {}
            for ac in sim_context.app_contexts:
                app = RuntimeKpnApplication(ac.name, ac.kpn, ac.mapping,
                                            ac.trace_reader, env, ac.start_time)
                applications.append(app)
                mappings[ac.name] = ac.mapping
    
            # Create the system
            system = RuntimeSystem(sim_context.platform, applications, env)
    
            # run the simulation
            system.simulate()
            system.check_errors()
            sim_context.exec_time = env.now

        except Exception as e:
            print("Exception in Simulation: {}".format(str(e)))
            traceback.print_exc()
            #log.exception(str(e))
            if hasattr(e, 'details'):
                log.info(e.details())
        return sim_context

# This is a temporary test class
class TestSet(object):
    # specify a fesability test set
    def is_feasible(self, s):
        """ test oracle function (2-dim) """
        #print("oracle for: " + str(s))
        if (len(s) != 2):
            print("test oracle requires a dimension of 2\n")
            exit(1)
        x = s[0]
        y = s[1]
        if ((x in range(1,3)) and (y in range(1,3))): # 1<=x<=2 1<=y<=2
            return True
        if ((x in range(1,4)) and (y in range(13,15))):
            return True
        if ((x in range(9,11)) and (y in range(9,11))):
            return False
        if ((x in range(7,13)) and (y in range(7,13))):
            return True
        else:
            return False


class TestTwoPrKPN():
    def is_feasible(self,s):
         """ test oracle function (2-dim) """
         if (len(s) != 2):
              print("test oracle requires a dimension of 2\n")
              exit(1)
         x = s[0]
         y = s[1]
         if x == y: #same PE
              return False
         elif x < 0 or x > 15 or y < 0 or y > 15: #outside of area
              #print("outside area")
              return False
         elif divmod(x,4)[0] == divmod(y,4)[0]: # same cluster
              return True
         else:
              return False

