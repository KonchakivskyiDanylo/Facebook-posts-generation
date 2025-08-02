import requests

res = requests.post("http://localhost:11434/api/generate", json={
    "model": "deepseek-r1",
    "prompt": "Explain DevOps in 3 lines.",
    "stream": False
})
print(res.status_code)
print(res.json())
