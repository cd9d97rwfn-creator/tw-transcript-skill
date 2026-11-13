import base64,io,json,re,sqlite3,tempfile,unittest
from pathlib import Path
from tw_transcript_agent.web import create_app

class WebsiteTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.app=create_app({'TESTING':True,'START_WORKER':False,'DATA_DIR':self.temp.name,'APP_PASSWORD':'a-private-password-for-test','GITHUB_REPO_URL':'https://github.com/example/transcript'})
  self.client=self.app.test_client();self.auth={'Authorization':'Basic '+base64.b64encode(b'user:a-private-password-for-test').decode()}
  html=self.client.get('/',headers=self.auth).text
  self.headers={**self.auth,'X-CSRF-Token':re.search(r'const token="([^"]+)"',html).group(1)}
 def tearDown(self): self.temp.cleanup()
 def test_upload_and_all_downloads(self):
  response=self.client.post('/api/jobs',headers=self.headers,data={'file':(io.BytesIO(b'fixture'),'audio.mp3')})
  self.assertEqual(response.status_code,202);identifier=response.json['id'];base='/api/jobs/'+identifier+'/download'
  self.assertEqual(self.client.get(base,headers=self.auth).status_code,409)
  folder=self.root/identifier;(folder/'export').mkdir()
  samples={'txt':('export/專有名詞校稿版.txt','忠實逐字稿'.encode()),'md':('export/專有名詞校稿版.md',b'# Transcript'),'json':('export/raw_segments.json',b'[]'),'zip':('result.zip',b'ZIP-FIXTURE')}
  for name,body in samples.values():(folder/name).write_bytes(body)
  with sqlite3.connect(self.root/'jobs.sqlite') as db:db.execute("UPDATE jobs SET status='done' WHERE id=?",(identifier,))
  for fmt,(_,body) in samples.items():
   with self.client.get(base+'?format='+fmt,headers=self.auth) as r:
    self.assertEqual(r.status_code,200);self.assertEqual(r.data,body);self.assertIn('attachment',r.headers['Content-Disposition'])
  for fmt in ['srt','../../.env','html']: self.assertEqual(self.client.get(base+'?format='+fmt,headers=self.auth).status_code,400)
  self.assertEqual(self.client.get(base+'?format=txt').status_code,401)
 def test_github_and_safe_missing_configuration(self):
  self.assertIn('href="https://github.com/example/transcript"',self.client.get('/',headers=self.auth).text)
  with self.assertRaises(ValueError):create_app({'APP_PASSWORD':'a-private-password-for-test','GITHUB_REPO_URL':'javascript:alert(1)'})
 def test_missing_key_blocks_charge(self):
  from unittest.mock import patch
  self.app.testing=False
  with patch.dict('os.environ',{'OPENAI_API_KEY':''}):
   self.assertEqual(self.client.post('/api/jobs',headers=self.headers,data={'file':(io.BytesIO(b'audio'),'a.mp3')}).status_code,503)
 def test_csrf_and_invalid_file(self):
  self.assertEqual(self.client.post('/api/jobs',headers=self.auth).status_code,403)
  self.assertEqual(self.client.post('/api/jobs',headers=self.headers,data={'file':(io.BytesIO(b'bad'),'a.html')}).status_code,400)

if __name__=='__main__':unittest.main()
