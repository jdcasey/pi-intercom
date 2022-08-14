#!/usr/bin/env python3

from setuptools import setup, find_packages

deps = []
with open("requirements.in.txt") as f:
    for line in f.readlines():
        line = line.strip()
        if len(line) > 0 and not line.startswith("#"):
            deps.append(line)

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
    install_requires=deps,
    include_package_data=True,
    test_suite="tests",
    entry_points={
      'console_scripts': [
        'intercom = intercompy:run',
        'intercompy-test-gpio = intercompy:selftest_gpio',
        'intercompy-session-setup = intercompy:session_setup'
      ],
    }
)

