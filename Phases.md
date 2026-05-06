# Phase 1: The Brain (LangGraph Logic)
Goal: Create the internal "decision-making" loop for a single pod.

Define the State: Setup the LangGraph State to track the current task, code snippets, and QA results.

Build the Nodes:

Architect: Analyzes the task and identifies which files to touch.

Builder: Generates the code.

QA: Runs a "simulated" test or linting check.

Control Flow: Ensure the graph can loop back from QA to Builder if errors are found.

# Phase 2: The Hands & Nerves (MCP & AG-UI)
Goal: Give the Brain the ability to act on the physical world and talk to the UI.

MCP Setup: Implement a local Model Context Protocol server that grants the agents read_file, write_file, and execute_command.

AG-UI Transport: Configure the CopilotKit Runtime on the backend to stream the LangGraph "steps" (e.g., "Architect is planning...") so the user sees the agent's progress in real-time.

# Phase 3: The Global Memory (ChromaDB Layer)
Goal: Allow agents to "remember" the project context and other devs' work.

Indexing Service: Create a script that "walks" the project folder, generates summaries of each file/component, and stores them in ChromaDB.

Context Retrieval Node: Add a "Pre-flight" node to the LangGraph that queries ChromaDB for relevant components/constants before the Builder starts coding.

The Semantic Update: Set up a "Post-merge" trigger that updates the database whenever new code is added to the project.

# Phase 4: The Body (React & CopilotKit UI)
Goal: Build the dashboard where the human orchestrates the "Power-Pod."

The Workspace: A React frontend using CopilotKit’s <CopilotSidebar/> or a custom chat interface.

A2UI Rendering: Implement the A2UI renderer to catch JSON payloads from the agents (e.g., a "Progress Card" or a "Component Preview").

Task Assignment: A simple UI for the human to say "Build the Login Form" and trigger the specific LangGraph branch.

# Phase 5: The Traffic Light (Git & Multi-User Sync)
Goal: Enable collaborative development without merge conflicts.

Git-Agent Integration: Give the Builder agent the ability to create feature branches (git checkout -b task-name).

Conflict Detection: Create a logic gate that checks if the files the agent wants to edit are currently being worked on by another "Pod" (via a shared status file or Git check).

The Gatekeeper: Final "Human-in-the-loop" UI where the developer reviews the agent's PR before it merges into the main branch.