from pathlib import Path
from loader import parse_python
from analyzers.security_analyzer import security_analyzer
from llm.explain import snippet_for

info = parse_python(Path(r"C:\Users\admin\AppData\Local\Temp\claude\6539791d589f1e68\51b166c7-65fc-4081-a563-bb23d0331792\scratchpad\sec\insecure.py"))
for f in security_analyzer(info)[:3]:
    print(f.line, f.message)
    print(snippet_for(f, info))
    print("-" * 40)
