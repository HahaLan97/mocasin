# Copyright (C) 2017-2019 TU Dresden
# All Rights Reserved
#
# Authors: Gerald Hempel, Andres Goens

import numpy as np

from pykpn.design_centering import oracle
from pykpn.design_centering import sample as dc_sample
from pykpn.design_centering import util as dc_util
from pykpn.util import logging
from pykpn.util import plot # t-SNE plotting stuff
from pykpn.representations.__init__ import RepresentationType
import sys

log = logging.getLogger(__name__)


class DesignCentering(object):
    def __init__(self, init_vol, oracle, representation, hitting_probability, hitting_probability_threshold,
                 deg_p_polynomial, deg_s_polynomial, step_width, adapt_samples, max_samples, record_samples,
                 show_polynomials, distr, visualize_mappings, keep_metrics, representation_type, max_pe):
        type(self).vol = init_vol
        type(self).oracle = oracle
        type(self).representation = representation
        type(self).samples = {}

        type(self).adapt_samples = adapt_samples
        type(self).max_samples = max_samples
        type(self).record_samples = record_samples
        type(self).show_polynomials = show_polynomials
        type(self).distr = distr
        type(self).visualize_mappings = visualize_mappings
        type(self).keep_metrics = keep_metrics
        type(self).representation_type = representation_type
        type(self).max_pe = max_pe



        type(self).p_value = self.__adapt_poly(hitting_probability, deg_p_polynomial)
        type(self).s_value = self.__adapt_poly(step_width, deg_s_polynomial)
        if hitting_probability_threshold <= 1:
            self.p_threshold = hitting_probability_threshold
        else:
            log.error(f"Hitting probability threshold ({hitting_probability_threshold}) is unreachable (>1)")
            sys.exit(1)

    def __adapt_poly(self, support_values, deg):
        num = len(support_values)
        x_interval = (type(self).max_samples/(num - 1))
        x = []
        y = []
        ret = []

        for _i in range(0, num, 1):
            x.append(_i * x_interval)
            y.append(support_values[_i])

        coeff = np.polyfit(x, y, deg)
        poly = np.poly1d(coeff)

        for _j in range(0, type(self).max_samples, 1):
            ret.append(poly(_j))

        if type(self).show_polynomials:
            tp = dc_util.ThingPlotter()
            tp.plot_curve(ret, type(self).max_samples)

        return ret

    def __has_duplicate(self, samples):
        seen = set()
        uniq_samples = []
        for s in samples:
            s = s.sample2simpleTuple()
            if s not in seen:
                seen.add(s)
                uniq_samples.append(s)
        return len(uniq_samples)

    def ds_explore(self):
        """ explore design space (main loop of the DC algorithm) """
        history = {'samples' : [], 'centers' : [], 'radii' : []}

        #check starting center
        center = self.vol.center
        current_center = dc_sample.Sample(sample=center, representation=self.representation)
        best_area = 0
        best_center = current_center

        for i in range(0, type(self).max_samples, type(self).adapt_samples):
            s = dc_sample.SampleGen(self.representation, type(self).max_pe)
            
            log.debug("dc: Current iteration {}".format(i))
            s_set = dc_sample.SampleSet()
            samples = s.gen_samples_in_ball(type(self).vol, self.distr, nsamples=type(self).adapt_samples)
            dup = type(self).adapt_samples - self.__has_duplicate(samples)

            if dup > 0:
                log.warning("DC: Sample-list of {} elements has {} duplicates.".format(type(self).adapt_samples, dup))
            
            #put samples as paramater in simulation
            log.info("dc: Input samples:\n {} ".format(samples))
            samples = type(self).oracle.validate_set(samples) # validate multiple samples
            log.info("dc: Output samples:\n {}".format(samples))

            s_set.add_sample_list(samples)
            s_set.add_sample_group(samples)

            log.debug("dc: Output fesaible samples:\n {}".format(s_set.get_feasible()))
            center = type(self).vol.adapt_center(s_set)
            #center = list(map(int, center))
            current_center = dc_sample.Sample(sample=center, representation=self.representation)
            self.oracle.validate_set([current_center])

            if not current_center.getFeasibility():
                log.warning("DC iteration with a non-feasible center")

            # if not type(self).oracle.validate(dc_sample.GeometricSample(center)): #this breaks the rest!
            #     c_cur = dc_sample.GeometricSample(center)
            #     c_old = dc_sample.GeometricSample(old_center)
            #     new_center = type(self).vol.correct_center(s_set, c_cur, c_old)
            #     print("Correction of infeasible center: {} take {} instead".format(center, new_center))
            cur_p = type(self).vol.adapt_volume(s_set, type(self).p_value[i], type(self).s_value[i])
            log.debug("dc: center: {} radius: {:f} p_emp: {}, target_p {}".format(type(self).vol.center,
                                                                                  type(self).vol.radius,
                                                                                  cur_p,
                                                                                  self.p_value[i]))
            area = cur_p * self.vol.radius**self.vol.true_dim

            if cur_p >= self.p_threshold and area >= best_area and current_center.getFeasibility():
                best_area = area
                best_center = center
                log.info(f"found a better center (radius {self.vol.radius}, p {cur_p}). updating.")

            if self.record_samples:
                for sample in samples:
                    history['samples'].append(sample)
                history['centers'].append(current_center)
                history['radii'].append(self.vol.radius)

        if best_area == 0:
            log.error("Could not find a center within hitting probability threshold."
                      "Returning last center candidate found.")
            best_center = center

        #modify last sample
        #TODO build mapping from center (this destroys parallel execution)
        center_sample = dc_sample.Sample(sample=best_center, representation=self.representation)
        center_sample_result = type(self).oracle.validate_set([center_sample])

        if self.visualize_mappings:

            if(self.keep_metrics):
                self.visualize_mappings(s_set.sample_groups, type(self).adapt_samples, history['centers'])
            else:
                self.visualize_mappings(s_set.sample_groups)

        log.debug("dc: center sample: {} {} {}".format(str(center_sample_result), str(center_sample), str(center)))

        return center_sample_result[0], history
    
    def visualize_mappings(self, sample_groups, tick=0, center_history=[]):
        # put all evaluated samples in a big array
        mappings = []
        exec_times = []

        history = type(self).oracle.validate_set(center_history)
        for h in history:
            mappings.append(h.getSimContext().app_contexts[0].mapping)
            exec_times.append(0)

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
        plot.visualize_mapping_space(mappings, exec_times,
                                     None,
                                     RepresentationType[self.representation_type],
                                     tick,
                                     len(center_history))

