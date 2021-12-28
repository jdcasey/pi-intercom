#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    zip_safe=True,
    name='intercompy',
    version='0.0.1',
    long_description="Turn a Raspberry Pi into an intercom with Telegram",
    classifiers=[
      "Development Status :: 3 - Alpha",
      "Intended Audience :: Developers",
      "License :: OSI Approved :: GNU General Public License (GPL)",
      "Programming Language :: Python :: 3",
    ],
    keywords='telegram rpi raspberry-pi',
    author='John Casey',
    author_email='jdcasey@commonjava.org',
    url='https://github.com/jdcasey/pi-intercom',
    license='GPLv3+',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    install_requires=[
      "python-telegram-bot",
      "ruamel.yaml",
      "click",
      "pyaudio",
      'python-vlc',
      'ffmpy',
    ],
    include_package_data=True,
    test_suite="tests",
    entry_points={
      'console_scripts': [
        'intercom = intercompy:run'
      ],
    }
)

