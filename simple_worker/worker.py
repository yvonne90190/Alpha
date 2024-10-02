import time
import os
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from simple_worker.auth import get_session
from simple_worker.simulation import simulate_alpha
from simple_worker.utils import load_pending_alphas
import alpha as alpha_lib
from simple_worker.config import SIMULATION, ALPHA

class Worker:
    def __init__(self, session):
        self.sess = session
        self.semaphore = asyncio.Semaphore(10)
        self.executor = ThreadPoolExecutor(max_workers=10)

    async def simulate_alpha_coroutine(self, alpha: str, file_path: str):
        async with self.semaphore:
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(self.executor, simulate_alpha, self.sess, alpha)
                # Comment out or remove the following line to avoid printing success message
                # print(f"Simulation successful, file {file_path}")
                self.remove_file(file_path)
            except Exception as e:
                # Comment out or remove the following line to avoid printing error message
                # print(f"Simulation failed, file {file_path} error: {e}")
                pass

    async def run_simulations(self):
        while True:
            pending_alphas = load_pending_alphas()
            if not pending_alphas:
                print("No pending simulations. Sleeping for 2.5 seconds.")
                await asyncio.sleep(2.5)
                continue

            tasks = [self.simulate_alpha_coroutine(alpha, file_path) for alpha, file_path in pending_alphas[:10]]
            await asyncio.gather(*tasks)

    def run(self):
        # asyncio.run(self.run_simulations())
        while True:
            while len(os.listdir(alpha_lib.AlphaStage.RUNNING.value)) < 10 and len(os.listdir(alpha_lib.AlphaStage.PENDING.value)) > 0:
                filename = os.listdir(alpha_lib.AlphaStage.PENDING.value)[0]
                print(f'Send {filename} to running')
                alpha = alpha_lib.Alpha.read_from_disk(
                    os.path.join(alpha_lib.AlphaStage.PENDING.value, filename)
                )
                resp = self.sess.post(
                    SIMULATION,
                    json=alpha.payload
                )
                if 'Location' not in resp.headers:
                    time.sleep(1)
                    continue
                alpha.result['location_url'] = resp.headers['Location']
                alpha.update_status(alpha_lib.AlphaStage.RUNNING)

            for filename in os.listdir(alpha_lib.AlphaStage.RUNNING.value):
                print(f'Check {filename} from running')
                alpha = alpha_lib.Alpha.read_from_disk(
                    os.path.join(alpha_lib.AlphaStage.RUNNING.value, filename)
                )
                simulation_progress = self.sess.get(alpha.result['location_url'])
                if simulation_progress.headers.get("Retry-After", 0) == 0:
                    print(f'Send {filename} from result')
                    try:
                        alpha_id = simulation_progress.json()["alpha"]
                    except KeyError:
                        print(f'{simulation_progress.status_code}')
                        print(f'{simulation_progress.headers}')
                        print(f'{simulation_progress.json()}')
                        if simulation_progress.json()['status'] == 'FAIL':
                            alpha.update_status(alpha_lib.AlphaStage.PENDING)
                            break
                        raise
                    alpha_response = self.sess.get(f"{ALPHA}/{alpha_id}")
                    if alpha_response.status_code != 200:
                        print(f"Failed to get recordsets: {alpha_response.status_code}")
                        return None
                    try:
                        alpha.result = alpha_response.json()
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        return None
                    alpha.update_status(alpha_lib.AlphaStage.RESULT)
                    break
                time.sleep(float(simulation_progress.headers["Retry-After"]))
            if len(os.listdir(alpha_lib.AlphaStage.RUNNING.value)) == 0:
                time.sleep(5)
                print(f'No alpha to sim...')
            


    def remove_file(self, file_path: str):
        try:
            os.remove(file_path)
            # Comment out or remove the following line to avoid printing file deletion message
            # print(f"File {file_path} deleted successfully")
        except OSError:
            # Comment out or remove the following line to avoid printing file deletion error message
            # print(f"Error deleting file {file_path}: {e}")
            pass

def main():
    session = get_session()
    worker = Worker(session)
    worker.run()

if __name__ == '__main__':
    main()
