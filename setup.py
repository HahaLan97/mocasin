import distutils.cmd
import os
import urllib.request
import sys
import tarfile
import tempfile

from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
from doc.build_doc import BuildDocCommand
import subprocess

project_name = "pykpn"
version = "0.1"

install_requirements = [
    'argparse',
    'arpeggio',
    'cvxpy',
    'cvxpy<1.2' if sys.version_info < (3, 7) else 'cvxpy',
    'cvxopt',
    'deap',
    'h5py',
    'hydra-core>=1.0.3,<1.1.0',
    'scipy',
    'scipy<1.6.0' if sys.version_info < (3, 7) else 'scipy',
    'lxml',
    'matplotlib',
    'networkx',
    'numba',
    'numpy',
    'pint',
    'pydot',
    'pympsym>=0.5',
    'pyyaml',
    'pyxb',
    'recordclass',
    'simpy',
    'sortedcontainers',
    'termcolor',
    'tqdm',
]
setup_requirements = ['pytest-runner', 'sphinx', 'numpy']


if sys.version_info < (3, 7):
    install_requirements.append('dataclasses')


class InstallPynautyCommand(distutils.cmd.Command):
    """A custom command to install the pynauty dependency"""

    description = "install the pynauty dependency"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Run the command.

        First, run ``make pynauty`` to build the c library. Then, run ``python
        setup.py install`` to install pynauty.
        """
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            print("Downloading nauty")
            urllib.request.urlretrieve(
                "http://users.cecs.anu.edu.au/~bdm/nauty/nauty27r1.tar.gz",
                "nauty27r1.tar.gz")
            print("Downloading pynauty")
            urllib.request.urlretrieve(
                "https://web.cs.dal.ca/~peter/software/pynauty/pynauty-0.6.0.tar.gz",
                "pynauty-0.6.0.tar.gz")
            print("Extracting pynauty")
            with tarfile.open("pynauty-0.6.0.tar.gz") as tar:
                tar.extractall(".")
            print("Extracting nauty")
            with tarfile.open("nauty27r1.tar.gz") as tar:
                tar.extractall("pynauty-0.6.0/")
            os.rename("pynauty-0.6.0/nauty27r1", "pynauty-0.6.0/nauty")
            print("Build pynauty")
            subprocess.check_call(["make", "pynauty"],
                                  cwd=f"{tmpdir}/pynauty-0.6.0")
            print("Install pynauty")
            subprocess.check_call(["python", "setup.py", "install"],
                                  cwd=f"{tmpdir}/pynauty-0.6.0")
        os.chdir(cwd)


class InstallCommand(install):

    def run(self):
        self.run_command('pynauty')
        # XXX Actually install.run(self) should be used here. But there seems
        # to be a bug in setuptools that skips installing the required
        # packages... The line below seems to fix this.
        # See: https://cbuelter.wordpress.com/2015/10/25/extend-the-setuptools-install-command/comment-page-1/
        self.do_egg_install()


class DevelopCommand(develop):

    def run(self):
        develop.run(self)
        self.run_command('pynauty')

setup(
    name=project_name,
    version=version,
    packages=find_packages(),
    install_requires=install_requirements,
    setup_requires=setup_requirements,
    tests_require=['pytest', 'pytest_mock'],
    command_options={
        'build_sphinx': {
            'project': ('setup.py', project_name),
            'version': ('setup.py', version),
            'release': ('setup.py', version),
            'source_dir': ('setup.py', 'doc'),
            'build_dir': ('setup.py', 'doc/build'),
        }
    },
    cmdclass={
        'doc': BuildDocCommand,
        'pynauty': InstallPynautyCommand,
        'install': InstallCommand,
        'develop': DevelopCommand,
    },
    entry_points={'console_scripts': ['pykpn=pykpn.__main__:main',
                                      'pykpn_profile=pykpn.__main__:profile' ]},
    include_package_data=True,
)
