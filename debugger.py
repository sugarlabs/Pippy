import openai

# Initialize a chat history to provide context for llm model
chat = [{"role": "system",
        "content": """You are a very friendly python programming assistant for children. 
                    Your goal is to help them debug or answer specific questions in simple and child-friendly language. 
                    Please note, you should provide some code analysis and guide them to find bugs instead of giving solutions directly.
                    You could encourage them to explore and think by raising relevant questions or providing useful tips."
                    You can use simple metaphors to make abstract concepts become easy-to-understand."""
        }]


def prompt_template(user_code, learner_question):
    """
    Prompt Engineering
    This function generates a well-formated prompt to send to LLM
    Input:
    user_code: string. The code extracted from code editor
    learner_question: string. Initially should be "Why the code doesn't work",
    but could also be specific follow-up questions.
    """
    prompt = f"""
    This is my code: {user_code}
    Could you please teach me {learner_question} 
    """
    return prompt


def code_analysis_with_llm(chat, prompt):
    chat.append({"role": "user", "content": prompt})
    response = openai.ChatCompletion.create(
        model = "gpt-4o",
        messages = chat,
    )
    ai_response = response.choices[0].message.content
    chat.append({"role": "assistant", "content": ai_response})
    return ai_response


def get_ai_response(user_code, learner_question):
    prompt = prompt_template(user_code, learner_question)
    ai_response = code_analysis_with_llm(prompt)
    return ai_response