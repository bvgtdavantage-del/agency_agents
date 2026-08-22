#!/bin/bash

#
# Bash Validation Script for the Robin Dark Web OSINT Integration
# Independently verifies that dark web tasks route to the OSINT Analyst
#
# Following Rule 4: Bash Test Validation for Math/Logic
#

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "🕵️  Validating Robin Dark Web OSINT Integration..."
echo "=================================================="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0

# The registered agents still carry the original author's absolute file_path
# values, so the config loader is bypassed here in favour of the raw YAML.
route_task() {
    python3 -c "
import os, sys, yaml
from agent_router import config as config_module
from agent_router.config import AgentConfig
from agent_router.router import AgentRouter

config_path = os.path.join(os.path.dirname(config_module.__file__), 'agents.yaml')
with open(config_path) as f:
    AgentConfig._config_cache = yaml.safe_load(f)
AgentConfig._cached_path = config_path

analysis = AgentRouter().analyze_task(sys.argv[1])
print(','.join(a['name'] for a in analysis['required_agents']))
" "$1"
}

assert_routes_to_osint() {
    local task="$1"
    echo -n "Routing: \"$task\"... "

    if route_task "$task" | grep -q "OSINT Analyst"; then
        echo -e "${GREEN}PASS${NC}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}FAIL${NC} (got: $(route_task "$task"))"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

assert_file_exists() {
    local path="$1"
    echo -n "File: $path... "

    if [ -f "$path" ]; then
        echo -e "${GREEN}PASS${NC}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo -e "${RED}FAIL${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

echo "--- Integration files ---"
assert_file_exists "integrations/robin/README.md"
assert_file_exists "integrations/robin/.env.example"
assert_file_exists "agents/security/security-osint-analyst.md"
echo ""

echo "--- Dark web routing ---"
assert_routes_to_osint "search the dark web for mentions of our company"
assert_routes_to_osint "run a darkweb investigation on this ransomware group"
assert_routes_to_osint "find leak site posts naming our subsidiary"
assert_routes_to_osint "check onion sites for our leaked credentials"
assert_routes_to_osint "profile this threat actor across tor hidden services"
echo ""

echo "--- Clearnet routing regression ---"
assert_routes_to_osint "run a whois and dns enumeration on example.com"
echo ""

echo "=================================================="
echo -e "Passed: ${GREEN}${PASS_COUNT}${NC}  Failed: ${RED}${FAIL_COUNT}${NC}"

if [ "$FAIL_COUNT" -ne 0 ]; then
    exit 1
fi

echo "✅ Robin integration validated"
