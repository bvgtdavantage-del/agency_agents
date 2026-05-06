"""
Setup configuration for agency_agents and hackingtool packages
"""

from setuptools import setup, find_packages

setup(
    name='agency_agents',
    version='0.3.0',
    description='Intelligent task routing, persistent knowledge, and all-in-one security research framework',
    author='Agency Agents',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'PyYAML>=6.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'second-brain=second_brain.cli:main',
            'hackingtool=hackingtool.cli:main',
        ],
    },
    package_data={
        'agent_router': ['agents.yaml'],
    },
    include_package_data=True,
)
