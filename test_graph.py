from app import ask_gemini
from review_graph import make_graph

files = [
    {"filename": "a.py", "patch": "+def avg(n):\n+    return sum(n) / len(n)"},
    {"filename": "b.py", "patch": "+def last(l):\n+    return l[len(l)]"},
]

result = make_graph(ask_gemini).invoke({"files": files, "findings": [], "summary": ""})
print(result["summary"])
