import sys
import json
import simplejson
import base64
import requests

URL_PREFIX = 'http://127.0.0.1:11111'
GET = requests.get
POST = requests.post
user = None

def request_page(url, data={}, params={}, method=GET) :
	assert url.startswith('/') and not url.startswith('//')
	resp = method(URL_PREFIX + url, data=data, params=params)
	return resp.json()

def assert_success(url, data={}, params={}, method=GET) :
	global user
	if user is not None :
		params = params.copy()
		params['user'] = user
	resp = request_page(url, data, params, method)
	if resp['success'] != True :
		print(repr(resp), file=sys.stderr)
		raise Exception('Not success')
	return resp

def assert_fail(url, data={}, params={}, method=GET, msg=None) :
	global user
	if user is not None :
		params = params.copy()
		params['user'] = user
	resp = request_page(url, data, params, method)
	if resp['success'] != False :
		print(repr(resp), file=sys.stderr)
		raise Exception('Success')
	if msg is not None :
		assert resp['message'] == msg
	return resp

# Run init.py before running the test

def test_init() :
	import os, time
	from settings import DB_NAME
	assert DB_NAME.startswith('sqlite:///')
	os.unlink(DB_NAME[len('sqlite:///'):])
	os.system('touch vserver.py')
	time.sleep(2)

def test_list_courses() :
	url = '/api/courses'
	global user
	user = None
	assert assert_fail(url, msg='Login required (Please supply user)')
	user = 'Nobody'
	assert assert_fail(url, msg='Login required (User not found)')
	user = 'Kevin'
	assert assert_success(url)['courses'] == ['course1']
	user = 'Abigail'
	assert assert_success(url)['courses'] == ['course2']
	user = 'Lawrence'
	assert assert_success(url)['courses'] == ['course1']
	user = 'Eric'
	assert assert_success(url)['courses'] == ['course2']

def test_add_courses() :
	url = '/api/course/%s'
	global user
	user = None
	assert assert_fail(url % 'course3', method=POST,
						msg='Login required (Please supply user)')
	user = 'Erics'
	assert assert_fail(url % 'course3', method=POST,
						msg='Login required (User not found)')
	user = 'Eric'
	assert_success(url % 'course3', method=POST)
	assert assert_fail(url % 'course3', method=POST,
						msg='Course already exists')
	assert assert_success('/api/courses')['courses'] == ['course2', 'course3']

def test_list_assignments() :
	url = '/api/assignments/%s'
	assert assert_success(url % 'course2')['assignments'] == \
			['assignment2a', 'assignment2b']
	assert assert_fail(url % 'jkl', msg='Course not found')

def test_download_assignment() :
	files = assert_success('/api/assignment/course1/challenge')['files']
	assert files[0]['path'] == 'file2'
	assert base64.b64decode(files[0]['content'].encode()) == b'22222'
	assert assert_fail('/api/assignment/jkl/challenger', msg='Course not found')
	assert assert_fail('/api/assignment/course1/challenger',
						msg='Assignment not found')
	# Check list_only
	files = assert_success('/api/assignment/course1/challenge?list_only=true') \
			['files']
	assert list(files[0]) == ['path']
	assert files[0]['path'] == 'file2'

def test_release_assignment() :
	data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
									{'path': 'b', 'content': 'amtsCg=='}])}
	assert assert_fail('/api/assignment/jkl/challenger', method=POST, 
						data=data, msg='Course not found')
	assert assert_fail('/api/assignment/course1/challenger', method=POST
						, msg='Please supply files')
	assert_success('/api/assignment/course1/challenger', method=POST, 
					data=data)
	assert assert_fail('/api/assignment/course1/challenger', method=POST, 
						data=data, msg='Assignment already exists')
	data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg'}])
	assert assert_fail('/api/assignment/course1/challenges', method=POST, 
			data=data, msg='Content cannot be base64 decoded')

def test_list_submissions() :
	assert assert_fail('/api/submissions/jkl/challenge', msg='Course not found')
	assert assert_fail('/api/submissions/course1/challenges',
						msg='Assignment not found')
	result = assert_success('/api/submissions/course1/challenge')
	assert len(result['submissions']) == 2
	assert set(result['submissions'][0]) == \
			{'student_id', 'timestamp', 'random'}
	assert result['submissions'][0]['student_id'] == 'Lawrence'
	assert result['submissions'][1]['student_id'] == 'Lawrence'
	result = assert_success('/api/submissions/course2/assignment2a')
	assert len(result['submissions']) == 0

def test_list_student_submission() :
	assert assert_fail('/api/submissions/jkl/challenge/st',
						msg='Course not found')
	assert assert_fail('/api/submissions/course1/challenges/st',
						msg='Assignment not found')
	assert assert_fail('/api/submissions/course1/challenge/st',
						msg='Student not found')
	result = assert_success('/api/submissions/course1/challenge/Lawrence')
	assert len(result['submissions']) == 2
	assert set(result['submissions'][0]) == \
			{'student_id', 'timestamp', 'random'}
	result = assert_success('/api/submissions/course2/assignment2a/Eric')
	assert len(result['submissions']) == 0

def test_submit_assignment() :
	data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
									{'path': 'b', 'content': 'amtsCg=='}])}
	assert assert_fail('/api/submission/jkl/challenge/st', method=POST,
						msg='Course not found')
	assert assert_fail('/api/submission/course1/challenges/st', method=POST,
						msg='Assignment not found')
	assert assert_fail('/api/submission/course1/challenge/st', method=POST,
						msg='Student not found')
	assert assert_fail('/api/submission/course1/challenge/Lawrence',
			method=POST, msg='Please supply files')
	assert_success('/api/submission/course1/challenge/Lawrence',
			method=POST, data=data)
	data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg=='}])
	assert_success('/api/submission/course1/challenge/Lawrence',
			method=POST, data=data)
	data['files'] = json.dumps([{'path': 'a', 'content': 'amtsCg'}])
	assert assert_fail('/api/submission/course1/challenge/Lawrence',
			method=POST, data=data, msg='Content cannot be base64 decoded')
	result = assert_success('/api/submissions/course1/challenge/Lawrence')
	assert len(result['submissions']) == 4	# 2 from init, 2 from this

