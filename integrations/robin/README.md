# Robin — Dark Web OSINT Integration

[Robin](https://github.com/apurvsinghgautam/robin) is an AI-powered dark web OSINT tool by
[Apurv Singh Gautam](https://github.com/apurvsinghgautam) (MIT licensed). It routes queries through Tor to
onion search engines, uses an LLM to refine the query and filter results, scrapes the surviving pages, and
returns a cited investigation summary.

This directory holds the setup and operating guide for using Robin alongside the **OSINT Analyst** agent.
Robin's source is **not** vendored here — it stays upstream and is pulled as a Docker image or a git checkout.

## Why it is registered here

`hackingtool` covers clearnet reconnaissance (WHOIS, DNS, IP geolocation, headers, TLS). It has no dark web
reach. Robin fills that gap, so the OSINT Analyst's threat-intelligence phase can cover both surfaces without
leaving the agency toolchain.

| Surface | Tool | Entry point |
|---|---|---|
| Clearnet infrastructure | `hackingtool` | `hackingtool whois / dns / ip / headers / ssl` |
| Dark web (.onion) | Robin | Streamlit UI on `http://localhost:8501` |

## Prerequisites

- **Tor** — Robin searches exclusively through a local Tor SOCKS5 proxy on `127.0.0.1:9050`.
  - Linux / WSL: `sudo apt install tor`
  - macOS: `brew install tor`
  - The Docker image bundles Tor and starts it in its entrypoint, so nothing is needed on the host.
- **Python 3.10+** — only for the non-Docker path.
- **One LLM provider** — a hosted API key, or a local Ollama / llama.cpp / OpenAI-compatible endpoint.

## Install

### Docker (recommended)

```bash
cp integrations/robin/.env.example .env
# edit .env and set exactly one provider

docker pull apurvsg/robin:latest

docker run --rm \
   -v "$(pwd)/.env:/app/.env" \
   -v "$(pwd)/investigations:/app/investigations" \
   --add-host=host.docker.internal:host-gateway \
   -p 8501:8501 \
   apurvsg/robin:latest
```

Open `http://localhost:8501`. The `investigations/` mount persists saved investigations across restarts;
without it they vanish when the container exits.

### Python checkout

```bash
git clone https://github.com/apurvsinghgautam/robin.git
cd robin
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp /path/to/agency_agents/integrations/robin/.env.example .env
# edit .env, then make sure Tor is running
streamlit run ui.py
```

## Configuration

All variables live in Robin's `.env` (template: [`.env.example`](.env.example)). A hosted model only appears
in the UI's model picker once its key is present, so an empty list of cloud models means a missing key.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Enables the `gpt-*` models |
| `ANTHROPIC_API_KEY` | Enables the `claude-sonnet-*` models |
| `GOOGLE_API_KEY` | Enables the `gemini-2.5-*` models |
| `OPENROUTER_API_KEY` / `OPENROUTER_BASE_URL` | Enables the `*-openrouter` models; base URL defaults to `https://openrouter.ai/api/v1` |
| `OLLAMA_BASE_URL` | Local Ollama; models are discovered at runtime |
| `LLAMA_CPP_BASE_URL` | Local llama.cpp server |
| `CUSTOM_API_BASE_URL` / `CUSTOM_API_KEY` / `CUSTOM_API_MODEL` | Any other OpenAI-compatible provider |

Under Docker, a local Ollama is reachable at `http://host.docker.internal:11434` and may need
`OLLAMA_HOST=0.0.0.0 ollama serve &` to accept connections from the container.

## How the pipeline works

1. **Refine** — the LLM rewrites the analyst's question into a short (≤5 word) engine query with no boolean operators.
2. **Search** — the refined query fans out over Tor to 16 onion search engines (Ahmia, OnionLand, Torgle,
   Amnesia, Kaizer, Anima, Tornado, TorNet, Torland, Find Tor, Excavator, Onionway, Tor66, OSS, Torgol,
   The Deep Searches), then results are deduplicated by URL.
3. **Filter** — the LLM discards results irrelevant to the original question.
4. **Scrape** — surviving onion pages are fetched through Tor with hard caps: 1 MB per download, 50k characters
   extracted, 2k characters returned per page, and only HTML/plaintext content types.
5. **Summarize** — the LLM produces a cited summary under the selected research preset.
6. **Follow up** — questions are answered from that investigation's own scraped data (no re-search), and
   suggested pivots can launch a fresh investigation.

The sidebar's health panel reports Tor proxy reachability, LLM credential validity, and per-engine status —
check it first when results come back empty.

## Research presets

| Preset | Use it for |
|---|---|
| Dark Web Threat Intel | General threat landscape, actor chatter, marketplace activity |
| Ransomware / Malware Focus | Leak sites, RaaS affiliates, double-extortion claims |
| Personal / Identity Investigation | Exposed identity documents and personal data |
| Corporate Espionage / Data Leaks | Source code, credentials, and internal document dumps |

Each preset accepts free-text custom instructions that are appended to its system prompt.

## Where it fits the OSINT Analyst workflow

Robin belongs in **Phase 2 (Passive Enumeration)** and **Phase 3 (Correlation & Analysis)** of the
[OSINT Analyst](../../agents/security/security-osint-analyst.md) workflow:

```
Phase 1  Seed data          →  domains, emails, org names, actor handles
Phase 2  Passive enum       →  hackingtool whois/dns/ip   (clearnet)
                              Robin investigation         (dark web)
Phase 3  Correlation        →  pivot onion findings back to clearnet:
                              hackingtool ip <addr> / hackingtool whois <domain>
Phase 4  Reporting          →  Robin's saved investigation JSON + confidence ratings
```

Robin's summaries are LLM-generated from scraped pages, so treat every claim as **possible** until the
underlying source is read directly and re-rated under the agent's confidence scheme.

## Operating notes

- Robin only reads publicly reachable onion pages, which keeps it inside the OSINT Analyst's passive-only
  principle. Do not use it to interact with, authenticate to, or transact on any service.
- Queries and scraped page content are sent to whichever LLM provider is configured. Use a local model
  (Ollama / llama.cpp) when the investigation itself is sensitive.
- Dark web access and the handling of data recovered from it are regulated differently across jurisdictions.
  Confirm authorization and applicable law before running an investigation, and apply the agent's data
  retention and deletion rules to anything saved under `investigations/`.
- Robin depends on third-party onion engines. Individual engines going dark is normal; an empty result set is
  more often an engine or Tor problem than a genuine absence of findings.

## Troubleshooting

| Symptom | Check |
|---|---|
| No results from any engine | Tor running and listening on `127.0.0.1:9050`; health panel engine status |
| Model picker is empty or missing a provider | The provider's key is set in `.env` and the file is mounted into the container |
| Ollama models not discovered | `OLLAMA_BASE_URL` uses `host.docker.internal` under Docker and Ollama is bound to `0.0.0.0` |
| Saved investigations disappear | Mount `investigations/` into the container |

## Upstream

- Repository: https://github.com/apurvsinghgautam/robin
- Docker Hub: https://hub.docker.com/r/apurvsg/robin
- License: MIT — Copyright (c) 2025 Apurv Singh Gautam
