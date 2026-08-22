"""Tests for the Robin dark web OSINT integration"""

import os
import re
import yaml
import pytest

from agent_router.config import AgentConfig
from agent_router.router import AgentRouter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'agent_router', 'agents.yaml')
INTEGRATION_DIR = os.path.join(PROJECT_ROOT, 'integrations', 'robin')
AGENT_MD = os.path.join(PROJECT_ROOT, 'agents', 'security', 'security-osint-analyst.md')

DARK_WEB_TASKS = [
    "search the dark web for mentions of our company",
    "run a darkweb investigation on this ransomware group",
    "find leak site posts naming our subsidiary",
    "check onion sites for our leaked credentials",
    "profile this threat actor across tor hidden services",
]


def _raw_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _osint_agent():
    for agent in _raw_config()['security']:
        if agent['name'] == 'OSINT Analyst':
            return agent
    raise AssertionError("OSINT Analyst not registered in agents.yaml")


@pytest.fixture
def router():
    """Router backed by agents.yaml, bypassing on-disk file_path validation.

    Most registered agents still carry the original author's absolute file_path
    values, so AgentConfig's loader cannot read the real config here.
    """
    AgentConfig._config_cache = _raw_config()
    AgentConfig._cached_path = CONFIG_PATH
    yield AgentRouter()
    AgentConfig.clear_cache()


class TestRobinIntegrationDocs:
    def test_integration_readme_exists(self):
        assert os.path.isfile(os.path.join(INTEGRATION_DIR, 'README.md'))

    def test_env_example_exists(self):
        assert os.path.isfile(os.path.join(INTEGRATION_DIR, '.env.example'))

    def test_env_example_carries_no_values(self):
        with open(os.path.join(INTEGRATION_DIR, '.env.example')) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                assert line.endswith('='), f"env template must not ship a value: {line}"

    def test_readme_documents_every_config_variable(self):
        with open(os.path.join(INTEGRATION_DIR, '.env.example')) as f:
            variables = [
                line.split('=')[0].strip()
                for line in f
                if line.strip() and not line.strip().startswith('#')
            ]
        with open(os.path.join(INTEGRATION_DIR, 'README.md')) as f:
            readme = f.read()
        for variable in variables:
            assert variable in readme, f"{variable} is undocumented in the integration README"

    def test_readme_links_upstream_and_license(self):
        with open(os.path.join(INTEGRATION_DIR, 'README.md')) as f:
            readme = f.read()
        assert 'https://github.com/apurvsinghgautam/robin' in readme
        assert 'MIT' in readme

    def test_agent_definition_references_integration(self):
        with open(AGENT_MD) as f:
            agent_md = f.read()
        assert 'Robin' in agent_md
        assert 'integrations/robin/README.md' in agent_md

    def test_agent_definition_links_resolve(self):
        with open(AGENT_MD) as f:
            agent_md = f.read()
        agent_dir = os.path.dirname(AGENT_MD)
        for target in re.findall(r'\]\((\.\./[^)#]+)\)', agent_md):
            resolved = os.path.normpath(os.path.join(agent_dir, target.strip('`')))
            assert os.path.exists(resolved), f"broken link in agent definition: {target}"


class TestOSINTAgentRegistration:
    def test_dark_web_keywords_registered(self):
        keywords = _osint_agent()['keywords']
        for keyword in ('dark web', 'darkweb', 'onion', 'tor', 'leak site', 'threat actor'):
            assert keyword in keywords

    def test_keywords_are_unique(self):
        keywords = _osint_agent()['keywords']
        assert len(keywords) == len(set(keywords))

    def test_description_mentions_dark_web(self):
        assert 'dark web' in _osint_agent()['description'].lower()

    def test_file_path_resolves(self):
        agent = _osint_agent()
        assert os.path.isfile(os.path.join(PROJECT_ROOT, agent['file_path']))


class TestDarkWebRouting:
    @pytest.mark.parametrize('task', DARK_WEB_TASKS)
    def test_dark_web_task_routes_to_osint_analyst(self, router, task):
        agents = router.analyze_task(task)['required_agents']
        assert 'OSINT Analyst' in [agent['name'] for agent in agents]

    @pytest.mark.parametrize('task', DARK_WEB_TASKS)
    def test_dark_web_task_clears_confidence_threshold(self, router, task):
        assert router.analyze_task(task)['confidence_score'] >= 0.5

    def test_clearnet_recon_still_routes_to_osint_analyst(self, router):
        agent = router.select_agent("run a whois and dns enumeration on example.com")
        assert agent['name'] == 'OSINT Analyst'

    def test_unrelated_task_does_not_route_to_osint_analyst(self, router):
        agent = router.select_agent("write a react component for the settings page")
        assert agent['name'] != 'OSINT Analyst'
