# Copyright (C) 2019 TU Dresden
# All Rights Reserved
#
# Authors: Felix Teweleit

from tgffParser import regEx as expr
import argparse

from pykpn.util import logging
from tgffParser.dataStructures import TgffProcessor, TgffGraph, TgffLink
from pykpn.common.kpn import KpnProcess, KpnGraph, KpnChannel

class Parser():
    def __init__(self, debug=False):
        self._debug = debug
        self.logger = logging.getLogger('tgff_parser')
        
        self.quantity_dict = {}
        self.std_link_dict = {}
        self.prim_link_dict = {}
        self.task_graph_dict = {}
        self.processor_dict= {}
        
        self.common_components = { 
            'comment' : expr.comment(),
            'new_line' : expr.new_line(),
            'scope_limiter' : expr.scope_limiter(),
            }
        
        self.data_components = {
            'task_graph' : expr.task_graph(),
            'commun_quant' : expr.commun_quant(),
            'hw_component' : expr.hw_component(),
            'hyperperiod' : expr.hyperperiod(),
            }
        
        self.task_graph_components = {
            'period' : expr.period(),
            'task' : expr.task(),
            'channel' : expr.channel(),
            'hard_deadline' : expr.hard_deadline(),
            'soft_deadline' : expr.soft_deadline(),
            }
        
        self.hw_components = {
            'properties' : expr.properties(),
            'operation' : expr.operation(),
            'std_link_value' : expr.std_link_value(),
            'prim_link_value': expr.prim_link_value()
            }
        
        self.commun_quant_components = {
            'commun_value' : expr.commun_value(),
            }
        
        self.unused_components = {
            'unused_statement' : expr.unused_statement(),
            'unused_scope' : expr.unused_scope(),
            }

    
    def parse_file(self, file_path):
        with open(file_path, 'r') as file:
            last_missmatch = None
            
            current_line  = file.readline()
            while current_line:
                key, match = self._parse_line(current_line, self.data_components)
                if key == 'task_graph':
                    self.logger.debug('Parsing task graph')
                    self._parse_task_graph(file, match)
                elif key == 'commun_quant':
                    self.logger.debug('Parsing communication quant')
                    self._parse_commun_quant(file, match)
                elif key == 'hw_component':
                    self.logger.debug('Parse HW component')
                    self._parse_hw_component(file, match, last_missmatch)
                elif key == 'unused_scope':
                    self.logger.debug('Parse unused group')
                    self._parse_unused_scope(file)
                else:
                    if not key is None:
                        last_missmatch = (key, match)
                    self._key_missmatch(key, file.tell())
                current_line = file.readline()
        
        self.logger.info('Finished parsing')
        return [self.task_graph_dict, self.quantity_dict, self.processor_dict, self.std_link_dict]
    
    def _parse_task_graph(self, file, match):
        identifier = 'TASK_GRAPH_' + (match.group('identifier'))
        tasks = {}
        channels = {}
        task_index_extension = 0
        channel_index_extension = 0
        
        current_line = file.readline()
        
        while current_line:
            key, match = self._parse_line(current_line, self.task_graph_components)
            if key == 'task':
                self.logger.debug('Added task: ' + match.group('name') + ' ' + match.group('type'))
                if not match.group('name') in tasks:
                    tasks.update( {match.group('name') : int(match.group('type'))} )
                else:
                    tasks.update( {match.group('name') + '_' + str(task_index_extension) : match.group('type')} )
                    task_index_extension += 1
            elif key == 'channel':
                self.logger.info('Added channel: ' + match.group('name') + ' ' + match.group('type'))
                if not match.group('name') in channels:
                    channels.update( {match.group('name') : [match.group('source'), match.group('destination'), match.group('type')]} ) 
                else:
                    channels.update( {match.group('name') + '_' + str(channel_index_extension): [match.group('source'), match.group('destination'), match.group('type')]} )
                    channel_index_extension += 1
            elif key == 'scope_limiter':
                self.logger.debug('Reached end of task graph')
                break
            else:
                self._key_missmatch(key, file.tell())
            current_line = file.readline()
        
        self.task_graph_dict.update( {identifier : TgffGraph(identifier, tasks, channels, self.quantity_dict)} )
        
    def _parse_commun_quant(self, file, match):
        identifier = match.group('identifier')
        commun_values = {}
        current_line = file.readline()
        
        while current_line:
            key, match = self._parse_line(current_line, self.commun_quant_components)
            if key == 'commun_value':
                self.logger.debug('Added commun_value ' + match.group('identifier') + ' ' + match.group('value'))
                commun_values.update( {int(match.group('identifier')) : float(match.group('value'))} )
            elif key == 'scope_limiter':
                self.logger.debug('Reached end of commun_quant')
                break
            else:
                self._key_missmatch(key, file.tell())
            current_line = file.readline()
        
        self.logger.info('Added to commun_quant dict: ' + identifier)
        self.quantity_dict.update( {int(identifier) : commun_values} )
    
    def _parse_hw_component(self, file, match, last_missmatch):
        identifier = match.group('name') + '_' + match.group('identifier')
        current_line = file.readline()
        last_missmatch = last_missmatch
        
        while current_line:
            key, match = self._parse_line(current_line, self.hw_components)
            if key == 'std_link_value':
                self._parse_std_link(identifier, file, match, last_missmatch)
                return
            elif key == 'prim_link_value':
                self._parsePrimLink(identifier, file, match)
                return
            elif key == 'properties' or key == 'operation':
                self._parseProcessor(identifier, file, key, match, last_missmatch)
                return
            elif key == 'scope_limiter':
                self.logger.error('Reached end of scope. Unable to recognize HW component!')
            else:
                self._key_missmatch(key, file.tell())
                last_missmatch = (key, match)
            current_line = file.readline()
        
    def _parse_std_link(self, identifier, file, match, last_missmatch):
        self.logger.debug('Recognized component as standard link!')
        
        name = identifier
        if last_missmatch[0] == 'comment':
            name = last_missmatch[1].group('comment').split()[0]
        throughput = 1 / float(match.group('bit_time'))
        link = TgffLink(name, throughput)
        
        self.logger.info('Added to link dict: ' + str(identifier))
        self.std_link_dict.update( {identifier : link } )
        
    
    def _parse_prim_link(self, identifier, file, match):
        self.logger.info("Recognized component as primitive link!")
        prim_link_values = []
        self._add_prim_link_value(prim_link_values, match)
        
        current_line = file.readline()
        
        while current_line:
            key, match = self._parse_line(current_line, self.hw_components)
            if key == 'prim_link_value':
                self._add_prim_link_value(prim_link_values, match)
            elif key == 'scope_limiter':
                self.logger.debug("Reached end of primLink")
                break
            else:
                self._key_missmatch(key, file.tell())
            current_line = file.readline()
            
        self.logger.info('Added to link dict: ' + str(identifier))
        self.prim_link_dict.update( {identifier : prim_link_values } )
    
    def _add_prim_link_value(self, data_struct, match):
        data_struct.append(match.group('c_use_prc'))
        data_struct.append(match.group('c_cont_prc'))
        data_struct.append(match.group('s_use_prc'))
        data_struct.append(match.group('s_cont_prc'))
        data_struct.append(match.group('packet_size'))
        data_struct.append(match.group('bit_time'))
        data_struct.append(match.group('power'))
        
    def _parseProcessor(self, identifier, file, key, match, last_missmatch):
        self.logger.debug("Recognized component as processing element")
        properties = []
        operations = {}
        
        if key == 'properties':
            self._add_properties(properties, match)
        elif key == 'operation':
            self._add_operation(operations, match)
        
        current_line = file.readline()
        
        while current_line:
            key, match = self._parse_line(current_line, self.hw_components)
            if key == 'properties':
                self._add_properties(properties, match)
            elif key == 'operation':
                self._add_operation(operations, match)
            elif key == 'scope_limiter':
                self.logger.debug('Reached end of processor')
                break
            else:
                self._key_missmatch(key, file.tell())
            current_line = file.readline()
            
        self.logger.info('Added to processor dict: ' + str(identifier))
        
        self.logger.info('Added to graph dict: ' + identifier)
        if last_missmatch[0] != 'comment':
            self.processor_dict.update( {identifier : TgffProcessor(identifier, operations)} )
        else:
            comment = last_missmatch[1].group('comment').split()
            processor_type = comment[0]
            
            if len(comment) > 1:
                for i in range(1, len(comment)):
                    processor_type += '_' + comment[i]
            self.processor_dict.update( {identifier : TgffProcessor(identifier, operations, processor_type=processor_type)} )
    
    def _add_properties(self, properties, match):
        self.logger.debug('Parsed processor properties')
        properties.append(match.group('price'))
        properties.append(match.group('buffered'))
        properties.append(match.group('preempt_power'))
        properties.append(match.group('commun_energ_bit'))
        properties.append(match.group('io_energ_bit'))
        properties.append(match.group('idle_power'))
    
    def _add_operation(self, operations, match):
        self.logger.debug('Parsed processor operation')
        tmpList = list()
        tmpList.append(match.group('version'))
        tmpList.append(match.group('valid'))
        tmpList.append(float(match.group('task_time')))
        tmpList.append(float(match.group('preempt_time')))
        tmpList.append(match.group('code_bits'))
        tmpList.append(match.group('task_power'))
        operations.update( { int(match.group('type')) : tmpList} )
        
    def _parse_unused_scope(self, file):
        current_line = file.readline()
        
        while current_line:
            key, match = self._parse_line(current_line)
            if key == 'unused_statement':
                self.logger.info.log("Ignored statement")
            elif key == 'scope_limiter':
                self.logger.info("Parsed block which will be ignored")
                break
            else:
                self._key_missmatch(key, file.tell())
            current_line = file.readline()
    
    def _parse_line(self, line, additional_components=None):
        for key, rx in self.common_components.items():
            match = rx.fullmatch(line)
            if match:
                return key, match
        
        if not additional_components == None:
            for key, rx in additional_components.items():
                match = rx.fullmatch(line)
                if match:
                    return key, match
            
        for key, rx in self.unused_components.items():
            match = rx.fullmatch(line)
            if match:
                return key, match
        
        return None, None
    
    def _key_missmatch(self, key, position):
        if key == 'new_line' or key == 'comment':
            if self._debug:
                print('Skip empty or comment line')
        elif not key == None:
            self.logger.warning('Parsed unhandled group: <' + key + '> at position: ' + str(position))
        else:
            self.logger.error('Parse error on position: ' + str(position))
                
def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('path',metavar='P', type=str)
    argument_parser.add_argument('--debug', metavar='D', const=True, nargs='?')
    args = argument_parser.parse_args()

    mParser = Parser(debug=args.debug)
    mParser.parseFile(args.path)
    
    
if __name__ == "__main__":
    main()
    
    