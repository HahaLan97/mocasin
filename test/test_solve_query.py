# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Felix Teweleit

import subprocess
import os

def test_audio_filter_exynos(datadir, expected_dir, audio_filter_exynos_query):
    mapping_file = "audio_filter_exynos_%s.mapping" % audio_filter_exynos_query[1]
    out_file = os.path.join(datadir, mapping_file)

    subprocess.check_call(["pykpn", "solve_query",
                           "query=%s" % audio_filter_exynos_query[0],
                           "kpn=audio_filter",
                           "platform=exynos",
                           "output_file=%s" % out_file],
                          cwd=datadir)

    with open(out_file,'r') as f:
        line = f.readline()
        assert line != "False"
        assert len(line) > 0

def test_audio_filter_multidsp(datadir, expected_dir, audio_filter_multidsp_query):
    mapping_file = "audio_filter_multidsp_%s.mapping" % audio_filter_multidsp_query[1]
    out_file = os.path.join(datadir, mapping_file)

    subprocess.check_call(["pykpn", "solve_query",
                           "query=%s" % audio_filter_multidsp_query[0],
                           "kpn=audio_filter",
                           "platform=multidsp",
                           "output_file=%s" % out_file],
                          cwd=datadir)

    with open(out_file,'r') as f:
        line = f.readline()
        assert line != "False"

def test_audio_filter_parallella(datadir, expected_dir, audio_filter_parallella_query):
    mapping_file = "audio_filter_parallella_%s.mapping" % audio_filter_parallella_query[1]
    out_file = os.path.join(datadir, mapping_file)

    subprocess.check_call(["pykpn", "solve_query",
                           "query=%s" % audio_filter_parallella_query[0],
                           "kpn=audio_filter",
                           "platform=parallella",
                           "output_file=%s" % out_file],
                          cwd=datadir)

    with open(out_file,'r') as f:
        line = f.readline()
        assert line != "False"

def test_hog(datadir, expected_dir, hog_query):
    mapping_file = "hog_%s.mapping" % hog_query[1]
    out_file = os.path.join(datadir, mapping_file)

    subprocess.check_call(["pykpn", "solve_query",
                           "query=%s" % hog_query[0],
                           "kpn=hog",
                           "platform=exynos",
                           "output_file=%s" % out_file],
                          cwd=datadir)

    with open(out_file,'r') as f:
        line = f.readline()
        assert line != "False"

def test_speaker_recognition(datadir, expected_dir, speaker_recognition_query):
    mapping_file = "speaker_recognition_%s.mapping" % speaker_recognition_query[1]
    out_file = os.path.join(datadir, mapping_file)

    subprocess.check_call(["pykpn", "solve_query",
                           "query=%s" % speaker_recognition_query[0],
                           "kpn=speaker_recognition",
                           "platform=exynos",
                           "output_file=%s" % out_file],
                          cwd=datadir)

    with open(out_file,'r') as f:
        line = f.readline()
        assert line != "False"
