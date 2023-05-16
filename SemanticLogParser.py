import re
import sqlite3
import pandas as pd
from pandas import DataFrame
import logging
from pathlib import Path

from data_utils import all_datasets
from LogParsingGPT import LogParsingGPT

class SemanticLogParser:
    
    def __init__(self, template_db=Path('templates.db')) -> None:
        self.llm_parser = LogParsingGPT()
        self.templates = self.init_template_db(template_db)
        self.parsed = DataFrame(columns=['log', 'template', 'instances'])
        
    def init_template_db(self, db_file) -> DataFrame:
        conn = sqlite3.connect(db_file)
        conn.execute(f'CREATE TABLE IF NOT EXISTS {db_file.stem} (template TEXT, variables TEXT)')
        templates = pd.read_sql_query(f'SELECT * FROM {db_file.stem}', conn)
        conn.close()
        return templates
    
    def template_to_regex(self, template: str) -> str:
        regex = template.replace('<*>', '(.+)')
        return regex
    
    def add_template(self, template: str, variables: dict):
        if variables:
            keys = str(variables.keys())
            self.templates.loc[len(self.templates)] = [template, keys]
        else:
            self.templates.loc[len(self.templates)] = [template, '']
    
    def already_template(self, log:str) -> bool:
        for template in self.templates['template']:
            regex = self.template_to_regex(template)
            matches = re.match(regex, log, re.DOTALL)
            if matches:
                instances = matches.groups()
                self.parsed.loc[len(self.parsed)] = [log, template, instances]
                return True
        return False
        

    def parse(self, log:str):
        if self.already_template(log):
            return self.parsed[self.parse['log'] == log]
        llm_output = self.llm_parser.parse(log)
        self.add_template(llm_output['template'], llm_output['variables'])
        self.already_template(log)
        return self.parsed[self.parse['log'] == log]

if __name__ == '__main__':
    parser = SemanticLogParser()
    logs = all_datasets()
    for log in logs['log'][:10]:
        parser.parse(log)
    print(parser.parsed)
    print(parser.templates)
    parser.templates.to_csv('templates.csv', index=False)
    parser.parsed.to_csv('parsed.csv', index=False)