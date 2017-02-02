# Record piano playing
# For a pyboard
# Uses a laser beam, interruped by the hammers, to tell that piano is played
# Controls a Sound Devices recorder (e.g. 702T) via a CL-1 interface box

import array
from machine import Pin
from pyb import Timer, rng, ADC, DAC, LED, Switch
from time import sleep, ticks_ms, ticks_diff, time
import micropython


def hv(signal, harmonic):
    length = len(signal)
    return sum(signal[i]*signal[(harmonic*i)%length]
               for i in range(length)) / length

class LaserBeam:
    def __init__(self, laser_pinname, photodiode_pinname):
        self.laser = Pin(laser_pinname, Pin.OUT_OD)
        self.photodiode = ADC(photodiode_pinname)
        self.threshold = 100

    def ping(self):
        dark = self.photodiode.read()
        self.laser.value(0)          # pull down to on
        light = self.photodiode.read()
        self.laser.value(1)          # float to off
        return light-dark

    def interrupted(self):
        return self.ping() < self.threshold \
            and sum(self.ping() for i in range(10)) < 10 * self.threshold

class Piano:
    def __init__(self, beam):
        self.beam = beam
        self.beam_ever_interrupted = False
        self.being_played = False
        self.internote = 30
        self.verbose = False

    def poll_beam(self):
        if self.beam.interrupted():
            self.beam_interrupted_t = time()
            self.beam_ever_interrupted = True
            return True
        else:
            return False

    def playing(self):
        """
        Determine if the piano is being played:
        1. A beam interruption (transition from unterrupted to interrupted)
        indicates the start of playing.
        2. It's no longer being played if the inter-note time has passed with
        no subsequent beam interruption
        """
        rv = self.poll_beam() \
             or self.beam_ever_interrupted \
             and (time() - self.beam_interrupted_t) < self.internote
        if self.verbose:
            print('piano playing: %s' % rv)
        return rv



class CL1:
    def __init__(self, stop_cmd, stop_status,
                 record_cmd, rec_status,
                 play_cmd, play_status):
        self.record_cmd = Pin(record_cmd, Pin.OUT, value=1)
        self.stop_cmd = Pin(stop_cmd, Pin.OUT, value=1)
        self.play_cmd = Pin(play_cmd, Pin.OUT, value=1)
        self.rec_status = Pin(rec_status)
        self.stop_status = Pin(stop_status)
        self.play_status = Pin(play_status)
        self.pulse_duration = 0.4

    def stopped(self):
        return not self.stop_status()

    def recording(self):
        return not self.rec_status()

    def playing(self):
        return not self.play_status()

    #FIXME: timeouts
    def stop(self):
        while not self.stopped():
            self._pulse_low(self.stop_cmd)
            if not self.stopped():
                print('Hey, stop!')

    def record(self):
        while not self.recording():
            self._pulse_low(self.record_cmd)
            if not self.recording():
                print('Hey, record!')

    def play(self):
        while not self.playing():
            self._pulse_low(self.play_cmd)
            if not self.playing():
                print('Hey, play!')

    def _pulse_low(self, what):
        what(0)
        sleep(self.pulse_duration)
        what(1)
        sleep(self.pulse_duration)

    def status(self):
        s = (self.stopped(), self.recording(), self.playing())
        names = ('stopped', 'recording', 'playing')
        return ' '.join(v[1] for v in zip(s, names) if v[0])

class Lights:
    def __init__(self, beam, deck):
        self.beam = beam
        self.deck = deck
        self.leds = [LED(1), LED(2), LED(3), LED(4)]

    def update(self):
        l = self.leds
        if self.deck.recording():
            l[0].on()
        else:
            l[0].off()
        if self.deck.playing():
            l[1].on()
        else:
            l[1].off()
        if self.deck.stopped():
            l[2].on()
        else:
            l[2].off()
        l[3].intensity(self.beam.ping() >> 4)
        


def main():
    micropython.alloc_emergency_exception_buf(100)
    print('simp here')
    beam = LaserBeam('X1', 'X11')
    deck = CL1('X17', 'X18', 'X19', 'X20', 'X21', 'X22')
    piano = Piano(beam)
    lights = Lights(beam, deck)
    pushbutton = Switch()
    verbose = False

    def show():
        lights.update()
        if not verbose:
            return
        print('{}: laser {}'.format(ticks_ms(), beam.interrupted()), end=' ')
        sleep(0.1)
        print('deck %s' % deck.status(), end=' ')
        if piano.playing():
            print('Piano being played', end='')
        print()

    sleep(1)                    # stabilize
    while True:
        show()
        if piano.playing() and not deck.recording():
            deck.record()
            print("record")
            while piano.playing():
                show()
            deck.stop()
            print("stop")
        
if __name__ == '__main__':
    main()
