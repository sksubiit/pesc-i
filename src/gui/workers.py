"""Workers carry data only. UI callbacks are owned and released by the main thread."""

from queue import Queue
import threading


class Worker:
    def __init__(self, results):
        self.jobs = Queue()
        self.results = results
        self.callbacks = {}
        self.next_id = 0
        threading.Thread(target=self.run, daemon=True).start()

    def submit(self, work, success, failure, cancelled):
        self.next_id += 1
        job_id = self.next_id
        self.callbacks[job_id] = (success, failure)
        self.jobs.put((job_id, work, cancelled))

    def dispatch(self, job_id, cancelled, succeeded, value):
        callbacks = self.callbacks.pop(job_id, None)
        if callbacks is not None and not cancelled.is_set():
            callbacks[0 if succeeded else 1](value)

    def close(self):
        self.callbacks.clear()
        self.jobs.put(None)

    def run(self):
        while True:
            job = self.jobs.get()
            if job is None:
                return
            job_id, work, cancelled = job
            succeeded, value = False, None
            if not cancelled.is_set():
                try:
                    value = work()
                    succeeded = True
                except Exception as exc:
                    value = exc
            self.results.put((self, job_id, cancelled, succeeded, value))
            # Do not retain completed work, exceptions, or chess positions while idle.
            work = value = None
