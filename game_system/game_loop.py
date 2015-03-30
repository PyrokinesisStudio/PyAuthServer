__all__ = "FixedTimeStepManager", "OnExitUpdate"


from time import monotonic


class OnExitUpdate(Exception):
    """Safe exit exception"""
    pass


class FixedTimeStepManager:
    """Real-time, fixed time-step logic controller"""
    
    time_step = 1 / 60
    maximum_dt = 1 / 5
    
    def __init__(self):
        self._running = False
        
        self._accumulator = 0.0
        self._last_time = None
    
    @property
    def is_running(self):
        return self._running
    
    def on_step(self, delta_time):
        """Step callback.
        Called for discrete intervals of time_step

        :param delta_time: discrete unit of update time
        """
        pass

    def on_update(self, delta_time):
        """Update callback.
        Called continuously for each iteration of update loop

        :param delta_time: continuous unit of update time
        """
        pass

    def _run(self):
        """Internal blocking execution function"""
        time_step = self.time_step
        
        while True:            
            current_time = monotonic()
            last_time = current_time if self._last_time is None else self._last_time
            delta_time = min(current_time - last_time, self.maximum_dt)
            self._last_time = current_time
            
            self._accumulator += delta_time
            
            while self._accumulator > time_step:
                self.on_step(time_step)                    
                self._accumulator -= time_step
                
                time_step = self.time_step

            self.on_update(delta_time)

    def cleanup(self):
        pass

    def delegate(self):
        """Start blocking execute of update functions at discrete time-step"""
        self._running = True
        
        try:
            self._run()
         
        except OnExitUpdate:
            pass
        
        finally:
            try:
                self.cleanup()

            finally:
                self._running = False