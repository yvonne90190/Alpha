import os
import time
import json
from .config import SIMULATION, ALPHA#, AlphaStage
import alpha as alpha_lib

def simulate_alpha(sess, alpha: alpha_lib.Alpha):
#    print(json.dumps(alpha._to_dict()))
    simulation_response = sess.post(SIMULATION, json=alpha.payload)
    print(simulation_response)

    if simulation_response.status_code != 201:
        print(f"Failed to start simulation: {simulation_response.status_code}")
        return

    simulation_progress_url = simulation_response.headers['Location']
    while True:
        simulation_progress = sess.get(simulation_progress_url)
        if simulation_progress.headers.get("Retry-After", 0) == 0:
            break
        print("Sleeping for " + simulation_progress.headers["Retry-After"] + " seconds")
        time.sleep(float(simulation_progress.headers["Retry-After"]))
    
    print("Alpha done simulating, getting alpha details")
    alpha_id = simulation_progress.json()["alpha"]
    alpha_response = sess.get(f"{ALPHA}/{alpha_id}")
    
    if alpha_response.status_code != 200:
        print(f"Failed to get recordsets: {alpha_response.status_code}")
        return None
    
    try:
        alpha.result = alpha_response.json()
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return None
    
    alpha.update_status(alpha_lib.AlphaStage.RESULT)
