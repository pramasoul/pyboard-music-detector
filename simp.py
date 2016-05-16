#
# simple

import array
from pyb import Pin, Timer, rng, ADC, DAC, LED
from time import sleep, ticks_ms, ticks_diff
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


class Mic:
    def __init__(self, mic_pinname, timer_id=6):
        self.mic = ADC(mic_pinname)
        self.tim = Timer(timer_id, freq=48000)
        self.samples = array.array('h', range(4800))
        self.normalized_spl = 0.0

    def level(self):
        samples = self.samples
        self.mic.read_timed(samples, self.tim)
        ave = sum(samples) / len(samples)
        self.normalized_spl = \
            min(1.0, sum((v-ave)**2 for v in samples) / len(samples) / 2278619.0)
        return self.normalized_spl

    def excited(self):
        return self.level() > 0.01


class Piano:
    def __init__(self, mic, beam):
        self.mic = mic
        self.beam = beam
        self.beam_ever_interrupted = self.mic_ever_excited = False
        self.being_played = False
        self.ms_internote = 30 * 1000

    def poll_beam(self):
        if self.beam.interrupted():
            self.beam_interrupted_t = ticks_ms()
            self.beam_ever_interrupted = True
            return True
        else:
            return False

    def poll_mic(self):
        if self.mic.excited():
            self.mic_excited_t = ticks_ms()
            self.mic_ever_excited = True
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
        return self.poll_beam() \
            or self.beam_ever_interrupted \
            and ticks_diff(self.beam_interrupted_t, ticks_ms()) < self.ms_internote 
        """
        if not self.being_played:
            if self.poll_beam(): # Check the laser beam (this is fast)
                self.being_played = True
        else:
            self.poll_beam()   # Check the laser beam (this is fast)
            if ticks_diff(self.beam_interrupted_t, ticks_ms()) < self.ms_internote:
                self.being_played = True
            else:
                # Could conceiveably be in an extended legato, so check the mic
                self.poll_mic()         # This is slow
                if self.mic_ever_excited \
                   and ticks_diff(self.mic_excited_t, ticks_ms() < self.ms_internote):
                    self.being_played = True
                else:
                    self.being_played = False
        return self.being_played
        """


class CL1:
    def __init__(self, stop_cmd, stop_status,
                 rec_cmd, rec_status,
                 play_cmd, play_status):
        self.rec_cmd = Pin(rec_cmd, Pin.OUT_OD)
        self.rec_cmd.value(1)
        self.stop_cmd = Pin(stop_cmd, Pin.OUT_OD)
        self.stop_cmd.value(1)
        self.play_cmd = Pin(play_cmd, Pin.OUT_OD)
        self.play_cmd.value(1)
        self.rec_status = Pin(rec_status, Pin.IN, pull=Pin.PULL_UP)
        self.stop_status = Pin(stop_status, Pin.IN, pull=Pin.PULL_UP)
        self.play_status = Pin(play_status, Pin.IN, pull=Pin.PULL_UP)

    def stopped(self):
        return not self.stop_status.value()

    def recording(self):
        return not self.rec_status.value()

    def playing(self):
        return not self.play_status.value()

    #FIXME: timeouts
    def stop(self):
        if not self.stopped():
            self.stop_cmd.value(0)
            while not self.stopped():
                sleep(0.1)
        self.stop_cmd.value(1)

    def record(self):
        if not self.recording():
            self.rec_cmd.value(0)
            while not self.recording():
                sleep(0.1)
        self.rec_cmd.value(1)

    def play(self):
        if not self.playing():
            self.play_cmd.value(0)
            while not self.playing():
                sleep(0.1)
        self.play_cmd.value(1)


class Lights:
    def __init__(self, mic, beam, deck):
        self.mic = mic
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
        l[2].intensity(self.beam.ping() >> 4)
        l[3].intensity(int(256*self.mic.normalized_spl))
        


def main():
    micropython.alloc_emergency_exception_buf(100)
    print('simp here')
    beam = LaserBeam('Y3', 'X11')
    mic = Mic('X12')
    deck = CL1('X17', 'X18', 'X19', 'X20', 'X21', 'X22')
    piano = Piano(mic, beam)
    lights = Lights(mic, beam, deck)

    def show():
        lights.update()
        """
        t = ((deck.stopped, 'stopped'),
             (deck.recording, 'recording'),
             (deck.playing, 'playing'))
        print('laser {}, mic {}'.format(beam.interrupted(), mic.excited()), end=' ')
        print('deck', end=' ')
        for test, label in t:
            if test():
                print(label, end= ' ')
        if piano.playing():
            print('Piano being played', end='')
        print()
        """

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
