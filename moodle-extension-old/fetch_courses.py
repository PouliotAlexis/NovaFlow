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
            const logoutLink = document.querySelector('a[href*=\"logout.php?sesskey=\"]');
            if (!logoutLink) return resolve(JSON.stringify({error: 'No sesskey'}));
            const sesskey = new URL(logoutLink.href).searchParams.get('sesskey');
            
            fetch('/lib/ajax/service.php?sesskey=' + sesskey + '&info=core_course_get_enrolled_courses_by_timeline_classification', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify([{
                    'index': 0,
                    'methodname': 'core_course_get_enrolled_courses_by_timeline_classification',
                    'args': {'classification': 'all', 'limit': 0, 'offset': 0, 'sort': 'fullname'}
                }])
            }).then(res => res.json()).then(data => {
                resolve(JSON.stringify(data));
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
            courses = data[0].get("data", {}).get("courses", [])
            for c in courses[:5]:
                print(f"[{c.get('shortname')}] {c.get('fullname')} - ID {c.get('id')}")
        else:
            print('Script returned no value. Result:', result)
    else:
        print('Moodle tab not found.')
except Exception as e:
    print('Error:', e)
