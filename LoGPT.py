import openai
import os
import re
import logging

logging.basicConfig(level=logging.INFO, filename='logpt.log')

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

class LoGPT:
    def __init__(self, temparature=0.2, openai_api_key: str = None) -> None:
        openai.api_key = openai_api_key or os.environ.get('OPENAI_API_KEY')
        self.model = 'gpt-3.5-turbo'
        self.temparature = temparature
        self.instruction = instruction
        self.examples = examples
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
        
        _, *template = template.split('=')
        template = '='.join(template).strip()

        if template.startswith('f'):
            template = template[1:]
        template = template.strip("'").strip('"').strip()

        # re-esacpe
        template = template.replace("\\'", "'")

        return {'variables': variables, 'template': template}
       
def match_template(logs: list[str], template: str) -> list[str]:
    template = replace_variable(template)
    template = re.escape(template)
    template = template.replace(r'<\*>', r'(.*)')
    regex = re.compile(template)
    return [ log for log in logs if regex.match(log) ]
     
def replace_variable(string):
    pattern = r'{(.*?)}'  # '{variable_name}' 패턴을 정규식으로 표현
    replaced_string = re.sub(pattern, r'<*>', string)
    return replaced_string

def run_pipeline(unmatched_logs: set[str], matched_logs: set[str]=set(), result: dict[str, dict]={}, temparature: float = 0.2, verbos: bool=False) -> dict[str, dict]:
    if verbos:
        print('---RUN PIPELINE---')
    logpt = LoGPT(temparature=temparature)
    for log in unmatched_logs:
        if log in matched_logs:
            continue
        try:
            llm_output = logpt.llm_run(f"'{log}'")
            output = logpt.output_parse(llm_output)
        except Exception as e:
            logging.error(f'Error occured {e}')
            logging.info(f'Skip this log: {log}')
            continue
        matches = match_template(list(unmatched_logs), output['template'])
        if len(matches) > 0:
            result[output['template']] = {
                'variables': output['variables'],
                'matches': matches,
            }
            matched_logs.update(matches)
        else:
            if verbos:
                print("---[NO MATCH]---")
                print(f'{log} \n-> \n{output["template"]} | {llm_output}')
                print("---[SKIP THIS LOG]---")

        if verbos:
            print(f'Parsed {len(result)} templates from {len(matched_logs)} / {len(unmatched_logs)} logs')

    return run_pipeline(unmatched_logs - matched_logs, matched_logs, result, temparature=0.8) if len(unmatched_logs - matched_logs) > 0 else result

# TODO: duplicate template detection algorithm
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
    parser.add_argument('--verbose', type=bool, default=False)
    args = parser.parse_args()

    if args.read:
        with open(f'results/result_{args.dataset}.json', 'r') as f:
            result = json.load(f)
        print(result)
        exit(0)

    test_data = load_dataset(args.dataset)
    logs = test_data['log'].tolist()
    result = run_pipeline(set(logs), verbos=args.verbose)

    import json
    with open(f'results/result_{args.dataset}.json', 'w') as f:
        json.dump(result, f, indent=4)

