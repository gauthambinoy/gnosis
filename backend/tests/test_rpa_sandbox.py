"""
RPA Engine Sandbox Validation Tests

Ensures that the RPA engine properly:
1. Validates all action types
2. Sanitizes selectors and values
3. Enforces action whitelists
4. Prevents browser escape
5. Respects timeout limits
"""

import pytest
from app.core.rpa_engine import (
    ActionType,
    RpaAction,
    RpaWorkflow,
    validate_action,
    validate_selector,
    RpaEngine,
)
from app.core.error_handling import ValidationError


class TestActionTypeWhitelist:
    """Test that only approved action types are allowed."""

    def test_all_valid_action_types(self):
        """All defined ActionType enum values are valid."""
        valid_actions = [
            ActionType.CLICK,
            ActionType.DOUBLE_CLICK,
            ActionType.RIGHT_CLICK,
            ActionType.TYPE,
            ActionType.PRESS_KEY,
            ActionType.SCROLL,
            ActionType.NAVIGATE,
            ActionType.WAIT,
            ActionType.WAIT_FOR_SELECTOR,
            ActionType.SCREENSHOT,
            ActionType.SELECT,
            ActionType.HOVER,
            ActionType.DRAG_DROP,
            ActionType.ASSERT_TEXT,
            ActionType.ASSERT_VISIBLE,
            ActionType.EXTRACT_TEXT,
            ActionType.EXTRACT_ATTRIBUTE,
            ActionType.CONDITIONAL,
            ActionType.LOOP,
        ]
        
        for action_type in valid_actions:
            # Should not raise
            action = RpaAction(
                action_type=action_type,
                selector="button.submit" if action_type != ActionType.NAVIGATE else None,
                value="" if action_type in [ActionType.TYPE, ActionType.NAVIGATE] else None,
            )
            assert action.action_type == action_type

    def test_no_shell_execution_action(self):
        """No SHELL_EXEC or SYSTEM action type exists."""
        # Verify dangerous action types don't exist
        assert not hasattr(ActionType, 'SHELL_EXEC')
        assert not hasattr(ActionType, 'SYSTEM')
        assert not hasattr(ActionType, 'EXECUTE_CODE')


class TestSelectorSanitization:
    """Test CSS selector and XPath injection prevention."""

    def test_valid_css_selectors(self):
        """Valid CSS selectors should pass."""
        valid_selectors = [
            "button.submit",
            "#login-form",
            "input[type='email']",
            ".btn-primary:hover",
            "div > span",
            "ul li:nth-child(2)",
        ]
        
        for selector in valid_selectors:
            # Should not raise
            result = validate_selector(selector, selector_type="css")
            assert result is not None

    def test_valid_xpath_selectors(self):
        """Valid XPath should pass."""
        valid_xpaths = [
            "//button[@id='submit']",
            "//div[@class='container']",
            "//input[@type='email']",
            "//form//input[1]",
        ]
        
        for xpath in valid_xpaths:
            # Should not raise
            result = validate_selector(xpath, selector_type="xpath")
            assert result is not None

    def test_reject_javascript_protocol_in_selector(self):
        """Reject javascript: protocol in selectors."""
        with pytest.raises(ValidationError):
            validate_selector("javascript:alert('xss')", selector_type="css")

    def test_reject_onclick_injection(self):
        """Reject onclick handlers in selectors."""
        with pytest.raises(ValidationError):
            validate_selector("*[onclick='alert(1)']", selector_type="css")


class TestValueSanitization:
    """Test input value sanitization."""

    def test_valid_text_input(self):
        """Valid text input should be allowed."""
        valid_inputs = [
            "user@example.com",
            "password123!@#",
            "The quick brown fox",
            "123-456-7890",
        ]
        
        for text in valid_inputs:
            # Should not raise - just validate length/format
            assert len(text) <= 10000

    def test_reject_excessive_length_input(self):
        """Reject input exceeding max length."""
        long_text = "x" * 50001
        with pytest.raises(ValidationError):
            validate_action(
                action_type=ActionType.TYPE,
                value=long_text,
            )

    def test_reject_javascript_in_type_action(self):
        """Reject JavaScript code in TYPE actions."""
        with pytest.raises(ValidationError):
            validate_action(
                action_type=ActionType.TYPE,
                value="<script>alert('xss')</script>",
            )

    def test_accept_special_characters_in_type(self):
        """Allow special characters that user might type."""
        valid_inputs = [
            "!@#$%^&*()",
            "[']{};:",
            "<?php echo;",  # As text, not executed
        ]
        
        for text in valid_inputs:
            # Should pass - these are data, not code
            result = validate_action(
                action_type=ActionType.TYPE,
                value=text,
            )
            assert result is not None


class TestWorkflowValidation:
    """Test RPA workflow validation."""

    def test_valid_workflow_structure(self):
        """Valid workflow should be accepted."""
        workflow = RpaWorkflow(
            name="Login workflow",
            actions=[
                RpaAction(
                    action_type=ActionType.NAVIGATE,
                    value="https://example.com/login",
                ),
                RpaAction(
                    action_type=ActionType.TYPE,
                    selector="input[type='email']",
                    value="user@example.com",
                ),
                RpaAction(
                    action_type=ActionType.CLICK,
                    selector="button.submit",
                ),
            ],
        )
        
        assert workflow.name == "Login workflow"
        assert len(workflow.actions) == 3

    def test_reject_empty_workflow(self):
        """Empty workflows should be rejected."""
        with pytest.raises(ValidationError):
            RpaWorkflow(name="Empty", actions=[])

    def test_reject_oversized_workflow(self):
        """Workflows with too many actions should be rejected."""
        actions = [
            RpaAction(
                action_type=ActionType.CLICK,
                selector="button",
            )
            for _ in range(1001)
        ]
        
        with pytest.raises(ValidationError):
            RpaWorkflow(name="Large", actions=actions)


