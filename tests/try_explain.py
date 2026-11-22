from pathlib import Path
from loader import parse_python
from analyzers.security_analyzer import security_analyzer
from llm.explain import explain_findings
from llm.gemini import LLMBusyError, LLMConfigError

info = parse_python(Path(r"C:\Users\admin\AppData\Local\Temp\claude\6539791d589f1e68\51b166c7-65fc-4081-a563-bb23d0331792\scratchpad\sec\insecure.py"))
findings = security_analyzer(info)


def happy(prompt, schema=None):
    assert schema is not None, "explain_findings forgot to send the schema"
    return '{"explanation": "it is bad", "fix": "x = 1"}'


def busy(prompt, schema=None):
    raise LLMBusyError("Gemini is busy (503)")

def no_key(prompt, schema=None):
    raise LLMConfigError("No Gemini API key")

for fake in [happy, busy, no_key]:          # functions in a list, like ANALYZERS
    print(f"=== {fake.__name__}")           # every function knows its own name
    try:
        results = explain_findings(findings, [info], fake)
    except LLMConfigError as e:
        print("stopped:", e)
        continue                            # skip the printing below, go to the next fake
    for r in results:
        print(r.finding.rule, r.finding.line, "→", r.explanation or r.error)

