from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from github import Github, Auth
from dotenv import load_dotenv
from db import SessionLocal, Review
import os
import json
import hmac
import hashlib
import google.generativeai as genai
import time

load_dotenv()

app = FastAPI()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

auth = Auth.Token(GITHUB_TOKEN)
gh = Github(auth=auth)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-3.8-flash")


def verify_signature(body: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def get_ai_review(diff_text: str) -> str:
    prompt = f"""You are a senior software engineer doing a code review.
Review the following code diff. Point out bugs, potential issues, and suggestions for improvement.
Keep it concise and use bullet points.

DIFF:
{diff_text}
"""
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Gemini error (try {attempt + 1}/3): {e}")
            if attempt < 2:
                time.sleep(40)
    return "The review could not be generated right now because the AI service is rate limited. Please open a new PR in a minute."


def process_pr_review(repo_name: str, pr_number: int):
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    diff_text = ""
    files_count = 0
    for file in pr.get_files():
        files_count += 1
        if file.patch:
            diff_text += f"File: {file.filename}\n{file.patch}\n\n"

    if not diff_text:
        pr.create_issue_comment("No reviewable code changes found in this PR.")
        return

    print("Sending diff to Gemini...")
    review = get_ai_review(diff_text)
    pr.create_issue_comment(f"### 🤖 AI Code Review\n\n{review}")

    try:
        with SessionLocal() as session:
            session.add(
                Review(
                    repo_name=repo_name,
                    pr_number=pr_number,
                    files_count=files_count,
                    review_text=review,
                )
            )
            session.commit()
        print("Review posted and saved to database!")
    except Exception as e:
        print(f"Review posted, but saving to database failed: {e}")


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = json.loads(body)

    if payload.get("action") == "opened":
        repo_name = payload["repository"]["full_name"]
        pr_number = payload["pull_request"]["number"]

        print(f"New PR opened: {repo_name} #{pr_number}")
        background_tasks.add_task(process_pr_review, repo_name, pr_number)

    return {"status": "ok"}