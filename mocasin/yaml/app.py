# Copyright (C) 2024 TU Dresden
# Licensed under the ISC license (see LICENSE.txt)
#
# Authors: Jiahong Bi

import logging

from omegaconf import OmegaConf
from hydra.utils import to_absolute_path
from mocasin.common.graph import DataflowChannel, DataflowGraph, DataflowProcess

log = logging.getLogger(__name__)

class YamlGraph(DataflowGraph):
    """Graph representation of a YAML application

    Args:
        yaml_file (str): the YAML file to read from
        name (str): the name to use for the application
    """

    def __init__(self, yaml_file):

        log.info("Start parsing application from YAML")

        self.yaml_graph = OmegaConf.load(to_absolute_path(yaml_file))
        log.debug(self.yaml_graph)
        name = self.yaml_graph.graph.name

        super().__init__(name)

        for node in self.yaml_graph.nodes:
            n_name = node.name
            if not self.validate_node(node):
                raise RuntimeError(f"Node {n_name} is missing expected keys")
            log.debug(f"Add process {name}.{n_name}")
            self.add_process(DataflowProcess(n_name))

        for channel in self.yaml_graph.channels:
            c_name = channel.name
            if not self.validate_channel(channel):
                raise RuntimeError(f"Channel {c_name} is incorrectly connected to a node in the graph")
            log.debug(f"Add channel {name}.{c_name}")
            df_channel = DataflowChannel(c_name, 1)
            self.add_channel(df_channel)
        
            src_process = self.find_process(channel.srcNode)
            src_process.connect_to_outgoing_channel(df_channel)
            log.debug(
                f"Process {name}.{src_process.name} writes to channel "
                f"{name}.{c_name}")

            dst_process = self.find_process(channel.dstNode)
            dst_process.connect_to_incomming_channel(df_channel)
            log.debug(
                f"Process {name}.{dst_process.name} reads from channel "
                f"{name}.{c_name}")
        
        log.info("Done parsing graph from YAML")
    
    def validate_node(self, node):
        if 'ports' not in node:
            log.error(f"Node {node.name} doesn't have 'ports' key")
            return False
        if 'exec_cycles' not in node:
            log.error(f"Node {node.name} doesn't have 'exec_cycles' key")
            return False
        return True
    
    def validate_channel(self, channel):
        if not self.validate_port(channel.srcNode, channel.srcPort, 'out'):
            log.error(f"Invalid srcPort {channel.srcPort} for srcNode {channel.srcNode}")
            return False
        
        if not self.validate_port(channel.dstNode, channel.dstPort, 'in'):
            log.error(f"Invalid dstPort {channel.dstPort} for dstNode {channel.dstNode}")
            return False
        
        return True

    def validate_port(self, node_name, port_name, port_type):
        node = next((n for n in self.yaml_graph.nodes if n.name == node_name), None)
        if not node:
            log.error(f"Node {node_name} not found")
            return False
        
        port = next((p for p in node.ports if p.name == port_name and p.type == port_type), None)
        if not port:
            log.error(f"Port {port_name} with type {port_type} not found in node {node_name}")
            return False
        
        return True
