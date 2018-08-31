#!/usr/bin/python
import re
import sys
import json
import logging
import argparse

from . import dc_oracle
from . import dc_sample
from . import dc_volume
from . import dc_settings as conf
from . import perturbationManager as p
from pykpn.common import logging
from pykpn.util import plot # t-SNE plotting stuff
import numpy as np
import matplotlib.pyplot as plt
from ... import representations as reps

from pykpn.common import logging

log = logging.getLogger(__name__)

class ThingPlotter(object):
    def plot_samples(self,samples):
        """ Plot sample points of the from [(x1,x2,...,xn), Boolean] """
        for _sample in samples:
            if samples[_sample]:
                plt.plot(_sample[0], _sample[1],"o", color='b')
            else:
                plt.plot(_sample[0], _sample[1],"o", color='r')
        plt.xticks(range(0, conf.max_pe, 1))
        plt.yticks(range(0, conf.max_pe, 1))
        center_x = sorted(pert_res_list)
        plt.show()

    def plot_curve(self, data):
        interval = int(conf.max_samples/10)
        for _j in range(0, conf.max_samples, 1):
            plt.plot(_j, data[_j],"o", color='b')
        plt.xticks(range(0, conf.max_samples, interval))
        plt.yticks(np.arange(0, 1, 0.1))
        plt.show()

    def plot_perturbations(sef, pert_res_list):
        # the first list element is the center
        x = []
        y = []
        for i,p in enumerate(sorted(pert_res_list, reverse=True)):
            if p is pert_res_list[0]:
                center_x = i
                break
                
        center_y = pert_res_list[0]
        for i,p in enumerate(sorted(pert_res_list, reverse=True)):
            x.append(i)
            y.append(p)

        plt.scatter(x,y)
        plt.scatter(center_x, center_y, color='r')
        plt.xlabel("Mappings")
        plt.ylabel("Perturbations Passed")
        plt.show()

class DesignCentering(object):

    def __init__(self, init_vol, distr, oracle):
        np.random.seed(conf.random_seed)
        type(self).distr = distr
        type(self).vol = init_vol
        type(self).oracle = oracle
        type(self).samples = {}
        type(self).p_value = self.__adapt_poly(conf.hitting_propability, conf.deg_p_polynomial)
        type(self).s_value = self.__adapt_poly(conf.step_width, conf.deg_s_polynomial)

    def __adapt_poly(self, support_values, deg):
        tp = ThingPlotter()
        num = len(support_values)
        x_interval = (conf.max_samples/(num - 1))
        x = []
        y = []
        ret = []
        for _i in range(0,num,1):
            x.append(_i * x_interval)
            y.append(support_values[_i])
        coeff = np.polyfit(x, y, deg)
        poly = np.poly1d(coeff)
        for _j in range(0, conf.max_samples, 1):
            ret.append(poly(_j))
        if (conf.show_polynomials):
            tp.plot_curve(ret)
        return ret

    def ds_explore(self):
        """ explore design space (main loop of the DC algorithm) """

        s_set = dc_sample.SampleSet()
        for i in range(0, conf.max_samples, conf.adapt_samples):
            s = dc_sample.SampleGeometricGen()
            #M = finiteMetricSpaceLP(exampleClusterArch,d=2)
            #M = reps.finiteMetricSpaceLPSym(reps.exampleClusterArchSymmetries,d=2)
            #s = dc_sample.MetricSpaceSampleGen(M)
            log.debug("dc: Current iteration {}".format(i))
            # TODO: may genrate identical samples which makes things ineffective 
            samples = s.gen_samples_in_ball(type(self).vol, type(self).distr, conf.adapt_samples)
            #print(samples)
            #print(str([s.sample for s in samples]))

            #serial
            #for s in samples:
            #    s.feasible = type(self).oracle.validate(s) #validate one sample
            #parallel

            #generate mapping from sample
            #for s in samples:
            #    m = genenrate_mapping(s)
            #    mappings.append(m)

            #put samples as paramater in simulation
            log.debug("dc: Input samples:\n {}".format(samples))
            samples = type(self).oracle.validate_set(samples) # validate multiple samples
            log.debug("dc: Output samples:\n {}".format(samples))



            #print("list {}".format(feasible_list))
            #for s in samples:
            #    print("Feasible: {}".format(s.feasible))
            #print(s)



            #for s in samples:
                # add to internal overall sample set
            #    type(self).samples.update({s.sample2tuple():s.feasible})
            
            s_set.add_sample_list(samples)
            s_set.add_sample_group(samples)

            log.debug("dc: Output fesaible samples:\n {}".format(s_set.get_feasible()))
            old_center = type(self).vol.center
            center = type(self).vol.adapt_center(s_set)
           # if not type(self).oracle.validate(dc_sample.GeometricSample(center)): #this breaks the rest!
           #     c_cur = dc_sample.GeometricSample(center)
           #     c_old = dc_sample.GeometricSample(old_center)
           #     new_center = type(self).vol.correct_center(s_set, c_cur, c_old)
           #     print("Correction of infeasible center: {} take {} instead".format(center, new_center))
            cur_p = type(self).vol.adapt_volume(s_set, type(self).p_value[i], type(self).s_value[i])
            log.debug("dc: center: {} radius: {:f} p: {}".format(type(self).vol.center, type(self).vol.radius, cur_p))

        #modify last sample
        #TODO build mapping from center 
        center_sample = dc_sample.Sample(sample=center)
        center_sample_list = []
        center_sample_list.append(center_sample)
        center_res_sample = type(self).oracle.validate_set(center_sample_list)
        self.visualize_mappings(s_set.sample_groups)
        log.debug("dc: center sample: {} {} {}".format(str(center_res_sample), str(center_sample), str(center)))
        return center_res_sample[0]
    
    def visualize_mappings(self, sample_groups):
        # put all evaluated samples in a big array
        mappings = []
        exec_times = []
        log.debug("dc: samples to visualize: {}".format(str(sample_groups)))
        c = 0
        for g in sample_groups:
            c = c + 0.1
            for s in g:
                mappings.append(s.getSimContext().app_contexts[0].mapping)
                exec_times.append(float(s.getSimContext().exec_time / 1000000000.0))
                #exec_times.append(float(c))

        log.info("==== Drawing Mapping Space ====")
        # it seems there are samples inside
        #plot.visualize_mapping_space(mappings, exec_times)
        
        thresholds = []
        #>>> visualize feasibility threshold in T-sne
        #for e in exec_times:
        #    if e < conf.threshold:
        #        thresholds.append(1)
        #    else:
        #        thresholds.append(0)
        #thresholds[-1] = 0.5
        #>>> visualize ARM usage in T-sne
        for m in mappings:
            pes_list = list(m.platform.processors())
            procs_list = m.kpn.processes()

            # map PEs to an integer
            #pes = {}
            #for i, pe in enumerate(pes_list):
            #    pes[pe.name] = i
            res = []
            for proc in procs_list:
                res.append(m.affinity(proc).name)

            log.debug("dc: results {}".format(str(res)))
            if "ARM0" in res or "ARM1" in res:
                thresholds.append(1)
            elif "ARM0" in res and "ARM1" in res and "E00" in res:
                thresholds.append(0.8)
            elif "ARM0" in res and "ARM1" in res and  "E01" in res:
                thresholds.append(0.6)
            else:
                thresholds.append(0)
        thresholds[-1] = 0.5
        #print("thresholds: {}".format(thresholds))
        plot.visualize_mapping_space(mappings, thresholds)
