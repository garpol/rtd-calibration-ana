from setuptools import setup, find_packages
from pathlib import Path

# Minimal setup to install the src folder as package `rtd_calibration_vgp`
setup(
    name='rtd_calibration_vgp',
    version='0.1.0',
    packages=find_packages(where='RTD_Calibration_VGP/src'),
    package_dir={'': 'RTD_Calibration_VGP/src'},
    include_package_data=True,
    install_requires=[
        'pandas',
        'numpy',
        'matplotlib'
    ],
)
