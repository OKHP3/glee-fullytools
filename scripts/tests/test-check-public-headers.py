#!/usr/bin/env python3
"""Offline regression tests for the public security-header checker."""
from __future__ import annotations

from contextlib import redirect_stdout
import importlib.util
from io import StringIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


_SCRIPT = Path(__file__).resolve().parent.parent / "check-public-headers.py"
_SPEC = importlib.util.spec_from_file_location("_check_public_headers", _SCRIPT)
assert _SPEC.loader is not None
mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mod)


STABLE_DIRECTIVES = {
    "script-src",
    "script-src-attr",
    "frame-src",
    "object-src",
    "base-uri",
    "form-action",
    "manifest-src",
    "upgrade-insecure-requests",
}

VALID_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self' https://www.googletagmanager.com 'sha256-test='",
        "script-src-attr 'none'",
        "frame-src 'self' https://okhp3.github.io",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "manifest-src 'self'",
        "upgrade-insecure-requests",
    )
)


def _policy_without(directive_to_remove: str) -> str:
    """Return the complete fixture policy with exactly one directive removed."""
    return "; ".join(
        directive
        for directive in VALID_POLICY.split("; ")
        if directive.split()[0] != directive_to_remove
    )


class PublicHeaderCspTests(unittest.TestCase):
    def run_checker(self, policy: str) -> tuple[int, str]:
        """Run the command entry point against mocked headers, never the network."""
        headers = {
            "strict-transport-security": "max-age=31536000",
            "content-security-policy": policy,
            "x-frame-options": "SAMEORIGIN",
            "x-content-type-options": "nosniff",
        }
        output = StringIO()
        with (
            patch.object(mod, "fetch_headers", return_value=headers),
            patch.object(
                sys,
                "argv",
                ["check-public-headers.py", "--url", "https://example.test/"],
            ),
            redirect_stdout(output),
        ):
            result = mod.main()
        return result, output.getvalue()

    def test_valid_policy_passes_every_stable_control(self) -> None:
        self.assertEqual(set(mod.REQUIRED_CSP_TOKENS), STABLE_DIRECTIVES)

        checks = mod.csp_checks(VALID_POLICY)
        self.assertEqual(
            {directive for directive, _, _ in checks},
            STABLE_DIRECTIVES,
        )
        self.assertTrue(
            all(passed for _, passed, _ in checks),
            msg=f"valid fixture failed CSP checks: {checks}",
        )

        result, output = self.run_checker(VALID_POLICY)
        self.assertEqual(result, 0, msg=output)
        self.assertNotIn("FAIL ", output)

    def test_script_src_rejects_unsafe_inline_and_names_the_directive(self) -> None:
        weakened_policy = VALID_POLICY.replace(
            "script-src 'self'",
            "script-src 'self' 'unsafe-inline'",
            1,
        )

        check = {
            directive: (passed, detail)
            for directive, passed, detail in mod.csp_checks(weakened_policy)
        }["script-src"]
        self.assertEqual(
            check,
            (False, "must not contain 'unsafe-inline'"),
            msg="script-src must be reported as weakened when it allows unsafe-inline",
        )

        result, output = self.run_checker(weakened_policy)
        self.assertEqual(result, 1, msg="unsafe-inline policy unexpectedly passed")
        self.assertIn(
            "FAIL script-src: must not contain 'unsafe-inline'",
            output,
            msg="failure output must identify the weakened script-src directive",
        )

    def test_missing_each_stable_control_fails_and_names_the_directive(self) -> None:
        for directive in sorted(STABLE_DIRECTIVES):
            with self.subTest(directive=directive):
                weakened_policy = _policy_without(directive)
                checks = {
                    name: (passed, detail)
                    for name, passed, detail in mod.csp_checks(weakened_policy)
                }

                self.assertEqual(
                    checks[directive],
                    (False, "directive missing"),
                    msg=f"missing {directive} must be reported as a weakened control",
                )
                self.assertEqual(
                    [name for name, (passed, _) in checks.items() if not passed],
                    [directive],
                    msg=f"only the removed {directive} control should fail",
                )

                result, output = self.run_checker(weakened_policy)
                self.assertEqual(
                    result,
                    1,
                    msg=f"checker unexpectedly passed without {directive}",
                )
                self.assertIn(
                    f"FAIL {directive}: directive missing",
                    output,
                    msg=f"failure output must identify the missing {directive} directive",
                )


if __name__ == "__main__":
    unittest.main()