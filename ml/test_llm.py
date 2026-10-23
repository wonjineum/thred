from llm import client, LLM_MODEL

r = client.chat.completions.create(
    model=LLM_MODEL,
    messages=[{"role": "user", "content": "Say hello in 3 words."}],
)
print(r.choices[0].message.content)