# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| Latest release | :white_check_mark: |
| Older releases | :x: |

Only the most recent version of LyricsMaker receives security fixes. Please update to the latest release before reporting an issue.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

To report a vulnerability, email: **securityreport@erikvankruiselbergen.nl**

Include in your report:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept or exploit code if available)
- The version of LyricsMaker or the commit hash you tested against
- Any suggested mitigations, if you have them

You will receive an acknowledgement within **48 hours**. After triage, you will be kept informed of progress toward a fix and public disclosure.

## Disclosure Policy

Once a fix is available:

1. A patched release will be published.
2. A GitHub Security Advisory will be opened to publicly document the issue and credit the reporter (unless you prefer to remain anonymous).

We ask that you give us a reasonable window (typically **90 days**) to resolve the issue before public disclosure.

## Scope

LyricsMaker is a local desktop application that reads audio and plain-text files from your machine and writes `.lrc` files. It makes no network requests and stores no credentials or personal data.

Relevant security concerns include, but are not limited to:

- **Malicious audio or lyrics files** that trigger unsafe behavior (path traversal, arbitrary code execution, etc.)
- **Packaging or supply-chain issues** in the distributed `LyricsMaker.exe`
- **Dependency vulnerabilities** in `pygame-ce` or `mutagen` as they affect this project

Out of scope: general vulnerabilities in third-party libraries unrelated to how LyricsMaker uses them.

## Credits

We appreciate responsible disclosure and will credit reporters in the associated Security Advisory unless anonymity is requested.
