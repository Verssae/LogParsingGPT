import logging
import openai
import os
import random
import tqdm
from pandas import DataFrame
import re

from data_utils import dataset, load_dataset

logging.basicConfig(level=logging.INFO)


openai.api_key = os.environ.get('OPENAI_API_KEY')
model = 'gpt-3.5-turbo'

system_prompt = """This is a log parser that parses a log line into a template and variables if variables exist. You should produce variable assigning lines and template assigning line using python syntax, specially f-string syntax. The generated code should generate the user's input log.
"""

refine_prompt = """You are an AI log analysis expert. You should look at sample log templates with variables and corresponding log messages, and update the templates where possible to make them more generic and meaningful. Sample logs should still be identifiable after template modifications. If you already have a well-made template, don't update it.
"""

refine_user_input = """ORIGINAL TEMPLATE: {template}
SAMPLED LOGS:
{logs}
END SAMPLED LOGS

"""

examples = [
    {"role": "user", "content": "'Returning 500 to user'"},
    {"role": "assistant", "content": "status_code = '500'\ntemplate = f'Returning {status_code} to user'"},
    {"role": "user", "content": "'Listing instance in cell 949e1227'"},
    {"role": "assistant", "content": "cell_id = '949e1227'\ntemplate = f'Listing instance in cell {cell_id}'"},
    {"role": "user", "content": "'onReceive action: android.intent.action.SCREEN_ON'"},
    {"role": "assistant", "content": "template = 'onReceive action: android.intent.action.SCREEN_ON'"},
    {"role": "user", "content": "'[instance: d96a117b-0193-4549-bdcc-63b917273d1d] Deleting instance files /var/lib/nova/instances/d96a117b-0193-4549-bdcc-63b917273d1d_del'"},
    {"role": "assistant", "content": "instance_id = 'd96a117b-0193-4549-bdcc-63b917273d1d'\npath = '/var/lib/nova/instances/d96a117b-0193-4549-bdcc-63b917273d1d_del'\ntemplate = f'[instance: {instance_id}] Deleting instance files {path}'"},
]

def llm_parse(log: str, history=examples) -> str:
    user_prompt = f"'{log}'"
    response = openai.ChatCompletion.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_prompt}
        ]
    )
    return response['choices'][0]['message']['content']

def llm_refine(template: str, samples=[]) -> str:
    
    response = openai.ChatCompletion.create(
        model=model,
        temperature=0.0,
        messages=[
            {"role": "system", "content": refine_prompt},
            {"role": "user", "content": refine_user_input.format(template=template, logs='\n'.join(samples))},
        ]
    )
    return response['choices'][0]['message']['content']

def match_template(logs: list[str], regex_template: str):
    matches = [ log for log in logs if re.match(regex_template, log, re.DOTALL)]
    if len(matches) < 3:
        return matches
    else:
        return random.sample(matches, 3)

def output_parse(llm_output: str) -> dict:
    *variables, template = llm_output.split('\n')
    variables = [ [ entity.strip() for entity in var.split('=') ] for var in variables ]
    variables = { var[0]: eval(var[1]) for var in variables }
    # remove quotes from variables
    # for var in variables:
    #     if variables[var].startswith("'") and variables[var].endswith("'"):
    #         variables[var] = variables[var][1:-1]
    template = template.split('=')[1].strip()
    # remove f-string
    template = template[2:-1]
    # remove all '\' from template
    template = template.replace('\\', '')

    # template = remove_semantic(template, variables.keys())

    return {'variables': variables, 'template': template}

def remove_semantic(template: str, variables: list[str]) -> str:
    for var in variables:
        template = template.replace('{' + var + '}', '<*>')
    return template

def to_regex(template: str) -> str:
    regex = template.replace('<*>', '(.+)')
    return regex

def sem_to_regex(template: str, variables: list[str]) -> str:
    for var in variables:
        template = template.replace('{' + var + '}', '(.+)')
    return template

def to_semantic(template: str, variables: dict) -> str:
    for var in variables:
        template = template.replace('<*>','{' + var + '}')
    return template

def reversible(template: str, variables: dict, log:str) -> bool:
    return log == template.format(**variables)

def pipeline(log: str) -> str:
    llm_output = llm_parse(log)
    parsed = output_parse(llm_output)
    regexed = sem_to_regex(parsed['template'], parsed['variables'].keys())

    test_data = load_dataset('HDFS')
    matches = match_template(test_data['log'].to_list(), regexed)
    refined = llm_refine(parsed['template'], matches)
    print(refined)
    # logging.info(f'Input: {log}\nOutput: {parsed}')
    # if reversible(parsed['template'], parsed['variables'], log):
    #     # Save to template database
    #     return parsed
    # else:
    #     logging.error(f'Not reversible: \n{log}\n{parsed["template"]}')
    #     print(parsed["variables"])
    return parsed

def evaluate(test_dataset: DataFrame):
    logs = test_dataset['random_log'].to_list()
    oracle = test_dataset['template'].to_list()
    variables = []
    templates = []
    correct = []
    for i in tqdm.trange(len(test_dataset)):
        parsed = pipeline(logs[i])
        parsed_variables = parsed['variables']
        parsed_template = parsed['template']
        templates.append(parsed_template)
        variables.append(parsed_variables)

        if remove_semantic(parsed_template, parsed_variables) == oracle[i]:
            # logging.info(f'{i+1} / {len(test_dataset)} correct')
            correct.append(True)
        else:
            # logging.warning(f'{i+1} / {len(test_dataset)} incorrect')
            correct.append(False)
    return DataFrame({'log': logs, 'oracle': oracle, 'template': templates, 'variables': variables, 'correct': correct})

def test_llm_refine():
    test_dataset = dataset('HDFS').sample(2)
    test_data = load_dataset('HDFS')
    for i in range(len(test_dataset)):
        log = test_dataset['random_log'].iloc[i]
        template = test_dataset['template'].iloc[i]
        print('[LOG]\n' + log)
        print('[TEMPLATE]\n' + template)
        llm_output = llm_parse(log)
        parsed = output_parse(llm_output)
        regexed = sem_to_regex(parsed['template'], parsed['variables'].keys())
        print('[Parsed]\n' + parsed['template'])
        print('[Regexed]\n' + regexed)
        matches = match_template(test_data['log'].to_list(), regexed)
        print('[Matches]')
        print(matches)
        refined = llm_refine(parsed['template'], matches)
        print(refined)
        



if __name__ == '__main__':
    # save dataframe to csv
    # test_dataset = dataset('HDFS').sample(1)
    # result = evaluate(test_dataset)
    # result.to_csv('result.csv', index=False)
    test_llm_refine()
