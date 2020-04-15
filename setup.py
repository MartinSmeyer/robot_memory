#!/usr/bin/env python3

import setuptools


setuptools.setup(name='mirobot-py',
                 version='0.9',
                 description="A Python interface library for WKlata's Mirobot",
                 author='Sourabh Cheedella',
                 author_email='cheedella.sourabh@gmail.com',
                 long_description=open("README.md", "r").read(),
                 long_description_content_type='text/markdown',
                 url="https://github.com/rirze/mirobot-py",
                 packages=['mirobot'],
                 classifiers=[
                     "Programming Language :: Python :: 3",
                     "License :: OSI Approved :: MIT License",
                     "Operating System :: OS Independent",
                 ],
                 python_requires='>=3.6',
                 install_requires=open('requirements.txt', 'r').read().splitlines(),
                 package_dir={'mirobot': 'mirobot'},
                 package_data={'mirobot': ['resources/*']}
)
