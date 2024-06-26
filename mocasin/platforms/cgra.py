import math
import logging

log = logging.getLogger(__name__)

from mocasin.common.platform import (
    Platform,
    Primitive,
    Processor,
    CommunicationPhase,
    CommunicationResource,
    CommunicationResourceType,
    FrequencyDomain
)
from mocasin.platforms.platformDesigner import PlatformDesigner, cluster
from hydra.utils import instantiate

import sys

class CGRAPlatformDesigner(PlatformDesigner):
    def __init__(self, platform):
        super().__init__(platform)
    
    def connectComponents(
            self,
            component1,
            component2,
            physicalLink=None,
            bidirectional=True):
        """Connect two different componentes with the given physical Link.
        The components may be either processor or communication resource
        """
        # TODO: check that element1 and element2 are processor or communicationResource
        try:
            self.adjacentList[component1].append(component2)
            if (bidirectional):
                self.adjacentList[component2].append(component1)
            if physicalLink:
                self.links.append(physicalLink)

        except:  # FIXME: this is fishy
            log.error("Exception caught: " + str(sys.exc_info()[0]))
            return
        
    def connectCgraPes(self, pes, n):
        for row in range(n):
            for col in range(n):
                pe_idx = row * n + col
                pe = pes[pe_idx]

                # Connect to the node itself
                self.connectComponents(pe, pe, bidirectional = False)

                # Connect nodes in the same row bidirectionally
                if col < n - 1:
                    next_pe = pes[pe_idx + 1]
                    self.connectComponents(pe, next_pe)

                # Connect nodes in different rows (north to south) unidirectionally
                if row < n - 1:
                    south_pe = pes[pe_idx + n]
                    self.connectComponents(pe, south_pe, bidirectional = True)
    
    def addPhysicalLink(self, physicalLink):
        adjacencyList = self.adjacentList

        for key in adjacencyList:
            for target in adjacencyList[key]:
                name = "pl_" + str(target) + "_" + str(key)
                communicationResource = CommunicationResource(
                    name,
                    physicalLink._frequency_domain,
                    physicalLink._resource_type,
                    physicalLink._read_latency,
                    physicalLink._write_latency,
                    physicalLink._read_throughput,
                    physicalLink._write_throughput,
                )
                self.platform.add_communication_resource(communicationResource)
    
    def generatePrimitivesForPes(self, pes):
        platform = self.platform
        adjacencyList = self.adjacentList

        for pe in pes:
            producerList = {}
            consumerList = {}
            for element in adjacencyList[pe]:
                producerList[pe] = pe
                consumerList[element] = pe
            prim = Primitive(f"prim_{pe.name}")
            produce_resources = []
            for pe, resources in producerList.items():
                pl_name = "pl_" + str(resources) + "_" + str(pe)
                pl = self.platform.find_communication_resource(pl_name)
                produce_resources.append(pl)
                produce = CommunicationPhase("produce", produce_resources, "write")
                prim.add_producer(pe, [produce])
            comsume_resources = []
            for pe, resources in consumerList.items():
                pl_name = "pl_" + str(resources) + "_" + str(pe)
                pl = self.platform.find_communication_resource(pl_name)
                comsume_resources.append(pl)
                consume = CommunicationPhase("consume", comsume_resources, "read")
                prim.add_consumer(pe, [consume])
            platform.add_primitive(prim)

class DesignerPlatformCGRA(Platform):
    def __init__(
        self,
        cgra,
        name="cgra",
        symmtries_json=None,
        embedding_json=None,
    ):
        if not isinstance(cgra, Processor):
            cgra = instantiate(cgra)
        super(DesignerPlatformCGRA, self).__init__(
            name,
            symmtries_json,
            embedding_json
        )
        designer = CGRAPlatformDesigner(self)
        designer.setSchedulingPolicy("FIFO", 1000)
        makeCGRA(
            name,
            designer,
            cgra,
            16
        )

class makeCGRA(cluster):
    def __init__(
        self,
        name,
        designer,
        cgra,
        num_pes
    ):
        super(makeCGRA, self).__init__(name,designer)

        size = int(math.sqrt(num_pes))
        if (size ** 2 != num_pes):
            raise RuntimeError("Number of PEs must be square!")

        cgraParams = peParams(cgra)
        # bramParams = l1Params(cgra.frequency_domain.frequency)
        # imParams = InMemParams()
        # omParams = OutMemParams()

        designer.setSchedulingPolicy("FIFO", 1000)

        cluster_cgra = cluster(f"cluster_cgra", designer)
        self.addCluster(cluster_cgra)

        # inMem = cluster_cgra.addStorage("IN_MEM", *imParams)
        # outMem = cluster_cgra.addStorage("OUT_MEM", *omParams)
        pes = []
        for i in range(num_pes):
            pe = cluster_cgra.addPeToCluster(f"pe{i:02d}", *cgraParams)
            pes.append(pe)
        
        designer.connectCgraPes(pes, size)

        physicalLink = CommunicationResource(
            "electric",
            FrequencyDomain("fd_electric", 250000000.0),
            CommunicationResourceType.PhysicalLink,
            0,
            0,
            100,
            60,
        )
        designer.addPhysicalLink(physicalLink)
        designer.generatePrimitivesForPes(pes)

def peParams(processor):
    return (
        processor.type,
        processor.frequency_domain,
        processor.power_model,
        processor.context_load_cycles,
        processor.context_store_cycles,
        processor.n_threads,
    )


# def l1Params(freq):
#     return (1, 1, 8, 8, freq)

# # Need to know the exact parameters from UPM
# def InMemParams():
#     return (120, 120, 8, 8, 933000000.0)

# def OutMemParams():
#     return (120, 120, 8, 8, 933000000.0)

