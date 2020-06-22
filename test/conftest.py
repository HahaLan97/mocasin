# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard, Felix Teweleit


import pytest
import os


@pytest.fixture
def datadir(tmpdir):
    """
    Fixture that prepares a data directory for running tests. The resulting
    directory contains symbolic links to the examples directory.
    """
    module_path = os.path.dirname(__file__)
    examples_path = os.path.join(module_path, "..", "examples")

    os.symlink(os.path.join(examples_path, "conf"),
               os.path.join(tmpdir, "conf"))
    os.symlink(os.path.join(examples_path, "slx"),
               os.path.join(tmpdir, "slx"))
    os.symlink(os.path.join(examples_path, "tgff"),
               os.path.join(tmpdir, "tgff"))
    os.symlink(os.path.join(examples_path, "csv"),
               os.path.join(tmpdir, "csv"))

    return tmpdir


@pytest.fixture
def expected_dir(request):
    module_path = os.path.dirname(request.module.__file__)
    module_name, _ = os.path.splitext(os.path.basename(request.module.__file__))
    return os.path.join(module_path, "expected_%s" % module_name)


@pytest.fixture(params=["exynos", "multidsp", "parallella"])
def slx_platform(request):
    return request.param


@pytest.fixture(params=["audio_filter", "hog", "speaker_recognition"])
def slx_kpn(request):
    return request.param


@pytest.fixture(params=[("audio_filter", "exynos", "'2017.10'"),
                        ("audio_filter", "multidsp", "'2017.10'"),
                        ("audio_filter", "parallella", "'2017.04'"),
                        ("hog", "exynos", "'2017.04'"),
                        ("speaker_recognition", "exynos", "'2017.04'")])
def slx_kpn_platform_pair(request):
    return request.param


@pytest.fixture(params=["auto-indust-cords",
                        "auto-indust-cowls",
                        "auto-indust-mocsyn-asic",
                        "auto-indust-mocsyn",
                        "consumer-cords",
                        "networking-cowls",
                        "office-automation-mocsyn-asic",
                        "telecom-mocsyn"])
def tgff(request):
    return request.param

@pytest.fixture(params=[("EXISTS fft_l MAPPED ARM00", 0),
                        ("EXISTS NOT ARM00 PROCESSING", 1),
                        ("EXISTS RUNNING TOGETHER [src, fft_r, ifft_r ]", 2),
                        ("EXISTS (fft_l MAPPED ARM06 OR fft_l MAPPED ARM05) AND (ARM00 PROCESSING)", 3)])
def audio_filter_exynos_query(request):
    return request.param

@pytest.fixture(params=[("EXISTS NOT fft_l MAPPED dsp2", 0),
                        ("EXISTS dsp3 PROCESSING", 1),
                        ("EXISTS RUNNING TOGETHER [fft_l, fft_r, filter_r ]", 2),
                        ("EXISTS (fft_l MAPPED dsp3 OR fft_l MAPPED dsp2) AND (dsp4 PROCESSING)", 3)])
def audio_filter_multidsp_query(request):
    return request.param

@pytest.fixture(params=[("EXISTS ifft_l MAPPED E02", 0),
                        ("EXISTS E07 PROCESSING", 1),
                        ("EXISTS NOT RUNNING TOGETHER [fft_l, src, sink ]", 2),
                        ("EXISTS (E08 PROCESSING) OR (E09 PROCESSING)", 3)])
def audio_filter_parallella_query(request):
    return request.param

@pytest.fixture(params=[("EXISTS DISTRIBUTOR MAPPED ARM05", 0),
                        ("EXISTS ARM07 PROCESSING", 1),
                        ("EXISTS RUNNING TOGETHER [DETECTION_WORKER_0, DETECTION_WORKER_1, DETECTION_WORKER_2 ]", 2),
                        ("EXISTS RUNNING TOGETHER [DETECTION_WORKER_1, DETECTION_WORKER_2 ] AND DETECTION_WORKER_5 \
                        MAPPED ARM07 AND ARM04 PROCESSING", 3)])
def hog_query(request):
    return request.param

@pytest.fixture(params=[("EXISTS NOT readwave_stage1 MAPPED ARM00", 0),
                        ("EXISTS ARM05 PROCESSING", 1),
                        ("EXISTS RUNNING TOGETHER [Worker_0, Worker_1, Worker_2 ]", 2),
                        ("EXISTS RUNNING TOGETHER [hamming_stage2, ShifterDLP, sink ] OR \
                        RUNNING TOGETHER [FFT_stage3, melFreqWrap_stage4 ]", 3)])
def speaker_recognition_query(request):
    return request.param

@pytest.fixture
def csv_file_path():
    return "csv/test_values.csv"