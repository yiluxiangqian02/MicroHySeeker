import httpx, time
t = httpx.HTTPTransport(local_address="0.0.0.0")
c = httpx.Client(transport=t, timeout=15)
for i in range(120):
    time.sleep(5)
    try:
        r = c.get("http://127.0.0.1:8200/api/experiments/detail/exp_20260420_215521_222242/progress")
        d = r.json()
        st = d.get("status", "?")
        step = d.get("current_step", {})
        step_type = step.get("step_type", "?") if isinstance(step, dict) else "?"
        step_desc = (step.get("description", "")[:30] if isinstance(step, dict) else "")
        err = d.get("error_detail", "")
        print(f"[{(i+1)*5}s] st={st} type={step_type} desc={step_desc} err={err}")
        if st in ("completed", "failed", "stopped"):
            break
    except Exception as e:
        print(f"[{(i+1)*5}s] poll error: {e}")
        c.close()
        t = httpx.HTTPTransport(local_address="0.0.0.0")
        c = httpx.Client(transport=t, timeout=15)
c.close()
