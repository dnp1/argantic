from importlib.machinery import SourceFileLoader
from pathlib import Path
from setuptools import setup

description = 'Data parsing for aiohttp using pydantic'
THIS_DIR = Path(__file__).resolve().parent
try:
    long_description = '\n\n'.join([
        THIS_DIR.joinpath('README.md').read_text(),
        THIS_DIR.joinpath('HISTORY.md').read_text()
    ])
except FileNotFoundError:
    long_description = description + '.\n\nSee https://github.com/dnp1/argantic for documentation.'

# avoid loading the package before requirements are installed:
version = SourceFileLoader('version', 'argantic/version.py').load_module()

setup(
    name='argantic',
    version=str(version.VERSION),
    description=description,
    long_description=long_description,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: Unix',
        'Operating System :: POSIX :: Linux',
        'Environment :: MacOS X',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet',
    ],
    author='Danilo Pereira',
    author_email='developer@danilo.info',
    url='https://github.com/dnp1/argantic',
    license='Apache License 2.0',
    packages=['argantic'],
    python_requires='>=3.6',
    zip_safe=True,
    install_requires=[
        'aiohttp>3,<4',
        'pydantic==0.14',
        'dataclasses>=0.6;python_version<"3.7"'
    ],
)
