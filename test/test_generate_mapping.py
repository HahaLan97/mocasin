# Copyright (C) 2020 TU Dresden
# All Rights Reserved
#
# Authors: Felix Teweleit

import subprocess
import os

def test_generate_mapping_slx(datadir, mapper, slx_kpn):
    subprocess.check_call(["pykpn", "generate_mapping",
                           "kpn=%s" % slx_kpn,
                           "platform=exynos",
                           "mapper=%s" % mapper,
                           "outdir=../../../",
                           "trace=slx_default"],
                          cwd=datadir)

    try:
        file_path = os.path.join(datadir, 'generated_mapping')
        file = open(file_path, 'r')
        file.close()
    except FileNotFoundError:
        assert False

def test_generate_mapping_tgff(datadir, mapper, tgff):
    tgff_dir = os.path.join(datadir, 'tgff/e3s-0.9')
    subprocess.check_call(["pykpn", "generate_mapping",
                           "kpn=tgff_reader",
                           "platform=tgff_reader",
                           "mapper=%s" % mapper,
                           "tgff.directory=%s" % tgff_dir,
                           "tgff.file=%s.tgff" % tgff,
                           "outdir=../../../",
                           "trace=tgff_reader"],
                          cwd=datadir)
    try:
        file_path = os.path.join(datadir, "best_time.txt")
        file = open(file_path, 'r')
        file.close()
    except FileNotFoundError:
        assert False
