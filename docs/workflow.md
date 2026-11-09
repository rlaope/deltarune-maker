# Working in the studio

Start with [AGENTS.md](../AGENTS.md), the shared creative and asset policy, and the [showcase catalog](../examples/catalog.json). The published examples document finished videos; their pages identify the available artifacts. The studio image is a visual concept.

## Use your preferred agent

Open the repository as the agent's working directory. No project-specific plugin or private skill installation is required to read these instructions.

| Agent | How project instructions load |
| --- | --- |
| Codex | Reads root `AGENTS.md` through its project instruction discovery. [Official documentation](https://developers.openai.com/codex/guides/agents-md). |
| Claude Code | Root `CLAUDE.md` imports `AGENTS.md` using `@AGENTS.md`. [Official documentation](https://code.claude.com/docs/en/memory#share-one-file-with-other-coding-tools). |
| Hermes Agent | Reads root `AGENTS.md` as project context. A local `.hermes.md`, `HERMES.md`, or `AGENTS.override.md` can take priority; check local overrides if instructions appear missing. [Official documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files). |
| Other tools | Explicitly attach or ask the agent to read `AGENTS.md` and this workflow before starting. |

A portable starting prompt:

> Read AGENTS.md and docs/workflow.md. Review the existing examples. Propose a DELTARUNE crossover with an English posting title, a clear setup, escalation, and payoff, and a source plan for the original assets from both games. Identify the production tools needed before implementing it.

Instruction loading is configuration-dependent. Confirm the agent has read the shared policy in your session. This repository does not prescribe an agent CLI, game engine, or rendering command; document the real commands and dependencies when adding a reproducible production project.

## From premise to finished scene

1. **Write the beat sheet.** Name the title, premise, cast, recognizable player interaction, escalation, and ending. Choose the duration from the story and allow time for dialogue, reactions, and suspense.
2. **Prepare the source inventory.** Apply the asset policy in `AGENTS.md` to both sides of the crossover. Record source identifiers and credits before editing. Preserve original files, then work from copies.
3. **Build a readable first pass.** Establish the scene and interaction before speeding up. Give movement room, maintain camera continuity, and check collision behavior wherever the scene represents gameplay.
4. **Review picture and sound together.** Play the entire sequence. Check character voices, sound timing, dialogue readability, camera transitions, pacing, and the payoff. Preview the social crop with platform overlays in mind.
5. **Approve and measure the final export.** Record its filename, SHA-256, dimensions, frame rate, duration, byte size, and audio stream details. Play the actual export through the ending with sound. Keep verification outputs with the production records. Produce shorts and regular gameplay editions when the delivery calls for both, preserving each independently. When a project specifies a single master, preserve and deliver that one approved export.

## Publish an example

Create `examples/<slug>/README.md` with its English title, premise, short scene description, source credits, and links to the finished videos. Use a frame from the approved video for the poster and record the source video and frame time in production records. Keep exact export metadata in [catalog.json](../examples/catalog.json), following its existing structure.

Upload approved MP4 files to the project's GitHub Releases and link those assets from the example page and catalog. Copy the approved files without transcoding. Download the uploaded assets and compare their SHA-256 values with the approved exports; matching hashes establish that publication preserved the bytes. Verify the published links and open each downloaded file for playback.

Commit documentation, catalog updates, and posters. Keep large production caches and original game asset bundles out of the showcase commit. A concept, a finished video, and reproducible production source are distinct artifacts; describe only what is actually included. If source is added later, record its tool versions, source inventory, actual regeneration command, and export verification procedure alongside it.

For an update to an existing work, point the showcase to the latest approved version after its upload, download, hash comparison, and playback succeed. Preserve the source needed to reproduce that version before cleaning up superseded delivery files. Leave other works untouched.
