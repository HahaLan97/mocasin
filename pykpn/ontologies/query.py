#Copyright (C) 2019 TU Dresden
#All Rights Reserved
#
#Authors: Andrès Goens, Felix Teweleit

try:
    text=unicode
except:
    text=str

from datetime import datetime
from pykpn.slx.kpn import SlxKpnGraph
from pykpn.common.mapping import Mapping
from pykpn.slx.platform import SlxPlatform
from pykpn.ontologies.solver import Solver
from pykpn.mapper.random import RandomMapping

def main():
    kpn = SlxKpnGraph('SlxKpnGraph',  "apps/audio_filter/audio_filter.cpn.xml",'2017.04')
    platform = SlxPlatform('SlxPlatform', 'apps/audio_filter/exynos/exynos.platform', '2017.04')
    mappingDict = {"mapping_one" : RandomMapping(kpn, platform), "mapping_two" : RandomMapping(kpn, platform)}
    mSolver = Solver(kpn, platform, mappingDict, debug=False)
    
    #inputString = "EXISTS ARM00 PROCESSING AND ARM01 PROCESSING AND ARM02 PROCESSING AND src MAPPED ARM01 AND RUNNING TOGETHER [sink, fft_l ]"
    #inputString = "EXISTS EQUALS mapping_one"
    inputString = "EXISTS src MAPPED ARM00 AND fft_l MAPPED ARM01"
    inputQuery = "EXISTS src MAPPED ARM00 AND filter_l MAPPED ARM01 AND RUNNING TOGETHER [src, filter_l ]"
    stateVec = [4, 5, 1, 2, 0, 0]
    
    answer = mSolver.request(inputQuery)
    
    if isinstance(answer, Mapping):
        print(answer.to_list(channels=False))
    else:
        print("No valid mapping found!")
    
if __name__ == "__main__":
    start = datetime.now()
    main()
    print(datetime.now() - start)
    