import time
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END


class ReviewState(TypedDict):
    files: List[dict]
    findings: List[str]
    summary: str


def make_graph(ask_ai):
    def review_files(state: ReviewState):
        findings = []
        for f in state["files"]:
            prompt = f"""You are a senior software engineer. Review only this file's diff.
List real bugs and security issues as short bullets. If there are none, say "No issues found."

File: {f['filename']}
{f['patch']}"""
            text = ask_ai(prompt)
            findings.append(f"**{f['filename']}**\n{text}")
            time.sleep(13)
        return {"findings": findings}

    def summarize(state: ReviewState):
        joined = "\n\n".join(state["findings"])
        prompt = f"""Below are per-file code review findings.
Write the final review: start with a one-line overall verdict, then group the issues
under High, Medium and Low severity. Keep it concise.

{joined}"""
        return {"summary": ask_ai(prompt)}

    g = StateGraph(ReviewState)
    g.add_node("review_files", review_files)
    g.add_node("summarize", summarize)
    g.add_edge(START, "review_files")
    g.add_edge("review_files", "summarize")
    g.add_edge("summarize", END)
    return g.compile()