def test_download_submission() :
	assert assert_fail('/api/submission/jkl/challenge/st',
						msg='Course not found')
	assert assert_fail('/api/submission/course1/challenges/st',
						msg='Assignment not found')
	assert assert_fail('/api/submission/course1/challenge/st',
						msg='Student not found')
	result = assert_success('/api/submission/course1/challenge/Lawrence')
	assert len(result['files']) == 1
	assert next(filter(lambda x: x['path'] == 'a', result['files'])) \
			['content'].replace('\n', '') == 'amtsCg=='
	assert assert_fail('/api/submission/course2/assignment2a/Eric',
						msg='Submission not found')
	# Check list_only
	result = assert_success(
		'/api/submission/course1/challenge/Lawrence?list_only=true')
	assert len(result['files']) == 1
	assert list(result['files'][0]) == ['path']
	assert result['files'][0]['path'] == 'a'

def test_upload_feedback() :
	data = {'files': json.dumps([{'path': 'a', 'content': 'amtsCg=='},
									{'path': 'b', 'content': 'amtsCg=='}]),
			'timestamp': '2020-01-01 00:00:00.000000 ', 'random': '123456789'}
	assert assert_fail('/api/feedback/jkl/challenge/st', method=POST,
			data=data, msg='Course not found')
	assert assert_fail('/api/feedback/course1/challenges/st', method=POST,
			data=data, msg='Assignment not found')
	assert assert_fail('/api/feedback/course1/challenge/st', method=POST,
			data=data, msg='Student not found')
	assert_success('/api/feedback/course1/challenge/Lawrence',
					method=POST, data=data)
	data['files'] = json.dumps([{'path': 'c', 'content': 'amtsCf=='}])
	assert_success('/api/feedback/course1/challenge/Lawrence',
					method=POST, data=data)
	assert assert_fail('/api/feedback/course1/challenge/Lawrence', method=POST,
			data={'timestamp': data['timestamp']},
			msg='Please supply random str')
	assert assert_fail('/api/feedback/course1/challenge/Lawrence', method=POST,
			data={'random': data['random']}, msg='Please supply timestamp')
	assert assert_fail('/api/feedback/course1/challenge/Lawrence', method=POST,
			data={'random': data['random'], 'timestamp': 'a'},
			msg='Time format incorrect')
	assert assert_fail('/api/feedback/course2/assignment2a/Eric', method=POST,
			data=data, msg='Submission not found')
	assert assert_fail('/api/feedback/course2/assignment2a/Eric', method=POST,
			data={'timestamp': data['timestamp'], 'random': ''},
			msg='Submission not found')

def test_download_feedback() :
	assert assert_fail('/api/feedback/jkl/challenge/st',
						msg='Course not found')
	assert assert_fail('/api/feedback/course1/challenges/st',
						msg='Assignment not found')
	assert assert_fail('/api/feedback/course1/challenge/st',
						msg='Student not found')
	meta = assert_success('/api/submission/course1/challenge/Lawrence')
	timestamp = meta['timestamp']
	random = meta['random']
	assert assert_fail('/api/feedback/course1/challenge/Lawrence',
			params={'timestamp': timestamp}, msg='Please supply random str')
	assert assert_fail('/api/feedback/course1/challenge/Lawrence',
			params={'random': random}, msg='Please supply timestamp')
	assert assert_fail('/api/feedback/course1/challenge/Lawrence',
			params={'random': random, 'timestamp': 'a'},
			msg='Time format incorrect')
	assert assert_fail('/api/feedback/course2/assignment2a/Eric',
			params={'random': random, 'timestamp': timestamp},
			msg='Submission not found')
	feedback = assert_success('/api/feedback/course1/challenge/Lawrence', 
							params={'timestamp': timestamp, 'random': random})
	assert feedback['files'] == []
	# Submit again
	data = {'files': json.dumps([{'path': 'a', 'content': 'amtsDg=='}]),
			'timestamp': timestamp, 'random': random}
	assert_success('/api/feedback/course1/challenge/Lawrence',
					method=POST, data=data)
	# Fetch again
	feedback = assert_success('/api/feedback/course1/challenge/Lawrence', 
							params={'timestamp': timestamp, 'random': random})
	assert len(feedback['files']) == 1
	assert feedback['files'][0]['path'] == 'a'
	assert feedback['files'][0]['content'].replace('\n', '') == 'amtsDg=='
	# Again, submit again
	data = {'files': json.dumps([{'path': 'a', 'content': 'bmtsDg=='}]),
			'timestamp': timestamp, 'random': random}
	assert_success('/api/feedback/course1/challenge/Lawrence',
					method=POST, data=data)
	# Again, fetch again
	feedback = assert_success('/api/feedback/course1/challenge/Lawrence',
							params={'timestamp': timestamp, 'random': random})
	assert len(feedback['files']) == 1
	assert feedback['files'][0]['path'] == 'a'
	assert feedback['files'][0]['content'].replace('\n', '') == 'bmtsDg=='
	# Check list_only
	feedback = assert_success('/api/feedback/course1/challenge/Lawrence',
							params={'timestamp': timestamp, 'random': random,
									'list_only': 'true'})
	assert len(feedback['files']) == 1
	assert list(feedback['files'][0]) == ['path']
	assert feedback['files'][0]['path'] == 'a'
