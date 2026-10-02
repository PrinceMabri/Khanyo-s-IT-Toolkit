from khanyo_toolkit.registry import CATEGORIES, REPORT_TOOLS, Tool

ALL_TOOLS = [t for tools in CATEGORIES.values() for t in tools]


def test_expected_categories_exist():
    assert list(CATEGORIES) == ["Dashboard", "System", "Network", "Maintenance"]


def test_labels_are_unique():
    labels = [t.label for t in ALL_TOOLS]
    assert len(labels) == len(set(labels))


def test_every_tool_is_well_formed():
    for tool in ALL_TOOLS:
        assert isinstance(tool, Tool)
        assert callable(tool.func)
        assert tool.tooltip.strip(), tool.label


def test_report_tools_exclude_state_changing_tools():
    assert REPORT_TOOLS
    assert all(not t.dangerous for t in REPORT_TOOLS)


def test_known_state_changing_tools_are_flagged():
    dangerous = {t.label for t in ALL_TOOLS if t.dangerous}
    assert {
        "Clear DNS Cache", "Reset Network Adapter", "Restart Print Spooler",
        "Clean Temp Files", "Empty Recycle Bin", "Create Restore Point", "Quick Health Scan",
    } <= dangerous