class DesignCenteringFromHydra(DesignCentering):
    def __init__(self, init_vol, oracle, representation, cfg):
        hitting_probability = cfg['hitting_probability']
        hitting_probability_threshold = cfg['hitting_probability_threshold']
        deg_p_polynomial = cfg['deg_p_polynomial']
        deg_s_polynomial = cfg['deg_s_polynomial']
        step_width = cfg['step_width']
        adapt_samples = cfg['adapt_samples']
        max_samples = cfg['max_samples']
        record_samples = cfg['record_samples']
        show_polynomials = cfg['show_polynomials']
        distr = cfg['distr']
        visualize_mappings = cfg['visualize_mappings']
        keep_metrics = cfg['keep_metrics']
        representation_type = cfg['representation']
        max_pe = cfg['max_pe']


        super(DesignCenteringFromHydra, self).__init__(init_vol, oracle, representation,
                                                       hitting_probability,
                                                       hitting_probability_threshold,
                                                       deg_p_polynomial,
                                                       deg_s_polynomial,
                                                       step_width,
                                                       adapt_samples,
                                                       max_samples,
                                                       record_samples,
                                                       show_polynomials,
                                                       distr,
                                                       visualize_mappings,
                                                       keep_metrics,
                                                       representation_type,
                                                       max_pe)
