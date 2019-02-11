
from setuptools import setup, find_packages

setup(
    name='pypigit',
    version='0.2.7',
    description='A simple PyPi-like server that automatically generates python packages from git tags',
    author='desertkun',
    license='MIT',
    author_email='desertkun@gmail.com',
    url='https://github.com/anthill-utils/pypigit',
    packages=find_packages(),
    include_package_data=True,
    package_data={
      "pypigit": ["pypigit/templates/*.html"]
    },
    zip_safe=False,
    install_requires=[
        "tornado>=5.0",
        "GitPython>=2.1.7",
        "giturlparse.py>=0.0.5",
        "PyYAML>=3.13"
    ]
)
