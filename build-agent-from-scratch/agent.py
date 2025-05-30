from termcolor import colored
import os
from dotenv import load_dotenv
load_dotenv()
### Models
import requests
import json
import operator
from google import genai
from google.genai import types

class OllamaModel:
    def __init__(self, model, system_prompt, temperature=0, stop=None):
        """
        Initializes the OllamaModel with the given parameters.

        Parameters:
        model (str): The name of the model to use.
        system_prompt (str): The system prompt to use.
        temperature (float): The temperature setting for the model.
        stop (str): The stop token for the model.
        """
        self.model_endpoint = "http://localhost:11434/api/generate"
        self.temperature = temperature
        self.model = model
        self.system_prompt = system_prompt
        self.headers = {"Content-Type": "application/json"}
        self.stop = stop

    def generate_text(self, prompt):
        """
        Generates a response from the Ollama model based on the provided prompt.

        Parameters:
        prompt (str): The user query to generate a response for.

        Returns:
        dict: The response from the model as a dictionary.
        """
        payload = {
            "model": self.model,
            "format": "json",
            "prompt": prompt,
            "system": self.system_prompt,
            "stream": False,
            "temperature": self.temperature,
            "stop": self.stop
        }

        try:
            request_response = requests.post(
                self.model_endpoint, 
                headers=self.headers, 
                data=json.dumps(payload)
            )

            print("REQUEST RESPONSE", request_response)
            request_response_json = request_response.json()
            response = request_response_json['response']
            response_dict = json.loads(response)

            print(f"\n\nResponse from Ollama model: {response_dict}")

            return response_dict
        except requests.RequestException as e:
            response = {"error": f"Error in invoking model! {str(e)}"}
            return response
        

class GeminiModel:
    def __init__(self, system_prompt, temperature=0, stop=None):
        """
        Initializes the GeminiModel with the given parameters using the Gemini SDK.

        Parameters:
        model (str): The name of the Gemini model to use (e.g., "gemini-pro", "gemini-1.5-flash").
        system_prompt (str): The system prompt to guide the model's behavior.
        api_key (str): Your Google Cloud API key for accessing Gemini.
                       It's recommended to load this from an environment variable for security.
        temperature (float): The temperature setting for the model (0.0 to 1.0).
                             Higher values make the output more random.
        stop (str or list of str, optional): A stop sequence or a list of stop sequences.
                                            The model will stop generating text when it encounters any of these.
        """
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.stop = stop


        # Configure the Gemini API with the provided API key
        # It's best practice to load API keys from environment variables:
        # genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        API_KEY = os.getenv("GEMINI_API_KEY")

        # Initialize the generative model
        self.model = genai.Client(vertexai=False, api_key=API_KEY)

    def generate_text(self, prompt):
        """
        Generates a response from the Gemini model based on the provided prompt.
        It attempts to parse the response as JSON, similar to the OllamaModel.

        Parameters:
        prompt (str): The user query to generate a response for.

        Returns:
        dict: The response from the model as a dictionary.
              Returns an error dictionary if the API call fails or JSON parsing fails.
        """
        try:
            # Construct the content for the model.
            # To emulate Ollama's 'system' parameter and ensure JSON output,
            # we combine the system prompt, a JSON output instruction, and the user's prompt
            # into the 'user' role's content parts.
            
            # Instruction to ensure the model outputs JSON
            json_output_instruction = "Please provide the response as a JSON object"

            full_content_parts = []
            if self.system_prompt:
                full_content_parts.append(self.system_prompt)
            
            full_content_parts.append(json_output_instruction)
            full_content_parts.append(prompt)

            # The `contents` list represents the conversation turn.
            # For a single-turn interaction mirroring the Ollama template,
            # we pass a list containing one user message.
            # contents = [
            #     {"role": "user", "parts": full_content_parts}
            # ]
            contents = types.Content(
                role='user',
                parts=[types.Part.from_text(text="".join(full_content_parts))]
            )

            # Define generation configuration parameters
            # generation_config = {
            #     "temperature": self.temperature,
            #     # You might add other parameters here if needed, e.g.:
            #     # "top_p": 0.95,
            #     # "top_k": 0.0,
            #     # "max_output_tokens": 8192,
            # }
            model_config = types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                # max_output_tokens=8192,
                max_output_tokens=1024,
                temperature=float(self.temperature),
                top_k=0.0,
                top_p=0.95,
            ),

            # print(f"Sending prompt to Gemini model: {full_content_parts}")

            # Make the API call to generate content
            response = self.model.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=contents,
                # config=model_config
            )

            # Access the text from the response object
            response_text = response.text
            # print("RAW GEMINI RESPONSE TEXT:", response_text)

                        # Strip markdown code fences if present
            if response_text.startswith("```json"):
                response_text = response_text[len("```json"):]
            if response_text.startswith("```"): # Handle cases where only ``` is present before json
                response_text = response_text[len("```"):]
            if response_text.endswith("```"):
                response_text = response_text[:-len("```")]
            
            response_text = response_text.strip() # Clean up any leading/trailing whitespace

            # print(response_text)

            # Attempt to parse the response text as a JSON dictionary
            ## 
            response_dict = json.loads(response_text)

            # print(f"\n\nResponse from Gemini model: {response_dict}")

            return response_dict

        except json.JSONDecodeError as e:
            # Handle cases where the model's response is not valid JSON
            error_message = f"Error parsing Gemini model response as JSON: {str(e)}"
            print(error_message)
            return {"error": error_message, "raw_response": response_text}
        except Exception as e:
            # Catch any other exceptions during the API call or processing
            error_message = f"Error in invoking Gemini model: {str(e)}"
            print(error_message)
            return {"error": error_message}
        
