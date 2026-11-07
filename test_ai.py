import ollama

# Ask our local AI model a question
response = ollama.chat(
    model="llama3.2:3b",
    messages=[
        {
            "role": "user",
            "content": "What is HIPAA? Explain in one sentence."
        }
    ]
)

# Display the AI's answer
print(response["message"]["content"])