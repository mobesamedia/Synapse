"""DeepSeek contract tests with fake credentials and a local SSE fixture."""
import ast
import io
import json
from pathlib import Path
import socket
import threading
import typing
from types import SimpleNamespace
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'ai_assistant.py'


def load():
    tree = ast.parse(SOURCE.read_text())
    names = {'_stream_openai_compat', '_run_api_in_thread', '_classify_error',
             '_load_settings', '_save_settings_dict', '_is_configured'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    constants = [n for n in tree.body if isinstance(n, ast.Assign) and
                 any(isinstance(t, ast.Name) and (t.id.startswith('CK_') or t.id in
                     {'_PFX', '_SECRET_KEYS', '_ALLOWED_URLS'}) for t in n.targets)]
    env = dict(vars(typing), constants=SimpleNamespace(ADDON_NAME_LAUNCHER="test"), json=json, urllib=urllib, socket=socket, threading=threading,
               _=lambda s: s, OLLAMA_EP_DEFAULT='http://localhost:11434',
               LLAMA_EP_DEFAULT='http://localhost:8080', DEFAULT_OWN_PROMPT='',
               _DEFAULT_CHIPS={}, _detect_night_mode=lambda: False,
               _get_theme_accent=lambda _: '#123456', _web_translations=lambda _: {},
               _session_generation=1, _conversation=[], _normalize_model=lambda s:s,
               _trim_conversation=lambda:None)
    exec(compile(ast.Module(body=constants+nodes, type_ignores=[]), str(SOURCE), 'exec'), env)
    return env


class DeepSeekTests(unittest.TestCase):
    def test_settings_and_secret_registration(self):
        e=load(); cfg={}; e['_cfg_get']=lambda k,d=None:cfg.get(k,d); e['_cfg_set']=cfg.__setitem__
        e['_save_settings_dict']({'provider':'deepseek','apiKey':' test-key ','model':'deepseek-flash'})
        saved=e['_load_settings']()
        self.assertEqual((saved['provider'],saved['apiKey'],saved['model']),('deepseek','test-key','deepseek-flash'))
        self.assertTrue(saved['isConfigured'])
        self.assertIn(e['CK_KEY_DEEPSEEK'], e['_SECRET_KEYS'])
        self.assertIn('https://platform.deepseek.com/api_keys',e['_ALLOWED_URLS'])
        self.assertNotIn(e['CK_KEY_OPENAI'],cfg)

    def test_stream_request_and_conversation(self):
        e=load(); js=[]; e['_js_on_main']=lambda s,g:js.append(s)
        class InlineThread:
            def __init__(self,target,**kw):self.target=target
            def start(self):self.target()
        lines=[b': keep-alive\n']+[('data: '+json.dumps({'choices':[{'delta':delta}]})+'\n').encode() for delta in
                                  [{'reasoning_content':'Think'}, {'content':'Hello '},{'content':'world'}]]+[b'data: [DONE]\n']
        messages=[{'role':'system','content':'Help me study'},{'role':'user','content':'Hello'}]
        with patch.object(threading,'Thread',InlineThread), patch.object(urllib.request,'urlopen',return_value=io.BytesIO(b''.join(lines))) as mock:
            e['_run_api_in_thread']({'provider':'deepseek','apiKey':'test-key','model':'deepseek-flash'},messages)
        req=mock.call_args.args[0]; body=json.loads(req.data)
        self.assertEqual(req.full_url,'https://api.deepseek.com/chat/completions')
        self.assertEqual(req.get_header('Authorization'),'Bearer test-key')
        self.assertEqual(body,dict(model='deepseek-flash',messages=messages,stream=True))
        self.assertEqual(mock.call_args.kwargs['timeout'],180)
        self.assertEqual(e['_conversation'],[{'role':'assistant','content':'Hello world'}])
        self.assertTrue(any('appendThinking' in x for x in js))
        self.assertIn('finalizeResponse();',js)

    def test_other_provider_budget_unchanged(self):
        e=load()
        with patch.object(urllib.request,'urlopen',return_value=io.BytesIO(b'data: [DONE]\n')) as mock:
            e['_stream_openai_compat']('https://example.com/chat','test','model',[],lambda _:None,token_param='max_completion_tokens')
        self.assertEqual(json.loads(mock.call_args.args[0].data)['max_completion_tokens'],2048)

    def test_balance_and_key_errors(self):
        e=load()
        for code,expected in [(402,'No API credit'),(401,'Invalid API key'),(429,'Request limit')]:
            err=urllib.error.HTTPError('https://api.deepseek.com',code,'error',{},io.BytesIO(b'{}'))
            self.assertIn(expected,e['_classify_error'](err,'deepseek'))


if __name__=='__main__':unittest.main()