def basic_calculator(input_str):
    """
    Perform a numeric operation on two numbers based on the input string or dictionary.

    Parameters:
    input_str (str or dict): Either a JSON string representing a dictionary with keys 'num1', 'num2', and 'operation',
                            or a dictionary directly. Example: '{"num1": 5, "num2": 3, "operation": "add"}'
                            or {"num1": 67869, "num2": 9030393, "operation": "divide"}

    Returns:
    str: The formatted result of the operation.

    Raises:
    Exception: If an error occurs during the operation (e.g., division by zero).
    ValueError: If an unsupported operation is requested or input is invalid.
    """
    try:
        # Handle both dictionary and string inputs
        if isinstance(input_str, dict):
            input_dict = input_str
        else:
            # Clean and parse the input string
            input_str_clean = input_str.replace("'", "\"")
            input_str_clean = input_str_clean.strip().strip("\"")
            input_dict = json.loads(input_str_clean)
        
        # Validate required fields
        if not all(key in input_dict for key in ['num1', 'num2', 'operation']):
            return "Error: Input must contain 'num1', 'num2', and 'operation'"

        num1 = float(input_dict['num1'])  # Convert to float to handle decimal numbers
        num2 = float(input_dict['num2'])
        operation = input_dict['operation'].lower()  # Make case-insensitive
    except (json.JSONDecodeError, KeyError) as e:
        return "Invalid input format. Please provide valid numbers and operation."
    except ValueError as e:
        return "Error: Please provide valid numerical values."

    # Define the supported operations with error handling
    operations = {
        'add': operator.add,
        'plus': operator.add,  # Alternative word for add
        'subtract': operator.sub,
        'minus': operator.sub,  # Alternative word for subtract
        'multiply': operator.mul,
        'times': operator.mul,  # Alternative word for multiply
        'divide': operator.truediv,
        'floor_divide': operator.floordiv,
        'modulus': operator.mod,
        'power': operator.pow,
        'lt': operator.lt,
        'le': operator.le,
        'eq': operator.eq,
        'ne': operator.ne,
        'ge': operator.ge,
        'gt': operator.gt
    }

    # Check if the operation is supported
    if operation not in operations:
        return f"Unsupported operation: '{operation}'. Supported operations are: {', '.join(operations.keys())}"

    try:
        # Special handling for division by zero
        if (operation in ['divide', 'floor_divide', 'modulus']) and num2 == 0:
            return "Error: Division by zero is not allowed"

        # Perform the operation
        result = operations[operation](num1, num2)
        
        # Format result based on type
        if isinstance(result, bool):
            result_str = "True" if result else "False"
        elif isinstance(result, float):
            # Handle floating point precision
            result_str = f"{result:.6f}".rstrip('0').rstrip('.')
        else:
            result_str = str(result)

        return f"The answer is: {result_str}"
    except Exception as e:
        return f"Error during calculation: {str(e)}"

