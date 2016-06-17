#!/usr/bin/env python3

from setuptools import setup

setup(
    name='bot',
    version='0.0.1',
    description='A Python 3.5, asyncio- and decorator-based IRC framework',
    author='minus',
    author_email='minus@mnus.de',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='irc bot framework',
    packages=['bot'],
)