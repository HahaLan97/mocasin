# Copyright (C) 2024 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Jiahong Bi

import logging
from omegaconf import OmegaConf
from dataclasses import dataclass, field
from hydra.utils import to_absolute_path
from mocasin.common.trace import (
    DataflowTrace,
    ComputeSegment,
    ReadTokenSegment,
    WriteTokenSegment,
)

log = logging.getLogger(__name__)

@dataclass
class _YamlFiringRule:
    """Helper class defining the firing rules of a YAML actor"""

    reads: dict = field(default_factory=dict)
    writes: dict = field(default_factory=dict)
    initial_writes: dict = field(default_factory=dict)

class YamlTrace(DataflowTrace):
    """Represents the behavior of a YAML application

    Args:
        yaml_file (str): a YAML file to read from
        
    """

    def __init__(self, yaml_file) -> None:
        log.info("Start parsing the YAML trace")

        self._graph = OmegaConf.load(to_absolute_path(yaml_file))
        self._firing_rules = {}
        self._node_cycles = {}

        self.__get_firing_rules(self._graph)
        self.__get_cycle_counts(self._graph)

        log.info("Done parsing the YAML trace")
    
    def __get_firing_rules(self, graph):
        for node in graph.nodes:
            rule = _YamlFiringRule()
            for port in node.ports:
                if port.type == "out":
                    channel = None
                    for c in graph.channels:
                        if c.srcNode == node.name and c.srcPort == port.name:
                            channel = c
                            break
                    rule.writes[channel.name] = 1
                    if channel.initToken > 0:
                        rule.initial_writes[channel.name] = channel.initToken
                    elif channel.initToken < 0:
                        raise RuntimeError("Number of initial tokens must greater than or equal to 0")
                else:
                    channel = None
                    for c in graph.channels:
                        if c.dstNode == node.name and c.dstPort == port.name:
                            channel = c
                            break
                    rule.reads[channel.name] = 1
            self._firing_rules[node.name] = rule
    
    def __get_cycle_counts(self, graph):

        for node in graph.nodes:
            # Considering that CGRA only have one processor type
            # and this accepts cycles instead of time
            proc_cycles = {'proc_type_0': node.exec_cycles, 'proc_type_1': node.exec_cycles}
            self._node_cycles[node.name] = proc_cycles
    
    def get_trace(self, process):
        firings = self._firing_rules[process]

        for channel, count in firings.initial_writes.items():
            yield WriteTokenSegment(channel=channel, num_tokens=count)

        for channel, count in firings.reads.items():
            yield ReadTokenSegment(channel=channel, num_tokens=count)

        yield ComputeSegment(processor_cycles=self._node_cycles[process])

        for channel, count in firings.writes.items():
            yield WriteTokenSegment(channel=channel, num_tokens=count)