def reverse_string(input_string):
    """
    Reverse the given string.

    Parameters:
    input_string (str): The string to be reversed.

    Returns:
    str: The reversed string.
    """
    # Check if input is a string
    if not isinstance(input_string, str):
        return "Error: Input must be a string"
    
    # Reverse the string using slicing
    reversed_string = input_string[::-1]
    
    # Format the output
    result = f"The reversed string is: {reversed_string}"
    
    return result

class ToolBox:
    def __init__(self):
        self.tools_dict = {}

    def store(self, functions_list):
        """
        Stores the literal name and docstring of each function in the list.

        Parameters:
        functions_list (list): List of function objects to store.

        Returns:
        dict: Dictionary with function names as keys and their docstrings as values.
        """
        for func in functions_list:
            self.tools_dict[func.__name__] = func.__doc__
        return self.tools_dict

    def tools(self):
        """
        Returns the dictionary created in store as a text string.

        Returns:
        str: Dictionary of stored functions and their docstrings as a text string.
        """
        tools_str = ""
        for name, doc in self.tools_dict.items():
            tools_str += f"{name}: \"{doc}\"\n"
        return tools_str.strip()
    
agent_system_prompt_template = """
You are an intelligent AI assistant with access to specific tools. Your responses must ALWAYS be in this JSON format:
{{
    "tool_choice": "name_of_the_tool",
    "tool_input": "inputs_to_the_tool"
}}

TOOLS AND WHEN TO USE THEM:

1. basic_calculator: Use for ANY mathematical calculations
   - Input format: {{"num1": number, "num2": number, "operation": "add/subtract/multiply/divide"}}
   - Supported operations: add/plus, subtract/minus, multiply/times, divide
   - Example inputs and outputs:
     Input: "Calculate 15 plus 7"
     Output: {{"tool_choice": "basic_calculator", "tool_input": {{"num1": 15, "num2": 7, "operation": "add"}}}}
     
     Input: "What is 100 divided by 5?"
     Output: {{"tool_choice": "basic_calculator", "tool_input": {{"num1": 100, "num2": 5, "operation": "divide"}}}}

2. reverse_string: Use for ANY request involving reversing text
   - Input format: Just the text to be reversed as a string
   - ALWAYS use this tool when user mentions "reverse", "backwards", or asks to reverse text
   - Example inputs and outputs:
     Input: "Reverse of 'Howwwww'?"
     Output: {{"tool_choice": "reverse_string", "tool_input": "Howwwww"}}
     
     Input: "What is the reverse of Python?"
     Output: {{"tool_choice": "reverse_string", "tool_input": "Python"}}

3. no tool: Use for general conversation and questions
   - Example inputs and outputs:
     Input: "Who are you?"
     Output: {{"tool_choice": "no tool", "tool_input": "I am an AI assistant that can help you with calculations, reverse text, and answer questions. I can perform mathematical operations and reverse strings. How can I help you today?"}}
     
     Input: "How are you?"
     Output: {{"tool_choice": "no tool", "tool_input": "I'm functioning well, thank you for asking! I'm here to help you with calculations, text reversal, or answer any questions you might have."}}

STRICT RULES:
1. For questions about identity, capabilities, or feelings:
   - ALWAYS use "no tool"
   - Provide a complete, friendly response
   - Mention your capabilities

2. For ANY text reversal request:
   - ALWAYS use "reverse_string"
   - Extract ONLY the text to be reversed
   - Remove quotes, "reverse of", and other extra text

3. For ANY math operations:
   - ALWAYS use "basic_calculator"
   - Extract the numbers and operation
   - Convert text numbers to digits

Here is a list of your tools along with their descriptions:
{tool_descriptions}

Remember: Your response must ALWAYS be valid JSON with "tool_choice" and "tool_input" fields.
"""

