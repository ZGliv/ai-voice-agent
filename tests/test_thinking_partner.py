"""Thinking-partner mode: which brain answers, web search only when needed, project context, whole-call memory."""
import json, sys, tempfile, threading, time, types, unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
import companion as c
import brain, deep, phone

class Speech:
    """Stands in for the Fish voice stream: records the text and leaves a short audio clip, as a real reply would."""
    def __init__(self,directory,*a,**k):self.directory=Path(directory);self.fed=[]
    def feed(self,text):self.fed.append(text)
    def finish(self,text):self.fed.append(text)
    def close(self):pass
    def wait(self):
        import wave
        with wave.open(str(self.directory/'reply.pending.wav'),'wb') as w:w.setparams((1,2,24000,0,'NONE','not compressed'));w.writeframes(b'\x10\x10'*4800)
        return {'first_audio':0.1}

class RoutingTests(unittest.TestCase):
    def setUp(self):
        catalog=patch('project_memory.catalog',return_value=[{'id':'parl-ai','name':'Parl.ai'}]);catalog.start();self.addCleanup(catalog.stop)
        self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.CURRENT=None;c.STOP.clear();c.initialize()
        self.cid=phone.new_conversation(c,'Phone call');self.deep_calls=[];self.small_calls=[]
    def tearDown(self):c.DATA=self.old;self.temp.cleanup()

    def ask(self,text,deep_reply='A considered answer.',small_reply='SAY\nQuick answer.',deep_error=None):
        with patch.object(c,'launch'):item=c.create_turn(self.cid,text=text)
        def big(data,system,messages,stop,on_text,meter=None):
            self.deep_calls.append({'system':system,'messages':messages})
            if deep_error:raise deep_error
            if deep_reply!='TOOLS':on_text(deep_reply)
            if meter is not None:meter['deep']={'model':'claude-sonnet-5-5','searches':0}
            return deep_reply
        def small(data,payload,stop,on_text,meter=None):
            self.small_calls.append(payload);reply=small_reply if isinstance(small_reply,str) else small_reply.pop(0)
            if isinstance(reply,dict):return reply
            on_text(reply);return {'role':'assistant','content':reply}
        with patch('fish_voice.key',return_value='k'),patch('fish_text_stream.available',return_value=True),patch('fish_text_stream.TextSpeech',Speech),\
             patch('phone.cached',return_value=None),patch.object(deep,'available',return_value=True),patch.object(deep,'chat',side_effect=big),patch('brain.chat',side_effect=small):
            c.CURRENT=item['id'];c.work(item['id'])
        return c.turn(item['id'])

    def test_thinking_out_loud_goes_straight_to_the_bigger_model(self):
        done=self.ask("Let's talk through Parl.ai pricing. Should I go paid-only?")
        self.assertEqual(done['output_text'],'A considered answer.');self.assertEqual(self.small_calls,[])
        self.assertIn('Project under discussion: Parl.ai',self.deep_calls[0]['system'])   # it knows which project he means

    def test_the_conversation_stays_with_the_bigger_model_until_he_asks_for_something(self):
        self.ask("What do you think about charging twenty dollars?")
        done=self.ask("Hmm, and if nobody converts?")            # no trigger words: still the same discussion
        self.assertEqual(done['output_text'],'A considered answer.');self.assertEqual(len(self.deep_calls),2);self.assertEqual(self.small_calls,[])
        self.assertEqual(self.deep_calls[1]['messages'][-3]['content'],'What do you think about charging twenty dollars?')
        tool=[{'role':'assistant','content':'','tool_calls':[{'id':'1','function':{'name':'speak_response','arguments':{}}}]},'Reminder noted.']
        self.ask("Remind me tomorrow to email Sam.",small_reply=tool)
        self.assertEqual(len(self.deep_calls),2);self.assertTrue(self.small_calls)   # an action goes to the tool route, not the talker

    def test_quick_questions_stay_on_the_fast_model_and_the_router_can_hand_up(self):
        done=self.ask("What's two plus two?")
        self.assertEqual(done['output_text'],'Quick answer.');self.assertEqual(self.deep_calls,[])
        self.assertIn('DEEP',self.small_calls[0]['messages'][0]['content'])       # the router is told it may hand up
        done=self.ask("Is nuclear power actually safe?",small_reply='DEEP')
        self.assertEqual(done['output_text'],'A considered answer.');self.assertEqual(len(self.deep_calls),1)

    def test_bigger_model_hands_actions_back_and_failures_fall_back(self):
        done=self.ask("What do you think, can you sort that out for me?",deep_reply='TOOLS')
        self.assertEqual(done['output_text'],'Quick answer.');self.assertTrue(done['timings']['deep_handed_back'])
        self.assertNotIn('Output only DEEP',self.small_calls[0]['messages'][0]['content'])   # no ping-pong back up
        self.small_calls.clear()
        done=self.ask("Should I learn Rust or Go?",deep_error=brain.CloudError('529 overloaded'))
        self.assertEqual(done['status'],'complete');self.assertEqual(done['output_text'],'Quick answer.');self.assertIn('overloaded',done['timings']['deep_failed'])

    def test_whole_call_is_remembered(self):
        for n in range(12):
            with c.connect() as db:db.execute("INSERT INTO turns(id,conversation_id,source,status,input_text,output_text,created,updated) VALUES(?,?,'text','complete',?,?,?,?)",(f't{n}',self.cid,f'point {n}',f'reply {n}',time.time()-100+n,time.time()))
        self.ask("What do you think overall?")
        said=[m['content'] for m in self.deep_calls[0]['messages']]
        self.assertIn('point 0',said);self.assertIn('point 11',said)   # more than the old eight exchanges

