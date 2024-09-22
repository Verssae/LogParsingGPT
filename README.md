# Semantic Log Parsing with Large Language Models

This repository contains the code and data for two papers **"Leveraging Prompt Engineering on Large Language Model for Semantic Log Parsing"**, and **"Enhancing Log Abstraction with Semantic Variable Naming via Large Language Models"**. The research focuses on transforming log parsing tasks into Python code generation tasks by applying prompt engineering techniques. The generated code is executed to parse log messages and verify the results in real-time, significantly improving the accuracy of semantic log parsing and abstraction.

## Overview

The primary objective of this work is to leverage LLMs to convert log messages into executable Python code. This novel approach allows for real-time validation of log parsing results, enhancing both the accuracy and semantic interpretation of log data. By framing the log parsing task as a code generation problem, LLMs are able to assign meaningful variable names and generate templates that reflect the underlying structure of log messages.

For example, given the following log message:
```
ss.bdimg.com:80 error : Could not connect to proxy proxy.cse.cuhk.edu.hk:5070 - Could not resolve proxy.cse.cuhk.edu.hk error 11001
```

The LLM generates the following Python code to parse the log message:


```python
host = 'ss.bdimg.com'
host_port = '80'
proxy = 'proxy.cse.cuhk.edu.hk'
proxy_port = '5070'
error_cde = '11001'
template = f'{host}:{host_port} error : Could not connect to proxy {proxy}:{proxy_port} - Could not resolve proxy {proxy} error {error_code}',
```
The generated code is then executed to parse the log message and validate the results. This approach significantly improves log parsing accuracy and abstraction by leveraging the capabilities of LLMs to generate and execute Python code.

## Files

- `LoGPT.py`: The main script implementing the LLM-based log parsing model. It generates Python code for parsing log messages and executes the code to ensure the parsed results match the input logs.
- `experiment.ipynb`: Jupyter notebook for running experiments, including data preprocessing, model interaction (prompt engineering), and evaluation metrics.
- `data_utils.py`: Utility functions for handling and processing log data.
- `results/`: Directory containing the results of the experiments.
- `loghub/`: Apache logs used for the experiments (from the [LogHub dataset](https://github.com/logpai/loghub)).

## Dependencies

To run the code, the following dependencies are required:

- Jupyter Notebook
- pandas
- openai

## API Key Setup

To run this project, you need to set the OpenAI API key as an environment variable. Use the following command to export your OpenAI API key before running the script:

```bash
export OPENAI_API_KEY=<your_openai_api_key>
```

Replace <your_openai_api_key> with your actual OpenAI API key.
