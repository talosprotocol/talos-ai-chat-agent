# Agent workspace: services/ai-chat-agent
> **Project**: services/ai-chat-agent

This folder contains agent-facing context, tasks, workflows, and planning artifacts for this submodule.

## Current State
Agent-facing chat service or wrapper. Uses streaming semantics and must respect meta-first and terminal done or error rules.

## Expected State
Stable streaming behavior, safe request limits, and strict allowlists. Clean integration with gateway and audit pipelines.

## Behavior
Provides chat agent capabilities, message routing, conversation management, and streaming responses for UI and API consumers.

## How to work here
- Run/tests:
- Local dev:
- CI notes:

## Interfaces and dependencies
- Owned APIs/contracts:
- Depends on:
- Data stores/events (if any):

## Global context
See `.agent/context.md` for monorepo-wide invariants and architecture.
