import random
import openai
import os
import re
from typing import Tuple

# You are an AI log analysis expert. Given a log message by user, parse it into variables and template using python f-string syntax. If there are no semantic variable names in this log, just provide `template = log_message`. The code you provide should be excutable and can generate the same user's input log. Do not include any explanations. Only provide the code. Here are some examples:

instruction = """
You are an AI log analysis expert. You should look a log message given by user then generate python code including variable assigning lines and f-string template assigining line. If there are no semantic variable names in this log message, template should be same as the log message. The generated code should generate the user's input log. Followings are examples:
EXAMPLES:
{examples}
END EXAMPLES
""".strip()

examples = [
    "USER: 'workerEnv.init() ok /etc/httpd/conf/workers2.properties'",
    "ASSISTANT: path = '/etc/httpd/conf/workers2.properties'\ntemplate = f'workerEnv.init() ok {path}'\n",
    "USER: 'Listing instance in cell 949e1227'",
    "ASSISTANT: cell_id = '949e1227'\ntemplate = f'Listing instance in cell {cell_id}'\n",
    "USER: 'ss.bdimg.com:80 error : Could not connect to proxy proxy.cse.cuhk.edu.hk:5070 - Could not resolve proxy.cse.cuhk.edu.hk error 11001'",
    "ASSISTANT: host = 'ss.bdimg.com'\nhost_port = '80'\nproxy = 'proxy.cse.cuhk.edu.hk'\nproxy_port = '5070'\nerror_cde = '11001'\ntemplate = f'{host}:{host_port} error : Could not connect to proxy {proxy}:{proxy_port} - Could not resolve proxy {proxy} error {error_code}'",
    "USER: 'onReceive action: android.intent.action.SCREEN_ON'",
    "ASSISTANT: template = f'onReceive action: android.intent.action.SCREEN_ON'"
]

second_instruction = """
SAMPLES: {samples}
Second, above are sample log messages generated by the template you've generated. Determine if the template needs to be updated by determining if the template is correct and that the variable names are well-constructed to represent the log messages.
""".strip()

third_instruction = """
Third, you should update the template to make it more generic and meaningful. The template should still be able to generate the sample log messages.
""".strip()

class LogParsingGPT:
    def __init__(self, temparature=0.2, openai_api_key: str = None) -> None:
        openai.api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        self.model = 'gpt-3.5-turbo'
        self.temparature = temparature
        self.instruction = instruction
        self.examples = examples
        self.second_instruction = second_instruction
        self.third_instruction = third_instruction
        self.messages = [{"role": "system", "content": instruction.format(examples='\n'.join(self.examples))}]

    def llm_run(self, user_prompt: str) -> str:
        response = openai.ChatCompletion.create(
            model=self.model,
            temperature=self.temparature,
            messages=self.messages + [{"role": "user", "content": user_prompt}]
        )
        return response['choices'][0]['message']['content']
        
    def output_parse(self,llm_output: str) -> dict:
        llm_output = llm_output.replace('ASSISTANT:\n', '')
        *variables, template = llm_output.split('\n')

        before = locals().copy()
        exec('\n'.join(variables))
        after = locals().copy()
        variables = {k: after[k] for k in after if k not in before and k != 'before'}
        
        template = template.split('=')[1].strip()

        if template.startswith('f'):
            template = template[1:]
        template = template.strip("'").strip('"').strip()

        # re-esacpe
        template = template.replace("\\'", "'")

        return {'variables': variables, 'template': template}
        
def check_substring_set(string, substring_set):
    current_index = 0
    for substring in substring_set:
        substring_index = string.find(substring, current_index)
        if substring_index == -1:
            return False
        current_index = substring_index + len(substring)
    return True
       
def match_template(logs: list[str], template: str) -> list[str]:
    template = replace_variable(template)
    template = re.escape(template)
    template = template.replace(r'<\*>', r'(.+)')
    regex = re.compile(template)
    return [ log for log in logs if regex.match(log) ]
     
def replace_variable(string):
    pattern = r'{(.*?)}'  # '{variable_name}' 패턴을 정규식으로 표현
    replaced_string = re.sub(pattern, r'<*>', string)
    return replaced_string

def var_to_star(template: str) -> str:
    replaced_template = replace_variable(template)
    return replaced_template

def pipeline(logset: set[str], result: dict[str, dict], temparature=0.2) -> Tuple[dict[str, dict], set[str]]:
    print('---PIPELINE---')
    log_parser = LogParsingGPT(temparature=temparature)
    all_matches = set()
    for unique_log in logset:
        if unique_log in all_matches:
            continue
        print(f'Parsed {len(all_matches)} / {len(logset)} logs')
        llm_output = log_parser.llm_run(f"'{unique_log}'")
        try:
            output = log_parser.output_parse(llm_output)
        except Exception as e:
            print("---[ERROR]---\n",e)
            print(f'{unique_log} \n-> \n{llm_output}')
            print("---[SKIP THIS LOG]---")
            continue
        matches = match_template(list(logset), output['template'])

        if len(matches) > 0:
            result[output['template']] = {
                'variables': output['variables'],
                'matches': matches,
            }
        else:
            print("---[NO MATCH]---")
            print(f'{unique_log} \n-> \n{output["template"]}')
            print("---[SKIP THIS LOG]---")
        all_matches.update(matches)
    print(f'Parsed {len(result)} templates from {len(all_matches)} / {len(logset)} logs')
    
    return result, logset - all_matches

def run(logs: list[str]) -> dict[str, dict]:
    result = {}
    random.shuffle(logs)
    logset = set(logs)
    result, logset = pipeline(logset, result, temparature=0.0)
    while len(logset) > 0:
        result, logset = pipeline(logset, result, temparature=0.8)
    return result

def duplicate_template(templates: list[str]):
    dups = {}
    for t in templates:
        result = match_template(templates, t)
        if len(result) > 1:
            subs = [ r for r in result if r != t]
            dups[t] = subs
    same = []
    for t in dups:
        for s in dups[t]:
            if t in dups[s]:
                same.append((t,s))
    return dups, same
    
if __name__ == '__main__':
    from data_utils import load_dataset
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, required=True)
    parser.add_argument('--read', type=bool, default=False)
    args = parser.parse_args()

    if args.read:
        with open(f'results/result_{args.dataset}.json', 'r') as f:
            result = json.load(f)

        duplicate_template(result.keys())
        exit(0)

    test_data = load_dataset(args.dataset)
    logs = test_data['log'].tolist()
    result = run(logs)

    # print('---[Duplicated templates]---')
    # duplicate_template(result.keys())

    import json
    with open(f'results/result_{args.dataset}.json', 'w') as f:
        json.dump(result, f, indent=4)