class ProjectTests(unittest.TestCase):
    def test_most_recently_named_project_wins_and_small_talk_names_none(self):
        catalog=[{'id':'parl-ai','name':'Parl.ai'},{'id':'parl-ai-markets-x','name':'Parl.ai Markets'},{'id':'map-of-knowledge','name':'Map of Knowledge'}]
        with patch('project_memory.catalog',return_value=catalog):
            self.assertEqual(deep.mentioned_project(["what about parlay pricing"])['id'],'parl-ai')
            self.assertEqual(deep.mentioned_project(["and the Parl.ai Markets terminal?"])['id'],'parl-ai-markets-x')
            self.assertEqual(deep.mentioned_project(["hmm okay","back to the map of knowledge game","parl.ai earlier"])['id'],'map-of-knowledge')
            self.assertIsNone(deep.mentioned_project(["how are you doing tonight"]))

class Stream:
    """Stands in for client.beta.messages.stream(...): yields scripted events, then a final message."""
    def __init__(self,events,stop_reason='end_turn'):self.events=events;self.stop_reason=stop_reason
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def __iter__(self):return iter(self.events)
    def get_final_message(self):
        return NS(stop_reason=self.stop_reason,content=[],model='claude-sonnet-5-5',usage=NS(input_tokens=5,output_tokens=9,cache_read_input_tokens=0))

def text(*pieces):
    return [NS(type='content_block_start',content_block=NS(type='text'))]+[NS(type='content_block_delta',delta=NS(type='text_delta',text=p)) for p in pieces]
SEARCH_STEP=[NS(type='content_block_start',content_block=NS(type='server_tool_use'))]

class ChatTests(unittest.TestCase):
    def run_chat(self,scripts,question):
        requests=[]
        class Messages:
            def stream(_,**kwargs):requests.append(kwargs);return scripts.pop(0)
        fake=types.ModuleType('anthropic');fake.APIError=type('APIError',(Exception,),{})
        fake.Anthropic=lambda **k:NS(beta=NS(messages=Messages()))
        heard=[];deep.CLIENTS.clear();self.addCleanup(deep.CLIENTS.clear)
        with patch.dict(sys.modules,{'anthropic':fake}),patch('brain.config',return_value={'key':'k','base_url':'https://api.anthropic.com/v1','model':'claude-haiku-5-5'}):
            out=deep.chat(Path('.'),'SYSTEM',[{'role':'user','content':question}],threading.Event(),heard.append,{})
        return out,heard,requests

    def test_plain_discussion_uses_no_tools_and_no_pre_answer_thinking(self):
        out,heard,requests=self.run_chat([Stream(text('Stay ','free.'))],'Should Parl.ai stay free?')
        self.assertEqual(out,'Stay free.');self.assertEqual(heard,['Stay ','Stay free.'])
        self.assertNotIn('tools',requests[0]);self.assertEqual(requests[0]['thinking'],{'type':'between_tools'})
        self.assertEqual(requests[0]['fallbacks'],'default')

    def test_search_happens_only_when_the_model_asks_and_control_words_are_never_spoken(self):
        out,heard,requests=self.run_chat([Stream(text('SEA','RCH')),Stream(text('Let me check. ')+SEARCH_STEP+text('It is 899 dollars.'))],'What is a good price for a small desktop?')
        self.assertEqual(out,'Let me look that up. It is 899 dollars.')
        self.assertNotIn('SEARCH',''.join(heard));self.assertNotIn('Let me check',out)   # his own lead-in is not repeated
        self.assertNotIn('tools',requests[0]);self.assertEqual(requests[1]['tools'][0]['type'],'web_search_20250305')

    def test_obvious_web_question_searches_at_once(self):
        out,heard,requests=self.run_chat([Stream(SEARCH_STEP+text('Rain by six.'))],"What's the latest news on the storm?")
        self.assertEqual(heard[0],'Let me look that up. ');self.assertEqual(len(requests),1);self.assertIn('tools',requests[0])

    def test_action_requests_come_back_as_tools_without_a_word_spoken(self):
        out,heard,_=self.run_chat([Stream(text('TOO','LS'))],'Can you check my email?')
        self.assertEqual((out,heard),('TOOLS',[]))

if __name__=='__main__':unittest.main()
