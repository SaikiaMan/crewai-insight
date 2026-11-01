"""Version compatibility facade; leaves target prompts/control flow unchanged.
Only the hard-coded discussion assignment is replaced to feed a dataset premise.
Task.execute -> execute_sync; CrewOutput -> raw; verbose=2 -> True.
"""
import ast
import contextlib
import io
import importlib.metadata
import platform
import json
import os
from pathlib import Path
import sys
import types
import traceback
from unittest.mock import patch
from qa.gemini import DEFAULT_MODEL, model_name, target_llm, total_tokens


def execute(trace):
    import crewai as real
    real_llm = real.LLM  # Save before the vendor import facade replaces crewai.
    from qa.target import TARGET
    case = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    trace['crewai_version'] = importlib.metadata.version('crewai')
    trace['dependencies'] = {name: importlib.metadata.version(name)
                             for name in ('crewai', 'litellm', 'pydantic', 'python-dotenv')}
    agents = []

    def Agent(**kwargs):
        kwargs['llm'] = target_llm(trace['provider_calls'], real_llm)
        kwargs['max_retry_limit'] = 0  # Transport owns bounded retries.
        agent = real.Agent(**kwargs)
        agents.append(agent)
        return agent

    class Task:
        def __init__(self, **kwargs):
            role = kwargs['agent'].role
            def completed(output):
                trace['events'].append({'event': 'task_end', 'role': role, 'raw': output.raw})
            self.inner = real.Task(**kwargs, callback=completed)
            trace['tasks'].append({'description': kwargs['description'], 'role': kwargs['agent'].role})

        def execute(self):
            trace['events'].append({'event': 'standalone_start', 'role': self.inner.agent.role})
            result = self.inner.execute_sync()
            trace['events'].append({'event': 'standalone_end', 'role': self.inner.agent.role, 'raw': result.raw})
            return result.raw

    class Crew:
        def __init__(self, **kwargs):
            kwargs['tasks'] = [t.inner for t in kwargs['tasks']]
            kwargs['verbose'] = bool(kwargs['verbose'])
            self.inner = real.Crew(**kwargs)

        def kickoff(self):
            trace['crew_calls'] += 1
            result = self.inner.kickoff()
            trace['dialogue_before_cleanup'] = result.raw
            return result.raw

    facade = types.ModuleType('crewai')
    facade.LLM = real_llm
    facade.Agent, facade.Task, facade.Crew, facade.Process = Agent, Task, Crew, real.Process
    source = (TARGET/'screenplay_writer.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'discussion' for t in node.targets):
            node.value = ast.Constant(case['premise'])
    ast.fix_missing_locations(tree)
    logs = io.StringIO()
    old = Path.cwd()
    try:
        os.chdir(TARGET)
        with patch.dict(sys.modules, {'crewai': facade}), contextlib.redirect_stdout(logs):
            namespace = {'__name__': '__main__', '__file__': str(TARGET/'screenplay_writer.py')}
            exec(compile(tree, str(TARGET/'screenplay_writer.py'), 'exec'), namespace)
        trace['dialogue'] = namespace['result']
        trace['score'] = namespace['score']
    except Exception as exc:
        trace['error'] = f'{type(exc).__name__}: {exc}'
        trace['traceback'] = traceback.format_exc()
    finally:
        os.chdir(old)
        trace['stdout'] = logs.getvalue()
        trace['total_tokens'] = total_tokens(trace['provider_calls'])
        trace['token_usage_scope'] = 'completed provider responses; may be partial on execution failure'

    return 1 if 'error' in trace else 0


def main():
    # Capture bootstrap/import failures as well as failures inside the target.
    destination = Path(sys.argv[2])
    trace = {'mode': 'live-compatibility', 'events': [], 'tasks': [], 'crew_calls': 0,
             'python': platform.python_version(), 'python_executable': sys.executable,
             'provider': 'gemini', 'provider_calls': [],
             'target_model': os.environ.get('TARGET_MODEL', DEFAULT_MODEL),
             'judge_model': os.environ.get('JUDGE_MODEL', DEFAULT_MODEL)}
    try:
        model_name('TARGET_MODEL')
        model_name('JUDGE_MODEL')
        execute(trace)
    except Exception as exc:
        trace['error'] = f'{type(exc).__name__}: {exc}'
        trace['traceback'] = traceback.format_exc()
    destination.write_text(json.dumps(trace, indent=2), encoding='utf-8')
    if 'traceback' in trace:
        print(trace['traceback'], file=sys.stderr)
    return 1 if 'error' in trace else 0


if __name__ == '__main__':
    raise SystemExit(main())
