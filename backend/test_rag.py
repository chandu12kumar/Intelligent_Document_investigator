import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")
from app.services.rag import run_investigation

questions = [
    "What is Ant Colony Optimisation?",
    "When was the lecture given?",
    "Who is Marco Dorigo?",
    "What applications are mentioned?",
    "What is the phone number of Michael Herrmann?",
    "What is the company's maternity leave policy?",
]

async def main():
    for q in questions:
        print("\n" + "=" * 70)
        print(f"QUESTION: {q}")
        res = await run_investigation(q)
        print(f"STATUS: {res.status.value}")
        print(f"CONFIDENCE: {res.confidence_level.value} ({res.confidence:.2f})")
        print(f"ANSWER:\n{res.answer}")
        print("KEY EVIDENCE:")
        for pt in res.evidence_points:
            print(f"  • {pt}")
        print("SOURCES:")
        for s in res.sources:
            print(f"  📄 {s.document} — Page {s.page} (Relevance: {int(s.relevance * 100)}%)")
            print(f"     \"{s.excerpt}\"")
        if res.uncertainty:
            print(f"UNCERTAINTY: {res.uncertainty}")
        else:
            print("UNCERTAINTY: None")

if __name__ == "__main__":
    asyncio.run(main())
