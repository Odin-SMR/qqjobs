""" Odin qsmr processing jobs generator """
from setuptools import setup

setup(
    name='Odin Qsmr Processing Jobs Generator',
    version='1.0',
    long_description=__doc__,
    packages=['jobsgenerator'],
    entry_points={
        'console_scripts': [
            'qsmrjobs = jobsgenerator.qsmrjobs:main']
    },
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'requests',
        'pycrypto',
    ]
)
