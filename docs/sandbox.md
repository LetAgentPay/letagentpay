# Sandbox

The Sandbox is an interactive testing environment inside the dashboard. It lets you create test agents, configure policies, and send purchase requests — all without affecting your production agents.

## Getting Started

1. Go to **Dashboard → Sandbox** (in the sidebar)
2. Click **Create Sandbox Agent** — creates an agent with $100 budget and auto-approve under $50
3. Use **Quick Send** buttons to fire test requests instantly
4. Watch the budget bar update in real time
5. Expand results to see detailed policy check results (pass/fail for each rule)

## Features

### Isolated from Production

Sandbox agents are completely separated from your real agents:

- Sandbox agents only appear on the Sandbox page
- Production agents only appear on the Home page
- Each has independent budgets, policies, and request history
- Agent names must be unique within sandbox and production separately

### Full Agent Management

Sandbox agents have the same capabilities as production agents:

- **Budget bar** — see available, spent, and held amounts
- **Policy configuration** — set up rules via AI chat (Edit Policy)
- **Pause / Resume / Archive** — control agent status
- **Rename** — click the pencil icon on the agent card
- **Auto top-up** — configure automatic budget replenishment
- **Request list** — approve or reject pending requests

### Test Requests

**Quick Send** — pre-configured sample requests across categories (food delivery, taxi, subscriptions, groceries, restaurants, electronics, entertainment, education). Click any button to send instantly.

**Send 5 Random** — burst mode, sends 5 random requests with 0.5s intervals.

**Custom Request** — specify amount, category, merchant, and description manually.

### Sandbox Results

Each request shows:
- Status badge (auto-approved / pending / rejected)
- Click to expand detailed policy checks (which rules passed/failed)
- Remaining budget after the request

### Policy Testing

1. Click **Edit Policy** next to the policy preview
2. Describe rules in natural language (e.g., "only allow groceries under $20")
3. Confirm the policy
4. Send test requests to verify the policy works as expected
5. Iterate — change the policy and test again

## Multiple Sandbox Agents

Create multiple sandbox agents with different policies to compare behavior:

- "Sandbox Agent 1" — strict policy, low limits
- "Sandbox Agent 2" — permissive, high auto-approve threshold
- Switch between them using the agent tabs

## Cleanup

- **Archive** — hides the agent, stops accepting requests. Restore from Settings → Archived Agents.
- Sandbox agents don't count toward any production metrics.
