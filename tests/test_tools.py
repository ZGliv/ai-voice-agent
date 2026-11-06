import json, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch
import companion as c
import companion_tools as tools
import codex_jobs as jobs

class ToolTests(unittest.TestCase):
 def setUp(self):
  catalog_patch=patch('project_memory.catalog',return_value=[]);catalog_patch.start();self.addCleanup(catalog_patch.stop)
  self.temp=tempfile.TemporaryDirectory();self.old=c.DATA;c.DATA=Path(self.temp.name);c.CURRENT=None;c.STOP.clear();c.initialize()
  with c.connect() as db:
   db.execute('INSERT INTO conversations VALUES(?,?,?,?)',('a'*32,'Test',time.time(),time.time()))
   db.execute('INSERT INTO conversation_projects VALUES(?,?)',('a'*32,'test'))
  with patch.object(c,'launch'):self.item=c.create_turn('a'*32,text='Remember this decision: keep speech local.')
 def tearDown(self):c.DATA=self.old;self.temp.cleanup()
 def test_save_is_idempotent_across_retry(self):
  for _ in range(2):result=tools.execute(c,self.item,'save_memory',{'kind':'decision','content':'Keep speech local.'})
  with c.connect() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM project_memory').fetchone()[0],1)
   self.assertEqual(db.execute('SELECT source_turn_id FROM project_memory').fetchone()[0],self.item['id'])
 def test_unscoped_memory_rejected(self):
  with c.connect() as db:db.execute('DELETE FROM conversation_projects')
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'save_memory',{'kind':'decision','content':'Test'})
 def test_invalid_memory_rejected(self):
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'save_memory',{'kind':'shell','content':'Test'})
 def test_job_needs_allowlisted_project(self):
  with self.assertRaises(c.Problem):jobs.draft(c,'/tmp','Do something','x')
 def test_job_only_drafts_and_deduplicates(self):
  with patch.object(jobs,'projects',return_value={'test':'/tmp'}),patch.object(jobs.subprocess,'Popen') as spawn:
   a=tools.execute(c,self.item,'prepare_codex_job',{'task':'Inspect the README and report.'})
   b=tools.execute(c,self.item,'prepare_codex_job',{'task':'Inspect the README and report.'})
  self.assertEqual(a['id'],b['id']);self.assertEqual(a['status'],'draft');spawn.assert_not_called()
 def test_restart_marks_jobs_interrupted(self):
  with patch.object(jobs,'projects',return_value={'test':'/tmp'}):job=jobs.draft(c,'test','Inspect README','x')
  jobs.update(c,job['id'],status='running');c.initialize()
  self.assertEqual(jobs.list_jobs(c)[0]['status'],'interrupted')
 def test_unknown_tool_rejected(self):
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'execute_shell',{'command':'echo hi'})

 def test_job_captures_memory_snapshot(self):
  tools.execute(c,self.item,'save_memory',{'kind':'decision','content':'Keep speech local.'})
  with patch.object(jobs,'projects',return_value={'test':'/tmp'}):job=jobs.draft(c,'test','Inspect README',None)
  with c.connect() as db:db.execute("UPDATE project_memory SET content='Changed later'")
  self.assertIn('Keep speech local.',job['context']);self.assertNotIn('Changed later',job['context'])

 def test_runner_sends_snapshot_and_uses_sandbox(self):
  import io
  from unittest.mock import Mock
  class Input(io.StringIO):
   def close(self):pass
  tools.execute(c,self.item,'save_memory',{'kind':'next_step','content':'Keep the interface minimal.'})
  with patch.object(jobs,'projects',return_value={'test':'/tmp'}):job=jobs.draft(c,'test','Inspect README',None)
  jobs.update(c,job['id'],status='running')
  d=c.DATA/'jobs'/job['id'];d.mkdir(parents=True);(d/'result.txt').write_text('Inspected.')
  process=Mock();process.stdin=Input();process.stdout=iter([]);process.returncode=0
  with patch.object(jobs,'make_workspace',return_value=d/'workspace'),patch.object(jobs,'read_preview',return_value=None),patch.object(jobs.subprocess,'Popen',return_value=process) as spawn:jobs.run(c,job,'/tmp')
  command=spawn.call_args.args[0]
  self.assertEqual(command[command.index('--cd')+1],str(d/'workspace'));self.assertIn('workspace-write',command)
  self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',command)
  self.assertIn('Keep the interface minimal.',process.stdin.getvalue())
  self.assertEqual(jobs.list_jobs(c)[0]['status'],'completed')

 def test_spoken_site_build_does_not_need_project_or_button(self):
  with c.connect() as db:db.execute('DELETE FROM conversation_projects')
  with patch.object(jobs,'launch_site',return_value={'id':'b'*32,'status':'preparing'}) as launch:
   result=tools.execute(c,self.item,'build_website',{'task':'Build a working focus timer website'})
  launch.assert_called_once_with(c,'Build a working focus timer website',self.item['id'])
  self.assertEqual(result['status'],'preparing')
 def test_unknown_project_cannot_start(self):
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'start_codex_job',{'task':'Build a website'})
 def test_live_progress_is_real_event_data(self):
  with patch.object(jobs,'projects',return_value={'test':'/tmp'}):job=jobs.draft(c,'test','Inspect README',None)
  jobs.consume_event(c,job['id'],{'type':'item.completed','item':{'type':'agent_message','text':'Read the actual README.'}})
  self.assertEqual(json.loads(jobs.get_job(c,job['id'])['progress'])[-1]['text'],'Read the actual README.')

 def test_research_does_not_require_project_and_deduplicates(self):
  with c.connect() as db:db.execute('DELETE FROM conversation_projects')
  job=jobs.draft(c,'__research__','Compare public speech API options',self.item['id'])
  jobs.update(c,job['id'],status='completed',result='A sourced comparison.')
  with patch.object(jobs,'launch_research',return_value=jobs.get_job(c,job['id'])) as launch:
   first=tools.execute(c,self.item,'research_task',{'task':'Compare public speech API options'})
   second=tools.execute(c,self.item,'research_task',{'task':'Compare public speech API options'})
  self.assertEqual(first['id'],second['id']);launch.assert_called_once()
  report=tools.execute(c,self.item,'read_job_result',{'job_id':first['id']})
  self.assertEqual(report['result'],'A sourced comparison.')

 def test_research_workspace_and_prompt_have_public_source_boundaries(self):
  job=jobs.draft(c,'__research__','Find current facts and cite sources',None)
  workspace=jobs.make_workspace(c,job,None)
  instructions=(workspace/'AGENTS.md').read_text()
  self.assertIn('public web sources',instructions);self.assertIn('Never invent sources',instructions)
  self.assertNotIn('Build the requested website',instructions)

 def test_active_job_is_not_hidden_by_newer_drafts(self):
  first=jobs.draft(c,'__research__','Research first',None);jobs.update(c,first['id'],status='running')
  for _ in range(41):last=jobs.draft(c,'__research__','Research later',None)
  with self.assertRaises(c.Problem) as error:jobs.start_job(c,last['id'])
  self.assertEqual(error.exception.status,409)

 def test_followup_copies_actual_uncommitted_work_and_preserves_parent(self):
  parent=jobs.draft(c,'__new_site__','Build a timer',None);workspace=jobs.make_workspace(c,parent,None)
  (workspace/'site').mkdir();(workspace/'site/index.html').write_text('Original actual work')
  (workspace/'.env').write_text('secret');(workspace/'linked.html').symlink_to(workspace/'site/index.html')
  (workspace/'.jarvis-preview.json').write_text('{"directory":"site"}')
  jobs.update(c,parent['id'],status='completed')
  child=jobs.draft(c,'__new_site__','Change the title',None,parent_id=parent['id']);copy=jobs.make_workspace(c,child,None)
  self.assertEqual((copy/'site/index.html').read_text(),'Original actual work')
  (copy/'site/index.html').write_text('Revised')
  self.assertEqual((workspace/'site/index.html').read_text(),'Original actual work')
  self.assertFalse((copy/'.env').exists());self.assertFalse((copy/'linked.html').exists());self.assertFalse((copy/'.jarvis-preview.json').exists())
  self.assertTrue((copy/'.jarvis-copy-notes.txt').exists());self.assertEqual(child['parent_id'],parent['id'])

 def test_followup_rejects_running_or_missing_workspace(self):
  parent=jobs.draft(c,'__new_site__','Build a timer',None);jobs.update(c,parent['id'],status='running')
  with self.assertRaises(c.Problem):jobs.draft(c,'__new_site__','Revise timer',None,parent_id=parent['id'])
  jobs.update(c,parent['id'],status='completed')
  with self.assertRaises(c.Problem):jobs.draft(c,'__new_site__','Revise timer',None,parent_id=parent['id'])

 def test_followup_tool_uses_followup_runner_not_research(self):
  parent=jobs.draft(c,'__new_site__','Build a timer',None)
  tools.execute(c,self.item,'job_status',{})
  with patch.object(jobs,'continue_job',return_value={'id':'c'*32,'status':'preparing'}) as follow,patch.object(jobs,'launch_research') as research:
   result=tools.execute(c,self.item,'continue_job',{'job_id':parent['id'],'task':'Change the title'})
  follow.assert_called_once_with(c,parent['id'],'Change the title',self.item['id']);research.assert_not_called();self.assertEqual(result['status'],'preparing')

 def test_saved_workspace_symlink_cannot_redirect_followup(self):
  parent=jobs.draft(c,'__new_site__','Build a timer',None);workspace=jobs.make_workspace(c,parent,None)
  outside=c.DATA/'outside';workspace.rename(outside);workspace.symlink_to(outside,target_is_directory=True)
  jobs.update(c,parent['id'],status='completed')
  with self.assertRaises(c.Problem):jobs.draft(c,'__new_site__','Revise timer',None,parent_id=parent['id'])

 def test_selected_private_preview_restores_from_validated_job(self):
  parent=jobs.draft(c,'__new_site__','Build a timer',None);workspace=jobs.make_workspace(c,parent,None)
  (workspace/'site').mkdir();(workspace/'site/index.html').write_text('Saved preview')
  (workspace/'.jarvis-preview.json').write_text('{"directory":"site"}')
  jobs.update(c,parent['id'],status='completed');(c.DATA/'selected-preview').write_text(parent['id'])
  try:
   jobs.site_preview.configure_remote('https://preview.example:8443',port=0)
   self.assertTrue(jobs.restore_remote_preview(c));self.assertEqual(jobs.site_preview.REMOTE_ROOT,(workspace/'site').resolve())
   (c.DATA/'selected-preview').write_text('../not-a-job');self.assertFalse(jobs.restore_remote_preview(c))
  finally:jobs.site_preview.shutdown()

 def test_voice_cancel_requires_fresh_job_identification(self):
  job=jobs.draft(c,'__new_site__','Build a timer.',None)
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'cancel_job',{'job_id':job['id']})
  self.assertEqual(jobs.get_job(c,job['id'])['status'],'draft')
  tools.execute(c,self.item,'job_status',{})
  result=tools.execute(c,self.item,'cancel_job',{'job_id':job['id']})
  self.assertEqual(result['status'],'cancelled');self.assertTrue(result['files_preserved'])
  self.assertEqual(tools.execute(c,self.item,'cancel_job',{'job_id':job['id']})['status'],'cancelled')

 def test_voice_cancel_preserves_completed_job_and_unknown_ids(self):
  job=jobs.draft(c,'__new_site__','Build a timer.',None);jobs.update(c,job['id'],status='completed',result='Saved result')
  tools.execute(c,self.item,'job_status',{})
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'cancel_job',{'job_id':'f'*32})
  result=tools.execute(c,self.item,'cancel_job',{'job_id':job['id']})
  self.assertEqual(result['status'],'completed');self.assertEqual(jobs.get_job(c,job['id'])['result'],'Saved result')

 def test_cancel_stops_registered_process_and_preserves_workspace(self):
  from unittest.mock import Mock
  job=jobs.draft(c,'__new_site__','Build a timer.',None);jobs.update(c,job['id'],status='running')
  folder=c.DATA/'jobs'/job['id']/'workspace';folder.mkdir(parents=True);(folder/'work.txt').write_text('Keep me')
  process=Mock();jobs.PROCESSES[job['id']]=process
  try:
   with patch.object(jobs,'terminate') as terminate:
    result=jobs.cancel_job(c,job['id']);terminate.assert_called_once_with(process)
   self.assertEqual(result['status'],'cancelled');self.assertEqual((folder/'work.txt').read_text(),'Keep me')
  finally:jobs.PROCESSES.pop(job['id'],None)

 def test_status_verification_is_compact_and_keeps_failures(self):
  report={'status':'failed','summary':'Checks failed','repair':{'attempts':1},'runs':[{'viewport':'mobile','checks':[{'name':'Reset','passed':False,'error':'Wrong time'}]*30}]}
  brief=tools.verification_brief(json.dumps(report))
  self.assertEqual(brief['repair_attempts'],1);self.assertEqual(len(brief['failures']),4);self.assertEqual(brief['failures'][0]['error'],'Wrong time')

 def test_next_step_completion_and_reopening_preserve_content(self):
  note=tools.execute(c,self.item,'save_memory',{'kind':'next_step','content':'Test phone playback.'})
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'set_next_step_status',{'memory_id':note['id'],'status':'done'})
  tools.execute(c,self.item,'read_memory',{})
  for status in ['done','done','open']:
   result=tools.execute(c,self.item,'set_next_step_status',{'memory_id':note['id'],'status':status})
   self.assertEqual(result['status'],status);self.assertEqual(result['content'],note['content']);self.assertEqual(result['source_turn_id'],note['source_turn_id'])

 def test_decisions_and_other_projects_cannot_be_completed(self):
  note=tools.execute(c,self.item,'save_memory',{'kind':'decision','content':'Use the local Mac.'})
  tools.execute(c,self.item,'read_memory',{})
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'set_next_step_status',{'memory_id':note['id'],'status':'done'})
  with c.connect() as db:db.execute("UPDATE project_memory SET kind='next_step',project_id='another' WHERE id=?",(note['id'],))
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'set_next_step_status',{'memory_id':note['id'],'status':'done'})

 def test_memory_search_is_bounded_and_finds_older_items(self):
  with c.connect() as db:
   for i in range(35):db.execute('INSERT INTO project_memory VALUES(?,?,?,?,?,?,?,?)',(str(i),'test','next_step',f'Task {i}','open',None,'',i))
  result=tools.execute(c,self.item,'read_memory',{})
  self.assertEqual(len(result['memory']),30);self.assertTrue(result['has_more'])
  result=tools.execute(c,self.item,'read_memory',{'query':'Task 0'})
  self.assertEqual(result['matching_count'],1);self.assertEqual(result['memory'][0]['content'],'Task 0')

 def test_unmatched_memory_search_labels_recent_candidates(self):
  note=tools.execute(c,self.item,'save_memory',{'kind':'next_step','content':'Test phone playback.'})
  result=tools.execute(c,self.item,'read_memory',{'query':'unrelated invoicing'})
  self.assertEqual(result['matching_count'],0);self.assertEqual(result['search_mode'],'recent_candidates_no_exact_match');self.assertEqual(result['memory'][0]['id'],note['id'])

 def test_voice_preview_identifies_job_and_deduplicates_open(self):
  job=jobs.draft(c,'__new_site__','Build a timer.',None);jobs.update(c,job['id'],status='completed')
  with patch.object(jobs,'read_preview',return_value='http://127.0.0.1:9999/'),patch.object(jobs,'open_on_mac') as opened:
   with self.assertRaises(c.Problem):tools.execute(c,self.item,'open_job_preview',{'job_id':job['id']})
   opened.assert_not_called();tools.execute(c,self.item,'job_status',{})
   for _ in range(2):result=tools.execute(c,self.item,'open_job_preview',{'job_id':job['id']})
   opened.assert_called_once_with('http://127.0.0.1:9999/');self.assertTrue(result['opening_requested'])

 def test_preview_never_opens_running_jobs_or_missing_sites(self):
  job=jobs.draft(c,'__new_site__','Build a timer.',None)
  with patch.object(jobs,'open_on_mac') as opened:
   with self.assertRaises(c.Problem):jobs.open_preview(c,job['id'])
   jobs.update(c,job['id'],status='completed')
   with patch.object(jobs,'read_preview',return_value=None):
    with self.assertRaises(c.Problem):jobs.open_preview(c,job['id'])
   opened.assert_not_called()

 def test_job_search_reaches_beyond_recent_forty(self):
  old=jobs.draft(c,'__new_site__','Build a hockey roster website.',None)
  for i in range(45):jobs.draft(c,'__new_site__',f'Build unrelated page number {i}.',None)
  self.assertNotIn(old['id'],[j['id'] for j in jobs.list_jobs(c)])
  result=tools.execute(c,self.item,'job_status',{'query':'hockey roster'})
  self.assertEqual([j['id'] for j in result['jobs']],[old['id']]);self.assertFalse(result['has_more'])
  self.assertTrue(tools.execute(c,self.item,'job_status',{})['has_more'])

 def test_job_search_treats_wildcards_and_sql_as_literal(self):
  jobs.draft(c,'__new_site__','Build a useful website.',None)
  for query in ['%',"' OR 1=1 --",'_missing_']:
   self.assertEqual(jobs.search_jobs(c,query)['jobs'],[])
  with self.assertRaises(c.Problem):jobs.search_jobs(c,'x'*161)
  with self.assertRaises(c.Problem):jobs.search_jobs(c,'word '*9)

 def test_project_can_be_selected_after_unscoped_greeting(self):
  with c.connect() as db:
   db.execute('DELETE FROM conversation_projects')
   db.execute('INSERT INTO turns(id,conversation_id,source,status,input_text,created,updated) VALUES(?,?,?,?,?,?,?)',('f'*32,'a'*32,'text','complete','Good morning',1,1))
  with patch('project_memory.catalog',return_value=[{'id':'one','name':'One'},{'id':'two','name':'Two'}]):
   result=tools.execute(c,self.item,'select_project',{'project_id':'one'});self.assertEqual(result['selected_project']['id'],'one')
   self.assertEqual(tools.execute(c,self.item,'select_project',{'project_id':'one'})['selected_project']['id'],'one')
   with self.assertRaises(c.Problem):tools.execute(c,self.item,'select_project',{'project_id':'two'})
  with c.connect() as db:
   self.assertEqual(db.execute('SELECT project_id FROM conversation_projects').fetchone()[0],'one')
   self.assertEqual(db.execute('SELECT input_text FROM turns WHERE id=?',('f'*32,)).fetchone()[0],'Good morning')

 def test_select_project_bounds_memory_context(self):
  with c.connect() as db:
   db.execute('DELETE FROM conversation_projects')
   for i in range(40):
    db.execute('INSERT INTO project_memory VALUES(?,?,?,?,?,?,?,?)',(str(i),'one','decision','x'*1900,'open',None,'',i))
  with patch('project_memory.catalog',return_value=[{'id':'one','name':'One'}]):
   result=tools.execute(c,self.item,'select_project',{'project_id':'one'})
  self.assertTrue(result['has_more']);self.assertGreater(len(result['memory']),0)
  self.assertLessEqual(len(json.dumps(result['memory'],ensure_ascii=False)),12000)
  with c.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM project_memory').fetchone()[0],40)

 def test_correct_saved_memory_preserves_identity_status_and_source(self):
  note=tools.execute(c,self.item,'save_memory',{'kind':'next_step','content':'Test on desktop.'})
  args={'memory_id':note['id'],'content':'Test on phone and desktop.'}
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'update_memory',args)
  tools.execute(c,self.item,'read_memory',{})
  tools.execute(c,self.item,'set_next_step_status',{'memory_id':note['id'],'status':'done'})
  for _ in range(2):result=tools.execute(c,self.item,'update_memory',args)
  self.assertEqual(result['content'],args['content']);self.assertEqual(result['status'],'done')
  for key in ['id','kind','source_turn_id','source_text','created']:self.assertEqual(result[key],note[key])
  with c.connect() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM project_memory').fetchone()[0],1)
   audit=json.loads(db.execute("SELECT result FROM voice_tool_results WHERE name='update_memory'").fetchone()[0])
   self.assertEqual(audit['previous_content'],'Test on desktop.')

 def test_memory_correction_rejects_stale_content_and_cross_project_ids(self):
  note=tools.execute(c,self.item,'save_memory',{'kind':'decision','content':'Use blue.'})
  tools.execute(c,self.item,'read_memory',{})
  with c.connect() as db:db.execute("UPDATE project_memory SET content='Use green.' WHERE id=?",(note['id'],))
  args={'memory_id':note['id'],'content':'Use cyan.'}
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'update_memory',args)
  tools.execute(c,self.item,'read_memory',{})
  self.assertEqual(tools.execute(c,self.item,'update_memory',args)['content'],'Use cyan.')
  with c.connect() as db:db.execute("UPDATE project_memory SET project_id='other' WHERE id=?",(note['id'],))
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'update_memory',args)

 def test_memory_correction_validates_replacement(self):
  for content in ['', ' ', None, 42, 'x'*2001]:
   with self.assertRaises(c.Problem):tools.execute(c,self.item,'update_memory',{'memory_id':'x','content':content})

 def test_followup_requires_observed_job(self):
  parent=jobs.draft(c,'__new_site__','Build a timer',None)
  with patch.object(jobs,'continue_job') as follow:
   with self.assertRaises(c.Problem):tools.execute(c,self.item,'continue_job',{'job_id':parent['id'],'task':'Change title'})
   tools.execute(c,self.item,'job_status',{})
   with self.assertRaises(c.Problem):tools.execute(c,self.item,'continue_job',{'job_id':'f'*32,'task':'Change title'})
   follow.assert_not_called()

 def test_project_followup_uses_current_memory_preserving_parent_snapshot(self):
  note=tools.execute(c,self.item,'save_memory',{'kind':'decision','content':'Use red accents.'})
  with patch.object(jobs,'projects',return_value={'test':'/tmp'}):parent=jobs.draft(c,'test','Build the design',None)
  with c.connect() as db:db.execute("UPDATE project_memory SET content='Use cyan accents.' WHERE id=?",(note['id'],))
  jobs.update(c,parent['id'],status='completed')
  with patch.object(jobs,'workspace_for',return_value=c.DATA):child=jobs.draft(c,'test','Revise the design',None,parent_id=parent['id'])
  self.assertIn('Use cyan accents.',child['context']);self.assertNotIn('Use red accents.',child['context'])
  self.assertIn('Use red accents.',jobs.get_job(c,parent['id'])['context'])

 def test_one_turn_saves_distinct_notes_without_retry_duplicates(self):
  requests=[{'kind':'decision','content':'Use cyan accents.'},{'kind':'next_step','content':'Test on a phone.'},{'kind':'next_step','content':'Check keyboard access.'}]
  saved=[tools.execute(c,self.item,'save_memory',args) for args in requests]
  self.assertEqual(len({n['id'] for n in saved}),3)
  for args,note in zip(reversed(requests),reversed(saved)):
   self.assertEqual(tools.execute(c,self.item,'save_memory',args)['id'],note['id'])
  with c.connect() as db:
   self.assertEqual(db.execute('SELECT count(*) FROM project_memory').fetchone()[0],3)
   audit=json.loads(db.execute("SELECT result FROM voice_tool_results WHERE name='save_memory'").fetchone()[0])
   self.assertEqual(len(audit['saved_items']),3)

 def test_save_retry_does_not_undo_later_correction_or_recreate_deleted_note(self):
  args={'kind':'decision','content':'Use red accents.'};note=tools.execute(c,self.item,'save_memory',args)
  tools.execute(c,self.item,'read_memory',{})
  tools.execute(c,self.item,'update_memory',{'memory_id':note['id'],'content':'Use cyan accents.'})
  self.assertEqual(tools.execute(c,self.item,'save_memory',args)['content'],'Use cyan accents.')
  with c.connect() as db:db.execute('DELETE FROM project_memory WHERE id=?',(note['id'],))
  with self.assertRaises(c.Problem):tools.execute(c,self.item,'save_memory',args)

 def test_save_retry_reads_legacy_single_note_audit(self):
  args={'kind':'decision','content':'Use the local Mac.'};note=tools.execute(c,self.item,'save_memory',args)
  with c.connect() as db:db.execute("UPDATE voice_tool_results SET result=? WHERE name='save_memory'",(json.dumps(note),))
  self.assertEqual(tools.execute(c,self.item,'save_memory',args)['id'],note['id'])
  second=tools.execute(c,self.item,'save_memory',{'kind':'next_step','content':'Test on phone.'})
  self.assertNotEqual(second['id'],note['id'])

 def test_keyword_memory_search_ranks_older_reordered_words(self):
  with c.connect() as db:
   db.execute('INSERT INTO project_memory VALUES(?,?,?,?,?,?,?,?)',('old','test','next_step','Check keyboard access on a phone.','open',None,'',0))
   for i in range(40):db.execute('INSERT INTO project_memory VALUES(?,?,?,?,?,?,?,?)',(str(i),'test','next_step',f'Phone task {i}','open',None,'',i+1))
  result=tools.execute(c,self.item,'read_memory',{'query':'phone keyboard'})
  self.assertEqual(result['search_mode'],'keyword_candidates');self.assertEqual(result['memory'][0]['id'],'old')
  self.assertTrue(result['has_more']);self.assertEqual(result['matching_count'],41)

 def test_keyword_memory_search_respects_word_boundaries_and_exact_precedence(self):
  from project_memory import search_memories
  notes=[{'content':'Update the catalog'},{'content':'Cat care'},{'content':'Care for the cat'}]
  matches,mode=search_memories(notes,'care cat')
  self.assertEqual(mode,'keyword_candidates');self.assertNotIn(notes[0],matches)
  matches,mode=search_memories(notes,'Cat care')
  self.assertEqual(mode,'exact_text');self.assertEqual(matches,[notes[1]])
  matches,mode=search_memories(notes,'what did we')
  self.assertEqual(mode,'recent_candidates_no_exact_match')

 def test_overview_works_unscoped_and_preserves_project_selection(self):
  catalog=[{'id':'one','name':'One','current_state':'Old catalog state','next_action':'Old suggestion','updated_at':'2026-01-01'},{'id':'two','name':'Two'}]
  with c.connect() as db:
   db.execute('INSERT INTO project_memory VALUES(?,?,?,?,?,?,?,?)',('1','one','next_step','Test on phone.','open',None,'',1))
   db.execute('INSERT INTO project_memory VALUES(?,?,?,?,?,?,?,?)',('2','one','next_step','Already done.','done',None,'',2))
   db.execute('INSERT INTO project_memory VALUES(?,?,?,?,?,?,?,?)',('3','two','decision','Use cyan.','open',None,'',3))
  with patch('project_memory.catalog',return_value=catalog):
   result=tools.execute(c,self.item,'project_overview',{})
   self.assertEqual(result['projects'][0]['id'],'one')
   self.assertEqual(result['projects'][0]['open_next_steps'],['Test on phone.'])
   self.assertEqual(result['projects'][0]['catalog_snapshot']['state'],'Old catalog state')
   self.assertEqual(result['projects'][1]['latest_decision'],'Use cyan.')
   with c.connect() as db:
    self.assertEqual(db.execute('SELECT project_id FROM conversation_projects').fetchone()[0],'test')
    db.execute('DELETE FROM conversation_projects')
   self.assertEqual(tools.execute(c,self.item,'project_overview',{})['total'],2)

 def test_overview_paginates_and_rejects_bad_inputs(self):
  catalog=[{'id':str(i),'name':f'Project {i:02d}'} for i in range(25)]
  with patch('project_memory.catalog',return_value=catalog):
   first=tools.execute(c,self.item,'project_overview',{});second=tools.execute(c,self.item,'project_overview',{'offset':first['next_offset']})
   self.assertEqual(len(first['projects']),10);self.assertTrue(first['has_more'])
   self.assertFalse({p['id'] for p in first['projects']} & {p['id'] for p in second['projects']})
   self.assertEqual(tools.execute(c,self.item,'project_overview',{'offset':25})['projects'],[])
  for args in [{'offset':-1},{'offset':True},{'offset':None}]:
   with self.assertRaises(c.Problem):tools.execute(c,self.item,'project_overview',args)

 def test_pause_listening_does_not_require_project_or_cancel_jobs(self):
  with c.connect() as db:db.execute('DELETE FROM conversation_projects')
  job=jobs.draft(c,'__new_site__','Build a timer',None);jobs.update(c,job['id'],status='running')
  for _ in range(2):result=tools.execute(c,self.item,'pause_listening',{})
  self.assertTrue(result['pause_after_reply']);self.assertEqual(c.turn(self.item['id'])['client_action'],'pause_listening')
  self.assertEqual(jobs.get_job(c,job['id'])['status'],'running')
