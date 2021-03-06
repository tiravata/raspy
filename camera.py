import picamera
import numpy as np
import io
import RPi.GPIO as GPIO
from scipy import misc
from datetime import datetime
from time import time, sleep

if GPIO.getmode() == -1: GPIO.setmode(GPIO.BOARD)

class Camera():
    def __init__(self, w=320, h=240):
        self.camera = picamera.PiCamera(resolution=(w,h))
        self.closed = self.camera.closed
        self.resolution(w, h)
        self.stream = io.BytesIO()

    def snap(self, use_video_port=True):
        if self.camera.closed:
            self.camera = picamera.PiCamera(resolution=(self.w,self.h))

        # take a snapshot
        self.camera.capture(self.stream, format='yuv', use_video_port=use_video_port)
        # save it to stream
        self.stream.truncate(self.fw*self.fh)
        self.stream.seek(0)
        # transform image
        image = np.fromstring(self.stream.getvalue(), dtype=np.uint8).reshape((self.fh, self.fw))[:self.h,:self.w]
        # reset stream
        self.stream.truncate(0)

        return image

    def savesnap(self, fname=None, use_video_port=True):
        if fname is None:
            fname = datetime.now().strftime('%Y%m%d_%H%M%S.%f.jpg')
        # save to file
        misc.imsave(fname, self.snap(use_video_port))

    def resolution(self, w, h):
        self.w, self.h = w, h
        self.fw = (w + 31) // 32 * 32
        self.fh = (h + 15) // 16 * 16
        self.camera.resolution = (w, h)

    def close(self):
        self.camera.close()
        self.closed = self.camera.closed

    def __repr__(self):
        return "Camera instance: resolution (%ix%i)" % (self.w, self.h)


class Servo():
    def __init__(self, gpio, pleft=0.750, pright=1.605):
        GPIO.setup(gpio, GPIO.OUT)
        self.gpio = gpio
        self.pleft    = pleft
        self.pright   = pright
        self.pcenter  = (1.*pright - pleft) / 2 + pleft
        self.hz       = 50
        self.pcurrent = None
        self.stubtime = 0.100

    def sleeptime(self, newposition, maxtime=0.5):
        # calculate the sleep time to let the servo move to the final position, before poweroff
        if self.pcurrent is None: return maxtime
        return max(0.05 ,(abs(self.pcurrent - newposition) / (self.pright-self.pleft)) * maxtime)

    def move(self, position):
        self.pwm = GPIO.PWM(self.gpio, self.hz); mscycle = 1000 / self.hz
        self.pwm.start(position * 100 / mscycle)
        sleep(self.sleeptime(position))
        self.pwm.stop()
        self.pcurrent = position
        sleep(self.stubtime)

    def left(self): self.move(self.pleft)

    def center(self): self.move(self.pcenter)

    def right(self): self.move(self.pright)

    def stop(self):
        self.pwm.stop()

    def angle(self, degree):
        # constrain between +90 or -90 degree and offset by 90
        degree = max(min(90,degree),-90)
        ratio = (degree+90) / 180.
        self.move((self.pright - self.pleft) * ratio + self.pleft)
        return degree

class Jib():
    def __init__(self, servo_x, servo_y):
        self.sx = servo_x   # servo on X-axis
        self.sy = servo_y   # servo on Y-axis
        self.center()       # center the Jib

    # MAIN MOVE FUNCTION
    def movex(self, angle): self.anglex = self.sx.angle(angle)
    def movey(self, angle): self.angley = self.sy.angle(angle)

    # INCREMENTAL MOVE FUNCTION
    def moveleft(self, a=5): self.movex(self.anglex - a)
    def moveright(self, a=5): self.movex(self.anglex + a)
    def moveup(self, a=5): self.movey(self.angley - a)
    def movedw(self, a=5): self.movey(self.angley + a)

    # PREDEFINED MOVEMENTS
    def centerx(self): self.movex(0)
    def centery(self): self.movey(0)
    def center(self): self.movex(0); self.movey(0)
    def left(self): self.movex(-90)
    def right(self): self.movex(+90)
    def up(self): self.movey(-90)
    def dw(self): self.movey(+90)


s1 = Servo(8,  pleft=0.550, pright=1.805)   # X-axis
s2 = Servo(10, pleft=0.700, pright=1.850)   # Y-axis

jib = Jib(s1,s2)
