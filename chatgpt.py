from openai import OpenAI
from langchain.prompts import load_prompt

client = OpenAI(
    api_key=open('api.txt', 'r').read()
)

class ChatGPT:
    def __init__(self, role):
        self.dialog = [{"role":"system","content":role}]
        self.dialog.append({"role":"user","content":load_prompt('prompts/initial_prompt.json').format(role=role)}) 

    def ask_question(self, question):
        self.dialog.append({"role":"user","content":question})
        result = client.chat.completions.create(
            model='gpt-3.5-turbo',
            messages=self.dialog
        )
        answer = result.choices[0].message.content
        self.dialog.append({"role":"assistant","content":answer})
        return answer
    
if __name__ == '__main__':
    chat_gpt = ChatGPT("Systems Engineer")
    while (question := input('\n> ')) != 'X':
        answer = chat_gpt.ask_question(question)
        print(answer)