class Agent:
    def __init__(self, tools):
        """
        Initializes the agent with a list of tools and a model.

        Parameters:
        tools (list): List of tool functions.
        model_service (class): The model service class with a generate_text method.
        model_name (str): The name of the model to use.
        """
        self.tools = tools

    def prepare_tools(self):
        """
        Stores the tools in the toolbox and returns their descriptions.

        Returns:
        str: Descriptions of the tools stored in the toolbox.
        """
        toolbox = ToolBox()
        toolbox.store(self.tools)
        tool_descriptions = toolbox.tools()
        return tool_descriptions

    def think(self, prompt):
        """
        Runs the generate_text method on the model using the system prompt template and tool descriptions.

        Parameters:
        prompt (str): The user query to generate a response for.

        Returns:
        dict: The response from the model as a dictionary.
        """
        tool_descriptions = self.prepare_tools()
        agent_system_prompt = agent_system_prompt_template.format(tool_descriptions=tool_descriptions)

        # Create an instance of the model service with the system prompt

       
        model_instance = GeminiModel(agent_system_prompt)
        
        # Generate and return the response dictionary
        agent_response_dict = model_instance.generate_text(prompt)
        return agent_response_dict

    def work(self, prompt):
        """
        Parses the dictionary returned from think and executes the appropriate tool.

        Parameters:
        prompt (str): The user query to generate a response for.

        Returns:
        The response from executing the appropriate tool or the tool_input if no matching tool is found.
        """
        agent_response_dict = self.think(prompt)
        # print(f" Agent response dict: ${agent_response_dict}")
        tool_choice = agent_response_dict.get("tool_choice")
        tool_input = agent_response_dict.get("tool_input")

        for tool in self.tools:
            if tool.__name__ == tool_choice:
                response = tool(tool_input)
                print(colored(response, 'cyan'))
                return

        print(colored(tool_input, 'cyan'))
        return
    
# Example usage
if __name__ == "__main__":
    """
    Instructions for using this agent:
    
    Example queries you can try:
    1. Calculator operations:
       - "Calculate 15 plus 7"
       - "What is 100 divided by 5?"
       - "Multiply 23 and 4"
    
    2. String reversal:
       - "Reverse the word 'hello world'"
       - "Can you reverse 'Python Programming'?"
    
    3. General questions (will get direct responses):
       - "Who are you?"
       - "What can you help me with?"
    
    Ollama Commands (run these in terminal):
    - Check available models:    'ollama list'
    - Check running models:      'ps aux | grep ollama'
    - List model tags:          'curl http://localhost:11434/api/tags'
    - Pull a new model:         'ollama pull mistral'
    - Run model server:         'ollama serve'
    """

    tools = [basic_calculator, reverse_string]

    # Using Ollama with llama2 model
    model_service = GeminiModel("")

    agent = Agent(tools=tools)

    print("\nWelcome to the AI Agent! Type 'exit' to quit.")
    print("You can ask me to:")
    print("1. Perform calculations (e.g., 'Calculate 15 plus 7')")
    print("2. Reverse strings (e.g., 'Reverse hello world')")
    print("3. Answer general questions\n")

    while True:
        prompt = input("Ask me anything: ")
        if prompt.lower() == "exit":
            break

        agent.work(prompt)
