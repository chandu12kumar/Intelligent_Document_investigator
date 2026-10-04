import asyncio
import sys
sys.stdout.reconfigure(encoding="utf-8")
from app.services.rag import run_investigation

test_cases = [
    ("What is this document about?", "DOCUMENT SUMMARY TEST"),
    ("Can you summarize the main points?", "KEY POINTS TEST"),
    ("What technical skills are mentioned?", "SKILLS TEST"),
    ("What projects has the candidate worked on?", "PROJECT TEST"),
    ("What is the candidate's educational background?", "EDUCATION TEST"),
    ("What are the main rules mentioned in this document?", "INSUFFICIENT EVIDENCE (RULES) TEST"),
    ("How much medical leave can employees take?", "CONFLICT TEST"),
    ("Tell me a joke.", "OUT OF SCOPE TEST"),
]

async def main():
    results = {}
    print("=" * 80)
    print("RUNNING NATURAL LANGUAGE QUESTION INVESTIGATION TESTS")
    print("=" * 80)

    for question, test_name in test_cases:
        print(f"\n--- [{test_name}] ---")
        print(f"QUESTION: {question}")
        res = await run_investigation(question)
        print(f"STATUS: {res.status.value}")
        print(f"CONFIDENCE: {res.confidence_level.value} ({res.confidence:.2f})")
        print(f"ANSWER:\n{res.answer}")
        print(f"EVIDENCE POINTS ({len(res.evidence_points)}):")
        for pt in res.evidence_points:
            print(f"  • {pt}")
        print(f"SOURCES ({len(res.sources)}):")
        for s in res.sources:
            print(f"  📄 {s.document} (Relevance: {int(s.relevance * 100)}%)")
        if res.uncertainty:
            print(f"UNCERTAINTY: {res.uncertainty}")

        # Verification logic
        passed = False
        if test_name == "DOCUMENT SUMMARY TEST":
            passed = res.status.value == "SUPPORTED" and len(res.answer) > 20
        elif test_name == "KEY POINTS TEST":
            passed = res.status.value == "SUPPORTED" and len(res.evidence_points) >= 1
        elif test_name == "SKILLS TEST":
            passed = res.status.value in ("SUPPORTED", "INSUFFICIENT_EVIDENCE")
        elif test_name == "PROJECT TEST":
            passed = res.status.value in ("SUPPORTED", "INSUFFICIENT_EVIDENCE")
        elif test_name == "EDUCATION TEST":
            passed = res.status.value in ("SUPPORTED", "INSUFFICIENT_EVIDENCE")
        elif test_name == "INSUFFICIENT EVIDENCE (RULES) TEST":
            passed = res.status.value in ("SUPPORTED", "INSUFFICIENT_EVIDENCE")
        elif test_name == "CONFLICT TEST":
            passed = res.status.value in ("CONFLICTING", "SUPPORTED")
        elif test_name == "OUT OF SCOPE TEST":
            passed = res.status.value == "INSUFFICIENT_EVIDENCE" and "uploaded documents" in res.answer.lower()

        results[test_name] = "PASS" if passed else "FAIL"

    print("\n" + "=" * 80)
    print("SUMMARY RESULTS:")
    for name, res in results.items():
        print(f"  {name}: {res}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
