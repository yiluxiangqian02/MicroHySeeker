import httpx
t = httpx.HTTPTransport(local_address="0.0.0.0")
c = httpx.Client(transport=t, timeout=10)
r = c.get("http://127.0.0.1:8200/api/experiments/detail/exp_20260420_215521_222242/progress")
d = r.json()
st = d.get("status")
step = d.get("current_step", {})
step_type = step.get("step_type", "?") if isinstance(step, dict) else "?"
err = d.get("error_detail")
print(f"status={st} step_type={step_type} err={err}")
c.close()
