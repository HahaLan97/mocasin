#Copyright (C) 2019 TU Dresden
#All Rights Reserved
#
#Authors: Felix Teweleit

import pytest
from arpeggio import ParserPython
from pykpn.ontologies.logicLanguage import Grammar
from pykpn.slx.platform import SlxPlatform
from pykpn.slx.kpn import SlxKpnGraph
from pykpn.ontologies.solver import Solver

@pytest.fixture
def parser():
    return ParserPython(Grammar.logicLanguage, reduce_tree=True, debug=False)

@pytest.fixture
def kpnGraph():
    return SlxKpnGraph('SlxKpnGraph',  "apps/audio_filter/audio_filter.cpn.xml",'2017.04')

@pytest.fixture
def platform():
    return SlxPlatform('SlxPlatform', 'apps/audio_filter/exynos/exynos.platform', '2017.04')

@pytest.fixture
def solver():
    kpn = SlxKpnGraph('SlxKpnGraph',  "apps/audio_filter/audio_filter.cpn.xml",'2017.04')
    platform = SlxPlatform('SlxPlatform', 'apps/audio_filter/exynos/exynos.platform', '2017.04')
    return Solver(kpn, platform)
    