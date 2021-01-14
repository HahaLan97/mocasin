# Copyright (C) 2017-2020 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard, Felix Teweleit, Andres Goens

import networkx as nx
from enum import Enum
from mocasin.util import logging
import random

log = logging.getLogger(__name__)

class TraceSegment(object):
    """Represents a segment in a process' execution trace

    :ivar processing_cycles:
        Duration (in cycles) of a processing segment. None if the segment does
        not contain any computations.
    :type processing_cycles: int or None
    :ivar read_from_channel:
        Name of the channel to read from at the end of the segment (after
        processing). None if no read access is to be performed. If not None,
        write_to_channel must be None.
    :type read_from_channel: str or None
    :ivar write_to_channel:
        Name of the channel to write to at the end of the segment (after
        processing). None if no write access is to be performed. If not None,
        read_from_channel must be None.
    :type write_to_channel: str or None
    :ivar n_tokens:
        Number of tokens to be read from or written to a channel. None if
        neither a write access nor a read access is to be performed at the end
        of the segment.
    :type n_tokens: int or None
    :ivar bool terminate:
        If True, this is the last segment of the execution trace.
    """

    def __init__(self, process_cycles=None, read_from_channel=None,
                 write_to_channel=None, n_tokens=None, terminate=False):
        """Initialize a trace segment)"""
        self.processing_cycles = process_cycles
        self.read_from_channel = read_from_channel
        self.write_to_channel = write_to_channel
        self.n_tokens = n_tokens
        self.terminate = terminate

    def sanity_check(self):
        """Perform a series of sanity checks on the object"""
        if (self.read_from_channel is not None and
                self.write_to_channel is not None):
            raise RuntimeError('A trace segment may not contain both a read '
                               'and a write access')
        if (self.n_tokens is None and (self.read_from_channel is not None or
                                       self.write_to_channel is not None)):
            raise RuntimeError('Trace segments contains a channel access but '
                               'the number of tokens is not specified!')


class TraceGenerator(object):
    """Creates trace segments

    This class is intended as a base class. A superclass could extend the
    functionality by generating random traces or reading traces from a file.
    """

    def next_segment(self, process_name, processor_type):
        """Return the next trace segment.

        Returns the next trace segment for a process running on a processor of
        the specified type (the segments could differ for different processor
        types). This should be overridden by a subclass. The default behavior
        is to return None

        :param str process_name:
            name of the process that a segment is requested for
        :param str processor_type:
            the processor type that a segment is requested for
        :returns: the next trace segment or None if there is none
        :rtype: TraceSegment or None
        """
        return None
    
    def reset(self):
        """Resets the generator.
        
        Resets the generator to its initial state. In this way we
        can avoid to instantiate a new generator in case a trace
        has to be calculated multiple times.
        
        Returns:
            None: By default. Nothing should be returned by the
                implementation of any subclass.
        """
        return None

class EmptyTraceGenerator(TraceGenerator):
    def next_segment(self, process_name, processor_type):
        log.warning("Generating traces from empty trace. Did you forget to specify a trace configuration?")
        return TraceSegment(terminate=True)

class RandomTraceGenerator(TraceGenerator):

    def __init__(self,expected_num_executions=1000,
                 min_cycles=100,max_cycles=10000):
        self.firings = {}
        self.max_firings = {}
        self.num_firings = {}
        #suggestion: give min/max cycles per processor type?
        #perhaps also per process_name?
        self.min_cycles = min_cycles
        self.max_cycles = max_cycles
        self.expected_num_executions = expected_num_executions

    def next_segment(self, process_name, processor_type):
        #This will not produce any read/write events currently.
        #This can't be fixed without having information about
        #the application. If the need arises, we can change it.
        #Otherwise we don't need to change the initalization
        #of the trace generator.
        if process_name not in self.firings:
            sigma = 0.1 * self.expected_num_executions
            final = random.gauss(self.expected_num_executions,sigma)
            total = round(final)
            self.firings[process_name] = []
            self.num_firings[process_name] = 0
            self.max_firings[process_name] = total
            for i in range(total):
                exec_cycles = random.randint(self.min_cycles, self.max_cycles)
                self.firings[process_name].append(exec_cycles)
            log.info(f"Random trace for {process_name}: {final} executions.")

        exec_cycles = self.firings[process_name][self.num_firings[process_name]]
        log.debug(f"firing {process_name} for {exec_cycles} cycles.")
        self.num_firings[process_name] += 1
        if self.num_firings[process_name] == self.max_firings[process_name]:
            return TraceSegment(process_cycles=exec_cycles,terminate=True)
        elif self.num_firings[process_name] < self.max_firings[process_name]:
            return TraceSegment(process_cycles=exec_cycles)
        else:
            raise RuntimeError("Getting a segment from finished trace.")


    def reset(self,seed=None):
        if seed is not None:
            random.seed(seed)
        for proc in self.num_firings:
            self.num_firings[proc] = 0

