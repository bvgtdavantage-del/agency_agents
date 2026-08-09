# Videos

Remotion composition props for [OpenMontage](https://github.com/calesthio/OpenMontage).

## agency-agents.json

A 53-second animated explainer of this repository: the agent library, the router's
keyword scoring and confidence threshold, Second Brain retrieval weights, hackingtool
in action, and the 11-rule engineering discipline.

To re-render:

```bash
git clone https://github.com/calesthio/OpenMontage.git
cd OpenMontage
make setup
cp /path/to/agency_agents/videos/agency-agents.json remotion-composer/public/demo-props/
.venv/bin/python render_demo.py agency-agents
```

Output lands in `projects/demos/renders/agency-agents.mp4`. Edit the JSON to change
text, timings, colors, or chart data — each entry in `cuts` is one timed scene.
