from pathlib import Path
from loader import parse_python
from analyzers.security_analyzer import security_analyzer
from llm.explain import build_prompt, parse_reply, EXPLANATION_SCHEMA
from llm.gemini import ask_llm
info = parse_python(Path(r"C:\Users\admin\AppData\Local\Temp\claude\6539791d589f1e68\51b166c7-65fc-4081-a563-bb23d0331792\scratchpad\sec\insecure.py"))

for f in security_analyzer(info)[:1]:
    print("""ANSWER""")
    prompt = build_prompt(f, info)
    print(prompt)
    text = ask_llm(prompt, schema=EXPLANATION_SCHEMA)
    print(text)
    result =  parse_reply(text)
    print(result)
    print("""LAZY ANSWER""")
    prompt_lazy = f"An issue is found the info related to which is : {f.message}, suggest fixes"
    response_lazy =ask_llm(prompt_lazy)
    print(response_lazy)