class EdgeType(Enum):
    SEQUENTIAL_ORDER = 1
    READ_AFTER_COMPUTE = 2
    BLOCK_READ = 3
    UNBLOCK_READ = 4
    BLOCK_WRITE = 5
    ROOT_OR_LEAF = 6

   
class TraceGraph(nx.DiGraph):
    """A Trace graph for the full execution of a KPN application.
    
    The graph covers the full execution of a KPN application on a specific platform. Individual 
    segments in the execution are covered within the graphs nodes. Dependencies between those 
    segments are covered within the graphs edges.
    The weight of each edge equals the amount of ticks needed to execute the following segment,
    regarding the current mapping.
    The graphs inherits the a directed graph from the networkX framework. All surrounding code 
    is construction overhead.
    """
    def __init__(self, kpn,
                 trace_generator,
                 process_mapping,
                 channel_mapping,
                 processor_groups,
                 primitive_groups):
        """
        Args:
            trace_generator (TraceGenerator) : 
            process_mapping (dict {str : list(str)} : 
            channel_mapping (dict {str : list(int)} :
            processor_groups (dict {str : list(processor)} :
        """
        
        super(TraceGraph, self).__init__()
        self.add_node('V_e', kpn_element=None)
        self.add_node('V_s', kpn_element=None)
        
        self.critical_path_nodes = None
        
        #captures the amount of read and write accesses for each channel
        channel_dict = {}
        for channel in kpn.channels():
            channel_dict.update({channel.name : [0, 0]})
        
        #captures the amount of executed segments and the last segment
        process_dict = {}
        for process in kpn.processes():
            process_dict.update({process.name : [0, None]})
            
        #Generate full trace for all processes
        not_terminated = set(process_dict.keys())
        while len(not_terminated) > 0:

            for process_name in list(not_terminated):
                processor = self._determine_slowest_processor(process_name, process_mapping, processor_groups)
                
                try:
                    current_segment = trace_generator.next_segment(process_name, processor.type)
                except AttributeError:
                    continue
                last_segment_index = process_dict[process_name][0]
                last_segment = process_dict[process_name][1]
                
                process_dict[process_name][1] = current_segment
                
                if current_segment.terminate:
                    not_terminated.remove(process_name)
                    continue
                
                if last_segment_index == 0:
                    #Adding dependencies from start node
                    self.add_edges_from([("V_s", "{}_1".format(process_name))], type=EdgeType.ROOT_OR_LEAF, weight=0)
                    #Add associated process as node attribute
                    self.nodes['{}_1'.format(process_name)]['kpn_element'] = process_name
                else:
                    edge_weight = 0
                    if last_segment.processing_cycles:
                        edge_weight = processor.ticks(last_segment.processing_cycles)
                    
                    #Adding sequential order dependencies
                    self.add_edges_from([("{}_{}".format(process_name, last_segment_index),
                                          "{}_{}".format(process_name, last_segment_index+1))],
                                          type=EdgeType.SEQUENTIAL_ORDER,
                                          weight=edge_weight,
                                          cycles=last_segment.processing_cycles)
                    
                    #Add associated process as node attribute
                    self.nodes['{}_{}'.format(process_name, last_segment_index)]['kpn_element'] = process_name
                    self.nodes['{}_{}'.format(process_name, last_segment_index+1)]['kpn_element'] = process_name
                    
                process_dict[process_name][0] += 1

                #Adding unblock read dependencies
                if last_segment and last_segment.write_to_channel is not None:
                    name = last_segment.write_to_channel
                    read_time = self._determine_slowest_access(name,
                                                               channel_mapping,
                                                               primitive_groups,
                                                               read_access=True)
                    self.add_edges_from([("r_{}_{}".format(name, channel_dict[name][1]-1),
                                         "{}_{}".format(process_name, last_segment_index+1))],
                                        type=EdgeType.UNBLOCK_READ,
                                        weight=read_time)
                    
                    #Add associated process as node attribute
                    self.nodes['r_{}_{}'.format(name, channel_dict[name][1]-1)]['kpn_element'] = name
                    self.nodes['{}_{}'.format(process_name, last_segment_index+1)]['kpn_element'] = process_name
                 
                #Adding block read dependencies
                if current_segment.write_to_channel is not None:
                    name = current_segment.write_to_channel
                    write_time = self._determine_slowest_access(name,
                                                                channel_mapping,
                                                                primitive_groups,
                                                                read_access=False)
                    self.add_edges_from([("{}_{}".format(process_name, last_segment_index+1),
                                          "r_{}_{}".format(name, channel_dict[name][1]))],
                                          type=EdgeType.BLOCK_READ,
                                          weight=write_time)
                    
                    #Add associated process as node attribute
                    self.nodes['r_{}_{}'.format(name, channel_dict[name][1])]['kpn_element'] = name
                    self.nodes['{}_{}'.format(process_name, last_segment_index+1)]['kpn_element'] = process_name
                    
                    channel_dict[name][1] += 1
                
                #Adding read after compute dependencies
                if current_segment.read_from_channel is not None:
                    name = current_segment.read_from_channel
                    write_time = self._determine_slowest_access(name,
                                                                channel_mapping,
                                                                primitive_groups,
                                                                read_access=False)
                    self.add_edges_from([("{}_{}".format(process_name, last_segment_index+1),
                                          "r_{}_{}".format(name, channel_dict[name][0]))],
                                          type=EdgeType.READ_AFTER_COMPUTE,
                                          weight=write_time)
                    
                    #Add associated process as node attribute
                    self.nodes['r_{}_{}'.format(name, channel_dict[name][0])]['kpn_element'] = name
                    self.nodes['{}_{}'.format(process_name, last_segment_index+1)]['kpn_element'] = process_name
                    
                    channel_dict[name][0] += 1
        
        #Adding dependencies to final node
        for node in self.nodes:
            if list(self.successors(node)) == [] and not node == "V_e":
                self.add_edges_from([(node, "V_e")], type=EdgeType.ROOT_OR_LEAF, weight=0)
    
   
    def change_element_mapping(self, element_name, element_mapping, element_groups, definitive=False):
        """Updates the graph regarding to a change in the mapping.
    
        This method updates the graph, regarding to the remapping of a single KPN element. Since the
        remapping of an element does not change the execution trace of an application, only the weights
        of edges are affected. Also it can be specified whether the update should be permanent or just
        temporarily for analytic purposes.
        In latter case, the method will just determine the length of the critical path considering the
        new mapping.
    
        Args:
            element_name (str): The name of the kpn element that has been remapped.
            element_mapping (list[int]): The ids of the hardware groups, the element
                has been mapped to.
            element_groups (dict{int : [hw_resource]}): A dictionary which maps the available ids to the
                existing hardware element groups for either communication resources or procesing elements.
            definitive (bool): States whether the change will be applied permanently or just for the sake
                of critical path determination.
        Returns:
            int: In every case the method will return the accumulated cycle count of all edges on the 
                critical path.
        """
        if not self.critical_path_nodes:
            raise RuntimeError('Call determine_critical_path_elements() in the first place!')
        
        last_node = None
        critical_path_length = 0
        
        for node in self.critical_path_nodes:
            if node == 'V_s':
                last_node = node
                continue
            
            new_weight = self.edges[last_node, node]['weight']
            
            if (self.edges[last_node, node]['type'] == EdgeType.SEQUENTIAL_ORDER and
                        self.nodes[last_node]['kpn_element'] == element_name):
                #for sequential order edges the last nodes element is relevant
                cycles = self.edges[last_node, node]['cycles']
                if cycles:
                    processor = self._determine_slowest_processor(element_name,
                                                                  element_mapping,
                                                                  element_groups)
                    new_weight = processor.ticks(cycles)
                
            elif (self.edges[last_node, node]['type'] == EdgeType.READ_AFTER_COMPUTE and
                        self.nodes[node]['kpn_element'] == element_name):
                #for read after compute edges the actual node is relevant
                new_weight = self._determine_slowest_access(element_name,
                                                                element_mapping,
                                                                element_groups,
                                                                read_access=False)
                
            elif (self.edges[last_node, node]['type'] == EdgeType.BLOCK_READ and
                        self.nodes[node]['kpn_element'] == element_name):
                #for block read edges the actual node is relevant
                new_weight = self._determine_slowest_access(element_name,
                                                                element_mapping,
                                                                element_groups,
                                                                read_access=False)
                
            elif (self.edges[last_node, node]['type'] == EdgeType.UNBLOCK_READ and
                        self.nodes[last_node]['kpn_element'] == element_name):
                #for unblock read edges the last node is relevant
                new_weight = self._determine_slowest_access(element_name,
                                                               element_mapping,
                                                               element_groups,
                                                               read_access=True)
                
            elif self.edges[last_node, node]['type'] == EdgeType.BLOCK_WRITE:
                #this kind of edges is currently not implemented
                #due to no representation of buffer sizes in mocasin
                pass
                
            elif self.edges[last_node, node]['type'] == EdgeType.ROOT_OR_LEAF:
                #edges to start and end node will always
                #remain unchanged
                pass
            
            if definitive:
                self.edges[last_node,node]['weight'] = new_weight
            
            critical_path_length += new_weight
            last_node = node
            
        
        return critical_path_length
        
    
    def determine_critical_path_elements(self):
        """Determine nodes and edges on the critical path.
        
        This method determines the critical path through the trace graph. It returns all 
        KPN elements associated with the critical path. Also the path's length and all
        nodes laying on the path.
        
        Returns:
            list[kpn_elements]: A list containing all elements associated with the
                critical path. The elements can either be channels or processes.
            int: The length of the critical path.
            list[str]: A list of all nodes laying on the critical path.
        """
        elements = []
        self.critical_path_nodes = nx.dag_longest_path(self)
        path_length = nx.dag_longest_path_length(self)
        
        for node in self.critical_path_nodes:
        
            if not (node == 'V_s' or node == 'V_e'):
                associated_element = self.nodes[node]['kpn_element']
            
                if associated_element not in elements:
                    elements.append(associated_element)
        
        return elements, path_length, self.critical_path_nodes
    
    
    def _determine_slowest_processor(self, process_name, process_mapping, processor_groups):
        """Determines the slowest group of processors from given set of groups.
        
        Determines from a given mapping of a KPN process to multiple groups of processors
        the group with the slowest timing characteristic.
        
        Args:
            process_name(str): The name of the KPN process.
            process_mapping(dict{str : list[int]}): A dictionary mapping the names of processes
                to ids of processor groups. 
            processor_groups(dict{int : list[mocasin.common.processor]}): A dictionary mapping 
                the id of a hardware group to a list of actual processors.
        Returns:
            mocasin.common.platform.Processor: Returns one processor of the slowest available
                hardware group.
        """
        if len(process_mapping[process_name]) == 1:
            return processor_groups[process_mapping[process_name][0]][0]
        else:
            processor = None
            
            for group_id in process_mapping[process_name]:
            
                if not processor:
                    processor = processor_groups[group_id][0]
                else:
                    if processor.frequency_domain.frequency > processor_groups[group_id][0].frequency_domain.frequency:
                        processor = processor_groups[group_id][0]
            
            if processor:
                return processor
            else:
                raise RuntimeError("No valid group available!")
    
    
    def _determine_slowest_access(self, channel_name, channel_mapping, primitive_groups, read_access=True):
        """Determines communication resource with slowest read/write characteristic.
        
        Determines for a given channel, mapped to multiple groups of communication primitives,
        the resource group which either has slowest read or write access.
        
        Args:
            channel_name (str): The name of the channel.
            channel_mapping (dict{str : list[int]}: A dictionary which maps the names of channels
                to a list of ids of hardware groups.
            primitive_groups (dict{int : list[mocasin.mapper.gbm_fullmapper.DerivedPrimitive]}): A 
                dictionary which maps the ids of hardware groups to a list of primitives.
            read_access (bool): States whether the function should determine the cycle count for 
                a read or write access. Is true by default.
        """
        static_cost = None
            
        for group_id in channel_mapping[channel_name]:
                    
            if not static_cost:
                static_cost = group_id
            else:
                if group_id > static_cost:
                    static_cost = group_id
        
        if static_cost or static_cost == 0:
            
            if read_access:
                return primitive_groups[static_cost][0].read_cost
            
            return primitive_groups[static_cost][0].write_cost
        else:
            raise RuntimeError('Cant determine slowest resource in channel mapping!')
