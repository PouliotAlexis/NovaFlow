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
            if (!logoutLink) return resolve(JSON.stringify({error: 'No sesskey found'}));
            const sesskey = new URL(logoutLink.href).searchParams.get('sesskey');
            
            fetch('/lib/ajax/service.php?sesskey=' + sesskey + '&info=core_calendar_get_action_events_by_timesort', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify([{
                    'index': 0,
                    'methodname': 'core_calendar_get_action_events_by_timesort',
                    'args': {'limitnum': 50, 'timesortfrom': Math.floor(Date.now() / 1000) - 86400 * 14}
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
            with open('moodle_api_timeline.json', 'w', encoding='utf-8') as f:
                f.write(val)
            print('Saved to moodle_api_timeline.json')
        else:
            print('Script returned no value. Result:', result)
    else:
        print('Moodle tab not found.')
except Exception as e:
    print('Error:', e)
