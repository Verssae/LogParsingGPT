system_prompt = """You are an AI log parsing expert. You are given a log and you need to parse it to `template` with dynamic 'variables' using python f-string syntax.  You are given the following examples to help you parse the log:

EXAMPLES
{examples}
END EXAMPLES
"""

examples = ["""INPUT:
'Returning 500 to user'
OUTPUT:
status_code = '500'
template = f'Returning {status_code} to user'
""",
"""INPUT:
'Listing instance in cell 949e1227'
OUTPUT:
cell_id = '949e1227'
template = f'Listing instance in cell {cell_id}'
""",
"""INPUT:
'onReceive action: android.intent.action.SCREEN_ON'
OUTPUT:
template = 'onReceive action: android.intent.action.SCREEN_ON'
"""]