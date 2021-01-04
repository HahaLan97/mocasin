# Copyright (C) 2017-2020 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard


from .convert import convert
from .parse import parse
from pykpn.util import logging
from pykpn.common.platform import Platform


log = logging.getLogger(__name__)


class SlxPlatform(Platform):

    def __init__(self, name, xml_file, **kwargs):
        super().__init__(name, symmetries_json=kwargs.get('symmetries_json',None))
        log.info('start parsing the platform description')
        xml_platform = parse(xml_file, True)
        convert(self, xml_platform, scheduler_cycles=kwargs.get('scheduler_cycles', None))
        log.info('done parsing the platform description')
