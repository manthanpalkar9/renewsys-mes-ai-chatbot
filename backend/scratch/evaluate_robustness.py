import asyncio
import json
import time
from app.llm.ollama_provider import OllamaProvider
from app.services.session_service import session_manager
from app.services.chat_service import chat_service

async def main():
    print("Loading queries...")
    with open("tests/fixtures/llm_robustness_queries.json") as f:
        dataset = json.load(f)

    llm = OllamaProvider("http://localhost:11434", "llama3.2")
    # Warm up
    try:
        await llm.parse_intent("hello", [])
    except Exception as e:
        print("Warmup failed:", e)

    results = []
    
    print("\n--- Single-turn Evaluation ---")
    for item in dataset["single"]:
        query = item["query"]
        expected = item["expected"]
        
        t0 = time.time()
        try:
            res = await llm.parse_intent(query, [])
            latency = time.time() - t0
            
            res_dict = res.model_dump()
            
            intent_pass = res_dict["intent"] == expected.get("intent")
            metric_pass = True
            if "metric" in expected:
                metric_pass = res_dict.get("metric") == expected["metric"]
            
            param_pass = True
            for k, v in expected.items():
                if k not in ("intent", "metric"):
                    if res_dict.get(k) != v:
                        param_pass = False
                        
            passed = intent_pass and metric_pass and param_pass
            
            result = {
                "id": item["id"],
                "category": item["category"],
                "query": query,
                "expected": expected,
                "actual": res_dict,
                "latency": latency,
                "pass": passed,
                "intent_pass": intent_pass,
                "param_pass": metric_pass and param_pass
            }
            results.append(result)
            print(f"[{'PASS' if passed else 'FAIL'}] {item['id']}: {query}")
            if not passed:
                print(f"  Expected: {expected}")
                print(f"  Actual: {res_dict}")
        except Exception as e:
            print(f"[ERROR] {item['id']}: {e}")
            results.append({"id": item["id"], "category": item["category"], "pass": False, "intent_pass": False, "param_pass": False, "latency": time.time() - t0})

    print("\n--- Conversational Evaluation ---")
    for conv in dataset["conversational"]:
        context = {}
        history = []
        for i, turn in enumerate(conv["turns"]):
            query = turn["query"]
            expected = turn["expected"]
            
            t0 = time.time()
            try:
                res = await llm.parse_intent(query, history)
                latency = time.time() - t0
                
                # Resolve context
                res = res.resolve_with_context(context)
                res_dict = res.model_dump()
                
                # Update context
                if res.line is not None: context["last_line"] = res.line
                if res.shift is not None: context["last_shift"] = res.shift
                if res.metric is not None: context["last_kpi"] = res.metric
                if res.date_expression is not None: context["last_date_expression"] = res.date_expression
                
                intent_pass = res_dict["intent"] == expected.get("intent")
                param_pass = True
                for k, v in expected.items():
                    if k != "intent":
                        if res_dict.get(k) != v:
                            param_pass = False
                            
                passed = intent_pass and param_pass
                
                history.append({"role": "user", "content": query})
                history.append({"role": "assistant", "content": "mocked response"})
                
                turn_id = f"{conv['id']}_t{i+1}"
                result = {
                    "id": turn_id,
                    "category": conv["category"],
                    "query": query,
                    "expected": expected,
                    "actual": res_dict,
                    "latency": latency,
                    "pass": passed,
                    "intent_pass": intent_pass,
                    "param_pass": param_pass
                }
                results.append(result)
                print(f"[{'PASS' if passed else 'FAIL'}] {turn_id}: {query}")
                if not passed:
                    print(f"  Expected: {expected}")
                    print(f"  Actual: {res_dict}")
            except Exception as e:
                print(f"[ERROR] {conv['id']}_t{i+1}: {e}")
                results.append({"id": f"{conv['id']}_t{i+1}", "category": conv["category"], "pass": False, "intent_pass": False, "param_pass": False, "latency": time.time() - t0})

    # Save results
    with open("scratch/eval_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
