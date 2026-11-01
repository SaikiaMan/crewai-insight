"""Execute the pinned, unmodified upstream program with boundary test doubles.
No generated text from this module is presented as an actual LLM response.
"""
import contextlib
import io
import os
import runpy
import sys
import types
from pathlib import Path
from unittest.mock import patch

TARGET = Path(__file__).resolve().parents[1] / 'vendor/screenplay_writer'


def execute_target(spam='', dialogue='## Alice:\nHello.\n\n## Bob:\nHello.', score='8', cwd=None):
    trace = {'tasks': [], 'crew_calls': 0, 'mode': 'boundary-double'}

    class Agent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Task:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            trace['tasks'].append(self)

        def execute(self):
            return spam if self.agent.kwargs['config']['role'].strip() == 'spamfilter' else score

    class Crew:
        def __init__(self, **kwargs):
            trace['crew_config'] = kwargs

        def kickoff(self, **kwargs):
            trace['crew_calls'] += 1
            trace['kickoff_inputs'] = kwargs
            return dialogue

    crewai = types.ModuleType('crewai')
    crewai.Agent, crewai.Task, crewai.Crew = Agent, Task, Crew
    crewai.Process = types.SimpleNamespace(sequential='sequential')
    dotenv = types.ModuleType('dotenv')
    dotenv.load_dotenv = lambda: None
    old = Path.cwd()
    output = io.StringIO()
    try:
        os.chdir(cwd or TARGET)
        with patch.dict(sys.modules, {'crewai': crewai, 'dotenv': dotenv}):
            with contextlib.redirect_stdout(output):
                runpy.run_path(str(TARGET / 'screenplay_writer.py'), run_name='__main__')
    finally:
        os.chdir(old)
        trace['stdout'] = output.getvalue()
    return trace
