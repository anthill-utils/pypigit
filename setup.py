
from setuptools import setup, find_packages

setup(
    name='pypigit',
    version='0.1.0',
    description='A simple PyPi-like server that uses git repositories as a source of python packages',
    author='desertkun',
    license='MIT',
    author_email='desertkun@gmail.com',
    url='https://github.com/anthill-utils/pypigit',
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        "tornado==5.1.1",
        "GitPython==2.1.7",
        "giturlparse.py==0.0.5"
    ]
)
