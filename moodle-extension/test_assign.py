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
            
            fetch('/lib/ajax/service.php?sesskey=' + sesskey + '&info=mod_assign_get_assignments', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify([{
                    'index': 0,
                    'methodname': 'mod_assign_get_assignments',
                    'args': {}
                }])
            }).then(r => r.json()).then(data => {
                resolve(JSON.stringify({
                    sesskey: sesskey,
                    assignData: data
                }));
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
            print("Successfully retrieved assignments.")
            with open('test_assign.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        else:
            print('Script returned no value. Result:', result)
    else:
        print('Moodle tab not found.')
except Exception as e:
    print('Error:', e)
