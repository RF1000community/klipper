#!/usr/bin/env python2
from main import mainApp
import time

def load_config(config):
    mainApp(config).start()

if __name__ == '__main__':
    mainApp().start()
    time.sleep()