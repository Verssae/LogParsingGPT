import openai
import os
from prompts import system_prompt, examples
from data_utils import load_dataset
import logging

logging.basicConfig(level=logging.INFO)

class LlmLogParser:
    def __init__(self, openai_api_key=None) -> None:
        openai.api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        self.model = 'gpt-3.5-turbo'

        self.prompt = system_prompt
        self.examples = examples

    def llm_parse(self, log: str) -> str:
        input_prompt = "INPUT: {log}"
        history = [
            ["Failed password for root from 183.62.140.253 port 37999 ssh2", """username = 'root'
ip_address = '183.62.140.253'
port = '37999'
template = f'Failed password for {username} from {ip_address} port {port} ssh2'"""],

        ]
        response = openai.ChatCompletion.create(
            model=self.model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": self.prompt.format(examples='\n'.join(self.examples))},
                {"role": "user", "content": input_prompt.format(log=history[0][0])},
                {"role": "assistant", "content": history[0][1]},
                {"role": "user", "content": input_prompt.format(log=log)}
            ]
        )
        return response['choices'][0]['message']['content']
    
    def parse_output(self, llm_output: str) -> dict:
        _, *variables, template = llm_output.split('\n')
        variables = [var.split(' = ') for var in variables]
        variables = {var[0]: var[1] for var in variables}
        # remove quotes from variables
        for var in variables:
            if variables[var].startswith("'") and variables[var].endswith("'"):
                variables[var] = variables[var][1:-1]
            
        template = template.split(' = ')[1]
        # remove f-string
        template = template[2:-1]
        for var in variables:
            template = template.replace('{' + var + '}', '<*>')

        return {'variables': variables, 'template': template}
    
    def validate_output(self, log:str, parsed: dict) -> bool:
        variables = parsed['variables']
        template = parsed['template']

        if variables != {}:
            template = template.replace('<*>', '{}').format(*variables.values())
        back = eval("'" + template + "'")

        return back == log
    
    def parse(self, log: str) -> dict:
        llm_output = self.llm_parse(log)
        parsed = self.parse_output(llm_output)
        # if not self.validate_output(log, parsed):
        #     logging.warning(f'Validation failed for log {log}')
        #     return None
        return parsed
    
def test_llm_parse():
    print('Testing LlmLogParser with OpenSSH dataset')
    print('function: llm_parse')
    parser = LlmLogParser()
    logs = load_dataset('OpenSSH')
    
    test_cases = logs.sample(3)
    for i in range(len(test_cases)):
        tc = test_cases.iloc[i]
        log = tc['log']
        print(f'{log}')
        gt = tc['template']
        output = parser.llm_parse(log)
        print('------------------>')
        print(output)
        print(f"template = f'{gt}'")
        print('-------------------')
        assert output == f"template = f'{gt}'"

def test_llm_parse_static():
    print('Testing LlmLogParser with OpenSSH dataset (static)')
    print('function: llm_parse')
    parser = LlmLogParser()
    logs = load_dataset('OpenSSH')
    logs = logs[logs['only_static']]
    test_cases = logs.sample(3)
    for i in range(len(test_cases)):
        tc = test_cases.iloc[i]
        log = tc['log']
        print(f'{log}')
        gt = tc['template']
        output = parser.llm_parse(log)
        print('------------------>')
        print(output)
        print(f"template = f'{gt}'")
        print('-------------------')
    
if __name__ == '__main__':
    test_llm_parse()
    test_llm_parse_static()