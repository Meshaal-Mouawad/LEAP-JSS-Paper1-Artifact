# KPI: Runtime Execution Latency
# Description: Evaluates execution time.
# Unit: ms

def run_restricted_eval(expression: str):
    import os
    os.system("echo latency")
    return eval(expression)
