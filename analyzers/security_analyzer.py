"""Flag risky code: dangerous calls, shell injection, unsafe loading, hard-coded secrets.

Works on CallSite and Assignment facts from the loader, never on raw source text.
That's why `x = "eval(...)"` in a string or a comment is NOT flagged, and
`import subprocess as sp; sp.run(cmd, shell=True)` IS.
"""
import re

from models import CallSite, FileInfo, Finding

# Calls that are risky whatever their arguments are.
# full call name -> (rule id, severity, why it's risky)
DANGEROUS_CALLS = {
    "eval":          ("dangerous-eval", "high", "runs any Python code it is given"),
    "exec":          ("dangerous-eval", "high", "runs any Python code it is given"),
    "os.system":     ("shell-injection", "high", "runs a shell command; untrusted input can inject commands"),
    "os.popen":      ("shell-injection", "high", "runs a shell command; untrusted input can inject commands"),
    "pickle.load":   ("unsafe-deserialization", "high", "loading untrusted pickle data can run arbitrary code"),
    "pickle.loads":  ("unsafe-deserialization", "high", "loading untrusted pickle data can run arbitrary code"),
    "marshal.loads": ("unsafe-deserialization", "high", "loading untrusted marshal data is unsafe"),
    "hashlib.md5":   ("weak-hash", "low", "MD5 is broken; don't use it for passwords or signatures"),
    "hashlib.sha1":  ("weak-hash", "low", "SHA-1 is broken; don't use it for passwords or signatures"),
}

# subprocess functions: only risky with shell=True.
SUBPROCESS_CALLS = {
    "subprocess.run", "subprocess.call", "subprocess.Popen",
    "subprocess.check_call", "subprocess.check_output",
}

# Names that suggest a secret. This regex looks at variable NAMES, not code,
# so it's fine here. Matches "password", "DB_PASSWORD", "api_key", "apiKey", ...
SECRET_NAME = re.compile(r"pass(word|wd)?|secret|token|api_?key|private_?key", re.IGNORECASE)


def _where(scope: str) -> str:
    """Readable location for messages: " in 'Dog.bark'" or "" at module level."""
    return f" in '{scope}'" if scope else ""


def _check_risky_call(call: CallSite) -> tuple[str, str, str] | None:
    """Return (rule, severity, message) if this call is risky, else None."""
    # 1. Always-dangerous calls.
    if call.name in DANGEROUS_CALLS:
        rule, severity, why = DANGEROUS_CALLS[call.name]
        return rule, severity, f"{call.name}() {why}"

    # 2. subprocess with shell=True: the command goes through a shell.
    if call.name in SUBPROCESS_CALLS and call.keywords.get("shell") is True:
        return ("shell-injection", "high",
                f"{call.name}(shell=True) lets untrusted input inject commands")

    # 3. yaml.load without a Loader can build arbitrary Python objects.
    #    The Loader can be passed as a keyword or as the 2nd positional argument.
    if call.name == "yaml.load" and "Loader" not in call.keywords and call.arg_count < 2:
        return ("unsafe-deserialization", "medium",
                "yaml.load() without a Loader is unsafe; use yaml.safe_load()")

    # 4. requests with verify=False turns off HTTPS certificate checks.
    if call.name.startswith("requests.") and call.keywords.get("verify") is False:
        return ("tls-verify-disabled", "medium",
                f"{call.name}(verify=False) disables HTTPS certificate checks")

    return None


def _secret_keywords(call: CallSite) -> list[str]:
    """Keyword names that receive a hard-coded secret: connect(password="hunter2")."""
    return [key for key, value in call.keywords.items()
            if SECRET_NAME.search(key) and isinstance(value, str) and value]


def _check_calls(info: FileInfo) -> list[Finding]:
    """Rules that look at function calls."""
    findings = []
    for call in info.calls:
        where = _where(call.scope)

        risky = _check_risky_call(call)
        if risky:
            rule, severity, message = risky
            findings.append(Finding(rule, severity, info.path, call.line, message + where))

        for key in _secret_keywords(call):
            findings.append(Finding("hardcoded-secret", "high", info.path, call.line,
                                    f"Hard-coded secret passed as '{key}=' to {call.name}(){where}"))
    return findings


def _check_assignments(info: FileInfo) -> list[Finding]:
    """Rule: a secret-looking name assigned a string literal, e.g. API_KEY = "abc123"."""
    findings = []
    for a in info.assignments:
        short = a.target.split(".")[-1]   # "self.password" -> "password"
        if SECRET_NAME.search(short) and a.value:   # empty string = placeholder, skip
            findings.append(Finding("hardcoded-secret", "high", info.path, a.line,
                                    f"Hard-coded secret assigned to '{a.target}'{_where(a.scope)}"))
    return findings


def security_analyzer(info: FileInfo) -> list[Finding]:
    """Run every security rule on one file and return the findings, sorted by line."""
    findings = _check_calls(info) + _check_assignments(info)
    return sorted(findings, key=lambda f: f.line)


if __name__ == "__main__":
    import sys
    from loader import find_files, parse_python

    for f in find_files(sys.argv[1]):
        for finding in security_analyzer(parse_python(f)):
            print(f"[{finding.severity}] {finding.file}:{finding.line}  {finding.message}")
