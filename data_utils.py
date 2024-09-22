from pathlib import Path
from pandas import DataFrame
import pandas as pd
import sqlite3
import random

base_dir=Path('./loghub')

def load_dataset(project):
    log_file = base_dir / project / f'{project}_2k.log_structured_corrected.csv'
    
    if not log_file.exists():
        raise FileNotFoundError(f'File {log_file} does not exist')
    
    # load datset from csv file with string type
    logs = pd.read_csv(log_file, dtype=str)
    logs['Project'] = project
    logs = logs[['Project', 'Content', 'EventTemplate']]
    logs.columns = ['project', 'log', 'template']
    logs['only_static'] = logs['log'] == logs['template']

    return logs

def save_dataset_to_sqlite(logs: DataFrame, db_file: Path, if_exists='append'):
    conn = sqlite3.connect(db_file)
    table_name = db_file.stem
    logs.to_sql(table_name, conn, if_exists=if_exists, index=False)
    conn.close()

def load_dataset_from_sqlite(db_file: Path):
    conn = sqlite3.connect(db_file)
    logs = pd.read_sql_query(f'SELECT * FROM {db_file.stem}', conn)
    conn.close()
    return logs

def all_projects():
    projects = [project.name for project in base_dir.iterdir() if project.is_dir()]
    return projects

def all_datasets(db_file=Path('logs.db')):
    if Path(db_file).exists():
        return load_dataset_from_sqlite(db_file)
    
    for project in all_projects():
        save_dataset_to_sqlite(load_dataset(project), db_file, if_exists='append')

    return load_dataset_from_sqlite(db_file)

def dataset(project):
    df = load_dataset(project)
    df = df[['log', 'template']]
    df = df.groupby('template').agg({'log': list}).reset_index()
    df['num_variables'] = df['template'].apply(lambda x: x.count('<*>'))
    df['is_static'] = df['num_variables'] == 0
    df.columns = ['template', 'logs', 'num_variables', 'is_static']
    df['random_log'] = df['logs'].apply(lambda x: random.choice(x))
    return df

if __name__ == '__main__':
    logs = all_datasets()
    print(len(logs))
    print(logs.index[0])
    # logs = load_dataset('Android')
    # print(len(logs))
    # save_dataset_to_sqlite(logs, 'logs.db', if_exists='replace')
    # logs = load_dataset_from_sqlite('logs.db')
    # print(len(logs))
