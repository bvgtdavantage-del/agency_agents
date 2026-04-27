"""
Setup configuration for agent_router package
"""

from setuptools import setup, find_packages

setup(
    name='agency_agents',
    version='0.2.0',
    description='Intelligent task routing and persistent knowledge system for specialized agents',
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
        ],
    },
    package_data={
        'agent_router': ['agents.yaml'],
    },
    include_package_data=True,
)
