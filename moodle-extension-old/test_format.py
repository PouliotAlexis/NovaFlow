import json, urllib.request, websocket

try:
    req = urllib.request.Request('http://localhost:9222/json')
    with urllib.request.urlopen(req) as response:
        targets = json.loads(response.read())

    ws_url = next((t['webSocketDebuggerUrl'] for t in targets if 'moodle.usherbrooke' in t.get('url', '')), None)

    if ws_url:
        ws = websocket.create_connection(ws_url, suppress_origin=True)
        
        script = """
        new Promise((resolve) => {
            const logoutLink = document.querySelector('a[href*="logout.php?sesskey="]');
            if (!logoutLink) return resolve(JSON.stringify({error: 'No sesskey'}));
            const sesskey = new URL(logoutLink.href).searchParams.get('sesskey');
            
            fetch('/lib/ajax/service.php?sesskey=' + sesskey + '&info=core_course_get_enrolled_courses_by_timeline_classification', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify([{
                    'index': 0,
                    'methodname': 'core_course_get_enrolled_courses_by_timeline_classification',
                    'args': {'classification': 'all', 'limit': 1, 'offset': 0, 'sort': 'fullname'}
                }])
            }).then(res => res.json()).then(data => {
                const courses = data[0].data.courses;
                
                return fetch('/lib/ajax/service.php?sesskey=' + sesskey + '&info=core_courseformat_get_state', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify([{
                        'index': 0,
                        'methodname': 'core_courseformat_get_state',
                        'args': {'courseid': courses[0].id}
                    }])
                }).then(r => r.json());
            }).then(data => {
                resolve(JSON.stringify(JSON.parse(data[0].data)));
            }).catch(err => resolve(JSON.stringify({error: err.toString()})));
        })
        """
        
        ws.send(json.dumps({
            'id': 1,
            'method': 'Runtime.evaluate',
            'params': {'expression': script, 'awaitPromise': True, 'returnByValue': True}
        }))
        
        result = json.loads(ws.recv())
        ws.close()
        
        val = result.get('result', {}).get('result', {}).get('value')
        if val:
            data = json.loads(val)
            print("Successfully retrieved course format state.")
            with open('test_format.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        else:
            print('Script returned no value. Result:', result)
    else:
        print('Moodle tab not found.')
except Exception as e:
    print('Error:', e)
