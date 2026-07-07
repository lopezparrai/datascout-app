import os
import pandas as pd
from google import genai
from google.genai import types

def describe_data(columns: list[str] = None) -> str:
    return "Dummy describe data result"

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

chat_history = [
    types.Content(role="user", parts=[types.Part.from_text(text="Give me a summary of the data")])
]

try:
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=chat_history,
        config=types.GenerateContentConfig(
            system_instruction="Dataset columns available: ['a', 'b']",
            tools=[describe_data],
        )
    )
    print("API Call Success")
    print("Has function calls?", bool(response.function_calls))
    
    if response.function_calls:
        # Append the model's response directly
        chat_history.append(response.candidates[0].content)
        
        # Build function response
        func_responses = []
        for fc in response.function_calls:
            print("Calling:", fc.name, fc.args)
            func_responses.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": "It works!"}
                )
            )
        chat_history.append(types.Content(role="user", parts=func_responses))
        
        # Second call
        resp2 = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=chat_history,
            config=types.GenerateContentConfig(
                system_instruction="Dataset columns available: ['a', 'b']",
                tools=[describe_data],
            )
        )
        print("Second call text:", resp2.text)
        
except Exception as e:
    import traceback
    traceback.print_exc()
