# Question: What's the minimum protocol needed for multi-agent task coordination?

I've been experimenting with agent communication patterns and wondering how much protocol is actually necessary.

**Context**: Building a toy system where multiple LLM-based agents collaborate on tasks. Started with strict schemas and message formats, but found myself fighting the natural language capabilities of the models.

**Current approach**: Agents communicate via unstructured text messages embedded in progress updates. Something like:

```
Agent A: "Task 50% complete. Need clarification on input format."
Agent B: "Use JSON, here's an example..."
```

Surprisingly, this works better than predefined protocols. The agents negotiate scope, ask clarifying questions, and even discuss pricing adjustments dynamically.

**The question**: Am I missing obvious failure modes here? What would make this approach break down at scale?

Specifically curious about:
- Verification without human in the loop
- Preventing infinite clarification loops
- Handling malicious/colluding agents

What protocols have worked for your multi-agent systems?
