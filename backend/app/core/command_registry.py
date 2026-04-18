"""Backend registry for keyboard commands."""

import logging
from dataclasses import dataclass, asdict
from typing import List

logger = logging.getLogger("gnosis.commands")


@dataclass
class Command:
    id: str
    label: str
    description: str = ""
    shortcut: str = ""
    category: str = "general"
    requires_auth: bool = True


BUILTIN_COMMANDS = [
    Command(
        "cmd-palette",
        "Open Command Palette",
        "Quick access to all commands",
        "Ctrl+K",
        "navigation",
    ),
    Command("nav-home", "Go to Dashboard", "Navigate to home", "G D", "navigation"),
    Command("nav-agents", "Go to Agents", "View all agents", "G A", "navigation"),
    Command("nav-pipelines", "Go to Pipelines", "View pipelines", "G P", "navigation"),
    Command(
        "nav-knowledge", "Go to Knowledge Base", "Access knowledge", "G K", "navigation"
    ),
    Command("nav-settings", "Go to Settings", "Platform settings", "G S", "navigation"),
    Command("new-agent", "Create New Agent", "Start agent creation", "N", "actions"),
    Command(
        "new-pipeline", "Create New Pipeline", "Build a workflow", "Shift+N", "actions"
    ),
    Command("search", "Global Search", "Search everything", "Ctrl+/", "search"),
    Command("refresh", "Refresh Data", "Reload current view", "R", "actions"),
    Command("toggle-theme", "Toggle Theme", "Switch dark/light", "T", "appearance"),
    Command("help", "Open Help", "Get contextual help", "?", "help"),
    Command(
        "shortcuts", "Show All Shortcuts", "List keyboard shortcuts", "Shift+?", "help"
    ),
    Command("escape", "Close/Cancel", "Close dialog or cancel", "Escape", "navigation"),
    Command("zoom-in", "Zoom In", "Increase font size", "Ctrl+=", "appearance"),
    Command("zoom-out", "Zoom Out", "Decrease font size", "Ctrl+-", "appearance"),
    Command(
        "fullscreen", "Toggle Fullscreen", "Enter/exit fullscreen", "F11", "appearance"
    ),
    Command(
        "copy-id",
        "Copy Current ID",
        "Copy item ID to clipboard",
        "Ctrl+Shift+C",
        "actions",
    ),
    Command("export", "Export Data", "Export current view", "Ctrl+E", "actions"),
    Command(
        "notifications",
        "Toggle Notifications",
        "Show/hide notifications",
        "Ctrl+Shift+N",
        "actions",
    ),
]


class CommandRegistry:
    def __init__(self):
        self._commands = {c.id: c for c in BUILTIN_COMMANDS}

    def list_commands(self, category: str = None) -> List[dict]:
        cmds = list(self._commands.values())
        if category:
            cmds = [c for c in cmds if c.category == category]
        return [asdict(c) for c in cmds]

    def search_commands(self, query: str) -> List[dict]:
        q = query.lower()
        return [
            asdict(c)
            for c in self._commands.values()
            if q in c.label.lower() or q in c.description.lower()
        ]


command_registry = CommandRegistry()