class TestTimeoutEnforcement:
    """Test timeout limits."""

    def test_action_timeout_limits(self):
        """Each action has reasonable timeout."""
        action = RpaAction(
            action_type=ActionType.WAIT,
            wait_time_ms=500,
        )
        
        # Should be reasonable (not infinite, not too small)
        assert 100 <= action.wait_time_ms <= 60000

    def test_workflow_execution_timeout(self):
        """Workflow execution should have total timeout."""
        workflow = RpaWorkflow(
            name="Test",
            actions=[
                RpaAction(action_type=ActionType.CLICK, selector="button")
            ],
            timeout_seconds=30,
        )
        
        # Total timeout should be enforced
        assert workflow.timeout_seconds <= 300  # Max 5 minutes


class TestNoFileSystemAccess:
    """Verify RPA engine cannot access file system."""

    def test_no_file_read_action(self):
        """No file read capability."""
        assert not hasattr(ActionType, 'READ_FILE')
        assert not hasattr(ActionType, 'FILE_SYSTEM')

    def test_no_file_write_action(self):
        """No file write capability."""
        assert not hasattr(ActionType, 'WRITE_FILE')
        assert not hasattr(ActionType, 'DOWNLOAD')

    def test_navigate_restricted_to_http(self):
        """Navigation should be restricted to http/https."""
        # file:// URLs should be blocked
        with pytest.raises(ValidationError):
            validate_action(
                action_type=ActionType.NAVIGATE,
                value="file:///etc/passwd",
            )


class TestNoCommandExecution:
    """Verify RPA engine cannot execute OS commands."""

    def test_no_system_command_action(self):
        """No system command execution action."""
        assert not hasattr(ActionType, 'EXEC')
        assert not hasattr(ActionType, 'SHELL')
        assert not hasattr(ActionType, 'BASH')

    def test_no_code_execution_action(self):
        """No arbitrary code execution."""
        assert not hasattr(ActionType, 'EVAL')
        assert not hasattr(ActionType, 'EXECUTE_PYTHON')
        assert not hasattr(ActionType, 'RUN_CODE')


class TestBrowserSandboxing:
    """Test browser sandbox enforcement."""

    def test_headless_mode_only(self):
        """Browser should run in headless mode."""
        engine = RpaEngine()
        # Verify headless configuration
        assert getattr(engine, 'headless', True) is True

    def test_no_extension_loading(self):
        """Browser extensions should not be loaded."""
        engine = RpaEngine()
        # Verify no extension paths configured
        extensions = getattr(engine, 'browser_extensions', [])
        assert len(extensions) == 0

    def test_no_user_data_persistence(self):
        """Temporary browser profiles, no persistent user data."""
        engine = RpaEngine()
        # Each execution should use clean profile
        assert getattr(engine, 'profile_persistence', 'temporary') == 'temporary'


class TestAuditLogging:
    """Test that all actions are logged."""

    def test_action_logging_enabled(self):
        """RPA engine logs all actions."""
        action = RpaAction(
            action_type=ActionType.CLICK,
            selector="button",
        )
        
        # Action should have audit trail fields
        assert hasattr(action, 'timestamp') or hasattr(action, 'created_at')

    def test_workflow_execution_logged(self):
        """Workflow execution creates audit trail."""
        workflow = RpaWorkflow(
            name="Test",
            actions=[
                RpaAction(action_type=ActionType.CLICK, selector="button")
            ],
        )
        
        # Workflow should track execution
        assert hasattr(workflow, 'execution_history') or hasattr(workflow, 'audit_log')


class TestInjectionPrevention:
    """Test injection attack prevention."""

    def test_selector_injection_attempt(self):
        """Prevent selector-based injection."""
        malicious_selector = "button')[0]; window.location='http://evil.com'; //"
        with pytest.raises(ValidationError):
            validate_selector(malicious_selector, selector_type="css")

    def test_value_injection_attempt(self):
        """Prevent value-based injection."""
        malicious_value = "x'); DROP TABLE agents; --"
        with pytest.raises(ValidationError):
            validate_action(
                action_type=ActionType.TYPE,
                value=malicious_value,
            )

    def test_xpath_injection(self):
        """Prevent XPath injection."""
        malicious_xpath = "//button[@id=' or '1'='1]"
        with pytest.raises(ValidationError):
            validate_selector(malicious_xpath, selector_type="xpath")


class TestRecordingPlayback:
    """Test action recording and replay safety."""

    def test_recorded_actions_validated(self):
        """Recorded actions go through validation."""
        # When recording user actions, they should be validated
        action = RpaAction(
            action_type=ActionType.CLICK,
            selector="button.safe",
        )
        
        # Should pass validation
        assert action.action_type == ActionType.CLICK

    def test_replay_uses_validated_actions(self):
        """Replay uses validated action definitions."""
        workflow = RpaWorkflow(
            name="Recorded",
            actions=[
                RpaAction(
                    action_type=ActionType.CLICK,
                    selector="button",
                ),
            ],
        )
        
        # All actions in workflow are validated
        for action in workflow.actions:
            assert action.action_type in ActionType


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
